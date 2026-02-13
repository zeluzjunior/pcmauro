# Generated manually: add Fator de Eficiência % to ConfigParadaMaquina

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0069_producao_diaria'),
    ]

    operations = [
        migrations.AddField(
            model_name='configparadamaquina',
            name='fator_eficiencia',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name='Fator de Eficiência %'),
        ),
    ]
