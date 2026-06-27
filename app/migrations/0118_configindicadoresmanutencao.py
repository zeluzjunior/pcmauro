from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0117_indicadoresmanutencao'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfigIndicadoresManutencao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ano', models.IntegerField(db_index=True, verbose_name='Ano')),
                ('mes', models.IntegerField(choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9), (10, 10), (11, 11), (12, 12)], verbose_name='Mês')),
                ('max_indice_dbo', models.DecimalField(blank=True, decimal_places=3, max_digits=15, null=True, verbose_name='Máx. Índice DBO')),
                ('max_consumo_gas_glp', models.DecimalField(blank=True, decimal_places=3, max_digits=15, null=True, verbose_name='Máx. Consumo Gás GLP')),
                ('max_perda_suino', models.DecimalField(blank=True, decimal_places=3, max_digits=15, null=True, verbose_name='Máx. Perda Suíno')),
                ('max_perda_industria', models.DecimalField(blank=True, decimal_places=3, max_digits=15, null=True, verbose_name='Máx. Perda Indústria')),
                ('max_consumo_agua', models.DecimalField(blank=True, decimal_places=3, max_digits=15, null=True, verbose_name='Máx. Consumo Água')),
                ('max_consumo_cavaco', models.DecimalField(blank=True, decimal_places=3, max_digits=15, null=True, verbose_name='Máx. Consumo Cavaco')),
                ('max_consumo_energia', models.DecimalField(blank=True, decimal_places=3, max_digits=15, null=True, verbose_name='Máx. Consumo Energia')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Data de Atualização')),
            ],
            options={
                'verbose_name': 'Configuração de Indicadores de Manutenção',
                'verbose_name_plural': 'Configurações de Indicadores de Manutenção',
                'db_table': 'config_indicadores_manutencao',
                'ordering': ['ano', 'mes'],
            },
        ),
        migrations.AddIndex(
            model_name='configindicadoresmanutencao',
            index=models.Index(fields=['ano', 'mes'], name='app_configi_ano_mes_2f8a91_idx'),
        ),
        migrations.AddConstraint(
            model_name='configindicadoresmanutencao',
            constraint=models.UniqueConstraint(fields=('ano', 'mes'), name='unique_config_indicadores_manutencao_ano_mes'),
        ),
    ]
