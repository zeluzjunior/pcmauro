# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0078_remove_excel_servico_concluido'),
    ]

    operations = [
        migrations.CreateModel(
            name='ParadaMaquinaOS',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('os_numero', models.CharField(max_length=10, verbose_name='Ordem de Serviço')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                ('parada_maquina', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='os_confirmadas', to='app.paradamaquina')),
            ],
            options={
                'verbose_name': 'Parada Máquina - OS Confirmada',
                'verbose_name_plural': 'Paradas Máquina - OS Confirmadas',
                'ordering': ['parada_maquina', 'os_numero'],
            },
        ),
        migrations.AddConstraint(
            model_name='paradamaquinaos',
            constraint=models.UniqueConstraint(fields=('parada_maquina', 'os_numero'), name='unique_parada_maquina_os'),
        ),
        migrations.AddIndex(
            model_name='paradamaquinaos',
            index=models.Index(fields=['os_numero'], name='app_paradam_os_nume_idx'),
        ),
    ]
