"""
Management command to import máquinas from XLSM/CSV file
Usage: python manage.py import_maquinas <file_path> [--update]
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.files.uploadedfile import InMemoryUploadedFile
import os
from io import BytesIO
from app.utils import upload_maquinas_from_file


class Command(BaseCommand):
    help = 'Importa máquinas de um arquivo XLSM, XLSX, XLS ou CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Caminho para o arquivo XLSM/CSV a ser importado'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Atualizar registros existentes ao invés de ignorar duplicados',
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        update_existing = options.get('update', False)

        # Verificar se o arquivo existe
        if not os.path.exists(file_path):
            raise CommandError(f'Arquivo não encontrado: {file_path}')

        self.stdout.write(f'Importando máquinas de: {file_path}')
        self.stdout.write(f'Atualizar existentes: {update_existing}')

        try:
            # Para arquivos locais, usar o caminho diretamente
            from app.utils import read_excel_file, read_csv_file
            from app.models import Maquina
            from django.db import transaction
            
            file_name = os.path.basename(file_path).lower()
            
            # Ler arquivo baseado na extensão
            if file_name.endswith(('.xlsx', '.xls', '.xlsm')):
                data = read_excel_file(file_path)
            elif file_name.endswith('.csv'):
                # Tentar diferentes encodings
                try:
                    data = read_csv_file(file_path, encoding='utf-8')
                except UnicodeDecodeError:
                    data = read_csv_file(file_path, encoding='latin-1')
            else:
                raise CommandError("Formato de arquivo não suportado. Use .xlsx, .xls, .xlsm ou .csv")
            
            if not data:
                raise CommandError("Arquivo vazio ou sem dados válidos")
            
            # Importar usando a mesma lógica do upload_maquinas_from_file
            from app.utils import normalize_column_name, _safe_int, _safe_str
            
            errors = []
            created_count = 0
            updated_count = 0
            
            # Processar dados em transação
            with transaction.atomic():
                for row_num, row_data in enumerate(data, start=2):
                    try:
                        # Normalizar nomes das colunas
                        normalized_data = {}
                        for key, value in row_data.items():
                            normalized_key = normalize_column_name(key)
                            normalized_data[normalized_key] = value
                        
                        # Validar que cd_maquina existe
                        cd_maquina = normalized_data.get('cd_maquina')
                        if not cd_maquina:
                            errors.append(f"Linha {row_num}: Código da máquina (CD_MAQUINA) é obrigatório")
                            continue
                        
                        # Converter cd_maquina para int
                        try:
                            if isinstance(cd_maquina, str):
                                cd_maquina = float(cd_maquina)
                            cd_maquina = int(float(cd_maquina))
                        except (ValueError, TypeError):
                            errors.append(f"Linha {row_num}: Código da máquina inválido: {cd_maquina}")
                            continue
                        
                        # Preparar dados para o modelo
                        maquina_data = {
                            'cd_maquina': cd_maquina,
                            'cd_unid': _safe_int(normalized_data.get('cd_unid')),
                            'nome_unid': _safe_str(normalized_data.get('nome_unid')),
                            'cs_tt_maquina': _safe_int(normalized_data.get('cs_tt_maquina')),
                            'descr_maquina': _safe_str(normalized_data.get('descr_maquina')),
                            'cd_setormanut': _safe_str(normalized_data.get('cd_setormanut')),
                            'descr_setormanut': _safe_str(normalized_data.get('descr_setormanut')),
                            'cd_priomaqutv': _safe_int(normalized_data.get('cd_priomaqutv')),
                            'nro_patrimonio': _safe_str(normalized_data.get('nro_patrimonio')),
                            'cd_modelo': _safe_int(normalized_data.get('cd_modelo')),
                            'cd_grupo': _safe_int(normalized_data.get('cd_grupo')),
                            'cd_tpcentativ': _safe_int(normalized_data.get('cd_tpcentativ')),
                            'descr_gerenc': _safe_str(normalized_data.get('descr_gerenc')),
                        }
                        
                        # Criar ou atualizar
                        if update_existing:
                            maquina, created = Maquina.objects.update_or_create(
                                cd_maquina=cd_maquina,
                                defaults=maquina_data
                            )
                            if created:
                                created_count += 1
                            else:
                                updated_count += 1
                        else:
                            # Apenas criar se não existir
                            maquina, created = Maquina.objects.get_or_create(
                                cd_maquina=cd_maquina,
                                defaults=maquina_data
                            )
                            if created:
                                created_count += 1
                            
                    except Exception as e:
                        errors.append(f"Linha {row_num}: {str(e)}")
                        continue

            # Mostrar resultados
            if errors:
                self.stdout.write(self.style.WARNING(f'\nEncontrados {len(errors)} erro(s):'))
                for error in errors[:20]:  # Mostrar primeiros 20 erros
                    self.stdout.write(self.style.WARNING(f'  - {error}'))
                if len(errors) > 20:
                    self.stdout.write(self.style.WARNING(f'  ... e mais {len(errors) - 20} erro(s)'))

            if created_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'\n{created_count} registro(s) criado(s) com sucesso!')
                )
            
            if updated_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'{updated_count} registro(s) atualizado(s) com sucesso!')
                )

            if created_count == 0 and updated_count == 0 and not errors:
                self.stdout.write(self.style.WARNING('\nNenhum registro foi importado.'))

            total = created_count + updated_count
            if total > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'\nTotal: {total} registro(s) processado(s) com sucesso!')
                )

        except Exception as e:
            raise CommandError(f'Erro ao importar arquivo: {str(e)}')

