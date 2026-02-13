# Generated manually: add Fator de Eficiência % for Indústria

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0071_config_parada_maquina_industria_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='configparadamaquina',
            name='fator_eficiencia_industria',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name='Fator de Eficiência % (Indústria)'),
        ),
    ]
