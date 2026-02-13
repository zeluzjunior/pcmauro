# Generated manually: add Indústria fields (dias úteis, total produção, perda máximo)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0070_config_parada_maquina_fator_eficiencia'),
    ]

    operations = [
        migrations.AddField(
            model_name='configparadamaquina',
            name='dias_uteis_industria',
            field=models.IntegerField(blank=True, null=True, verbose_name='Dias úteis (Indústria)'),
        ),
        migrations.AddField(
            model_name='configparadamaquina',
            name='total_producao_planejada_industria',
            field=models.IntegerField(blank=True, null=True, verbose_name='Total de Produção Planejada (Indústria)'),
        ),
        migrations.AddField(
            model_name='configparadamaquina',
            name='perda_maximo_industria',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name='% de Perda Máximo (Indústria)'),
        ),
        migrations.RemoveField(
            model_name='configparadamaquina',
            name='industria_param1',
        ),
        migrations.RemoveField(
            model_name='configparadamaquina',
            name='industria_param2',
        ),
        migrations.RemoveField(
            model_name='configparadamaquina',
            name='industria_param3',
        ),
    ]
