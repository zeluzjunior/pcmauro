# Generated manually: rename descr_recurso to descr_linha_producao

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0066_config_recurso_parada_descr_recurso'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='configrecursoparadamaquina',
            name='unique_config_recurso_parada_secao_descr',
        ),
        migrations.RenameField(
            model_name='configrecursoparadamaquina',
            old_name='descr_recurso',
            new_name='descr_linha_producao',
        ),
        migrations.AddConstraint(
            model_name='configrecursoparadamaquina',
            constraint=models.UniqueConstraint(fields=('secao', 'descr_linha_producao'), name='unique_config_recurso_parada_secao_linha'),
        ),
    ]
