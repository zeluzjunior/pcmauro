from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0120_projecaogasto_id_excel_primary_key'),
    ]

    operations = [
        migrations.CreateModel(
            name='PercentualDeHoras',
            fields=[
                ('matricula', models.CharField(max_length=20, primary_key=True, serialize=False, verbose_name='Matrícula')),
                ('nome', models.CharField(blank=True, max_length=255, null=True, verbose_name='Nome')),
                ('tempo1', models.CharField(blank=True, max_length=50, null=True, verbose_name='Tempo 1')),
                ('tempo2', models.CharField(blank=True, max_length=50, null=True, verbose_name='Tempo 2')),
                ('tempo3', models.CharField(blank=True, max_length=50, null=True, verbose_name='Tempo 3')),
                ('percentual', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='Percentual')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Data de Atualização')),
            ],
            options={
                'verbose_name': 'Percentual de Horas',
                'verbose_name_plural': 'Percentuais de Horas',
                'ordering': ['-percentual', 'nome', 'matricula'],
            },
        ),
    ]
