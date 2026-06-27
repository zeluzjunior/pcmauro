from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0116_requisicaoporosmanf0044'),
    ]

    operations = [
        migrations.CreateModel(
            name='IndicadoresManutencao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ano', models.IntegerField(db_index=True, verbose_name='Ano')),
                ('mes', models.IntegerField(choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9), (10, 10), (11, 11), (12, 12)], verbose_name='Mês')),
                ('dia', models.IntegerField(help_text='Dia do mês (1-31)', verbose_name='Dia')),
                ('indice_dbo', models.DecimalField(blank=True, decimal_places=3, max_digits=15, null=True, verbose_name='Índice DBO')),
                ('consumo_gas_glp', models.DecimalField(blank=True, decimal_places=3, max_digits=15, null=True, verbose_name='Consumo Gás GLP')),
                ('perda_suino', models.DecimalField(blank=True, decimal_places=3, max_digits=15, null=True, verbose_name='Perda Suíno')),
                ('perda_industria', models.DecimalField(blank=True, decimal_places=3, max_digits=15, null=True, verbose_name='Perda Indústria')),
                ('consumo_agua', models.DecimalField(blank=True, decimal_places=3, max_digits=15, null=True, verbose_name='Consumo Água')),
                ('consumo_cavaco', models.DecimalField(blank=True, decimal_places=3, max_digits=15, null=True, verbose_name='Consumo Cavaco')),
                ('consumo_energia', models.DecimalField(blank=True, decimal_places=3, max_digits=15, null=True, verbose_name='Consumo Energia')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Data de Atualização')),
            ],
            options={
                'verbose_name': 'Indicador de Manutenção',
                'verbose_name_plural': 'Indicadores de Manutenção',
                'db_table': 'indicadores_manutencao',
                'ordering': ['ano', 'mes', 'dia'],
            },
        ),
        migrations.AddIndex(
            model_name='indicadoresmanutencao',
            index=models.Index(fields=['ano', 'mes'], name='app_indicad_ano_mes_6a8f12_idx'),
        ),
        migrations.AddConstraint(
            model_name='indicadoresmanutencao',
            constraint=models.UniqueConstraint(fields=('ano', 'mes', 'dia'), name='unique_indicadores_manutencao_ano_mes_dia'),
        ),
    ]
