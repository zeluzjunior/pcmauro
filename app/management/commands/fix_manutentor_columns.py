"""
Management command to fix Manutentor table column data that was imported/entered in wrong columns.

Fixes applied (as reported by user):
- Matricula <- data from updated_at (converted to string)
- Nome <- data from Matricula

IMPORTANTE: Execute com --dry-run primeiro para verificar o resultado antes de aplicar.

Usage: python manage.py fix_manutentor_columns [--dry-run] [--reverse]

--reverse: Aplica o mapeamento inverso (se os dados estiverem no sentido oposto):
  - Matricula <- Nome (Matricula recebe o que está em Nome)
  - Nome <- Cargo (Nome recebe o que está em Cargo)
  - Cargo <- horario_inicio como string, etc.
  (Use apenas se o mapeamento padrão não fizer sentido para seus dados)
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Corrige dados nas colunas da tabela Manutentor (Matricula, Nome, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra o que seria alterado sem aplicar as mudanças',
        )
        parser.add_argument(
            '--reverse',
            action='store_true',
            help='Aplica mapeamento inverso: Matricula<-Nome, Nome<-Cargo (para dados com shift oposto)',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        reverse = options.get('reverse', False)
        from app.models import Manutentor, ManutentorMaquina, ManutencaoTerceiro

        if dry_run:
            self.stdout.write(self.style.WARNING('Modo DRY-RUN: nenhuma alteração será aplicada'))
        if reverse:
            self.stdout.write(self.style.WARNING('Modo REVERSE: Matricula<-Nome, Nome<-Cargo'))

        updates = []
        for m in Manutentor.objects.all():
            old_matricula = m.Matricula
            old_nome = m.Nome
            old_updated_at = m.updated_at
            old_cargo = m.Cargo or ''

            if reverse:
                # Shift reverso: Matricula <- Nome, Nome <- Cargo
                new_matricula = (old_nome or '').strip()[:1000]
                new_nome = (old_cargo or '').strip()[:1000] if old_cargo else (old_matricula or '')
            else:
                # Padrão: Matricula <- updated_at, Nome <- Matricula
                new_matricula = str(old_updated_at) if old_updated_at else ''
                new_nome = old_matricula or ''

            if not new_matricula:
                self.stdout.write(self.style.WARNING(f'  Pulando {old_matricula}: sem valor para nova Matricula'))
                continue

            # Evitar duplicatas de PK
            if Manutentor.objects.filter(Matricula=new_matricula).exclude(Matricula=old_matricula).exists():
                self.stdout.write(self.style.ERROR(
                    f'  Conflito: Matricula "{new_matricula[:30]}..." já existe. Pulando {old_matricula}'
                ))
                continue

            updates.append({
                'old_matricula': old_matricula,
                'new_matricula': new_matricula,
                'new_nome': new_nome,
            })

        if not updates:
            self.stdout.write('Nenhum registro para corrigir.')
            return

        self.stdout.write(f'Registros a corrigir: {len(updates)}')
        for u in updates[:5]:
            self.stdout.write(
                f"  {u['old_matricula']} -> Matricula='{u['new_matricula'][:40]}...', Nome='{u['new_nome'][:30]}'"
            )
        if len(updates) > 5:
            self.stdout.write(f'  ... e mais {len(updates) - 5}')

        if dry_run:
            self.stdout.write(self.style.SUCCESS('Dry-run concluído. Execute sem --dry-run para aplicar.'))
            return

        with transaction.atomic():
            for u in updates:
                old_matricula = u['old_matricula']
                new_matricula = u['new_matricula']
                new_nome = u['new_nome']

                # 1. Atualizar Manutentor primeiro (muda PK de old -> new)
                Manutentor.objects.filter(Matricula=old_matricula).update(
                    Matricula=new_matricula,
                    Nome=new_nome,
                )

                # 2. Atualizar FKs em ManutentorMaquina (manutentor_id aponta para PK)
                ManutentorMaquina.objects.filter(manutentor_id=old_matricula).update(manutentor_id=new_matricula)

                # 3. Atualizar FKs em ManutencaoTerceiro
                ManutencaoTerceiro.objects.filter(manutentor_id=old_matricula).update(manutentor_id=new_matricula)

        self.stdout.write(self.style.SUCCESS(f'Corrigidos {len(updates)} registros.'))
