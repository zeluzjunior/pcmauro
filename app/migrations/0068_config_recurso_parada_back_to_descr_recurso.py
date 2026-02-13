# Revert to descr_recurso for config (used in analysis page)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0067_config_recurso_parada_descr_linha_producao'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='configrecursoparadamaquina',
            name='unique_config_recurso_parada_secao_linha',
        ),
        migrations.RenameField(
            model_name='configrecursoparadamaquina',
            old_name='descr_linha_producao',
            new_name='descr_recurso',
        ),
        migrations.AddConstraint(
            model_name='configrecursoparadamaquina',
            constraint=models.UniqueConstraint(fields=('secao', 'descr_recurso'), name='unique_config_recurso_parada_secao_descr'),
        ),
    ]
