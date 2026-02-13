# Generated manually: rename grupo_recurso to descr_recurso

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0065_config_recurso_parada_maquina'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='configrecursoparadamaquina',
            name='unique_config_recurso_parada_secao_grupo',
        ),
        migrations.RenameField(
            model_name='configrecursoparadamaquina',
            old_name='grupo_recurso',
            new_name='descr_recurso',
        ),
        migrations.AddConstraint(
            model_name='configrecursoparadamaquina',
            constraint=models.UniqueConstraint(fields=('secao', 'descr_recurso'), name='unique_config_recurso_parada_secao_descr'),
        ),
    ]
