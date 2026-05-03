from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0091_setorprojecaocor'),
    ]

    operations = [
        migrations.CreateModel(
            name='PercentualImpactoSetor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('origem_setor', models.CharField(db_index=True, max_length=120, verbose_name='Setor/Origem')),
                ('percentual_alocado', models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Percentual Alocado (%)')),
                ('observacao', models.CharField(blank=True, max_length=255, null=True, verbose_name='Observação')),
                ('ativo', models.BooleanField(db_index=True, default=True, verbose_name='Ativo')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Data de Atualização')),
            ],
            options={
                'verbose_name': 'Percentual de Impacto por Setor',
                'verbose_name_plural': 'Percentuais de Impacto por Setor',
                'ordering': ['origem_setor'],
                'indexes': [
                    models.Index(fields=['origem_setor'], name='app_percent_origem__38c9b1_idx'),
                    models.Index(fields=['ativo'], name='app_percent_ativo_4afab3_idx'),
                ],
            },
        ),
    ]
