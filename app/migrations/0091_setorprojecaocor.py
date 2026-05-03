from django.db import migrations, models


def seed_setor_cores(apps, schema_editor):
    SetorProjecaoCor = apps.get_model('app', 'SetorProjecaoCor')
    defaults = [
        ('Turno A', '#0d6efd', 1),
        ('Turno B', '#198754', 2),
        ('Turno C', '#0dcaf0', 3),
        ('Externa', '#fd7e14', 4),
        ('Utilidades', '#6f42c1', 5),
        ('ETA / ETE / BIO', '#20c997', 6),
        ('Projetos', '#6610f2', 7),
        ('PCM', '#d63384', 8),
        ('Indefinido', '#6c757d', 9),
        ('Outros', '#495057', 10),
    ]

    for nome, cor, ordem in defaults:
        normalizado = ' '.join(str(nome).strip().upper().split())
        SetorProjecaoCor.objects.update_or_create(
            nome_setor_normalizado=normalizado,
            defaults={
                'nome_setor': nome,
                'cor_hex': cor,
                'ordem': ordem,
                'ativo': True,
            }
        )


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0090_projecaogasto_classificacao_reuniao'),
    ]

    operations = [
        migrations.CreateModel(
            name='SetorProjecaoCor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome_setor', models.CharField(db_index=True, max_length=100, unique=True, verbose_name='Nome do Setor')),
                ('nome_setor_normalizado', models.CharField(db_index=True, max_length=100, unique=True, verbose_name='Nome do Setor (normalizado)')),
                ('cor_hex', models.CharField(default='#6c757d', help_text='Formato #RRGGBB', max_length=7, verbose_name='Cor HEX')),
                ('ativo', models.BooleanField(db_index=True, default=True, verbose_name='Ativo')),
                ('ordem', models.PositiveIntegerField(default=0, verbose_name='Ordem')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Data de Atualização')),
            ],
            options={
                'verbose_name': 'Cor de Setor (Projeção)',
                'verbose_name_plural': 'Cores de Setores (Projeção)',
                'ordering': ['ordem', 'nome_setor'],
                'indexes': [
                    models.Index(fields=['nome_setor_normalizado'], name='app_setorpr_nome_se_5df9e8_idx'),
                    models.Index(fields=['ativo', 'ordem'], name='app_setorpr_ativo_1813e1_idx'),
                ],
            },
        ),
        migrations.RunPython(seed_setor_cores, migrations.RunPython.noop),
    ]
