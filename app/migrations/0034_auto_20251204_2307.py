# Generated migration to rename Cadastro to Matricula and remove Posto and Admissao fields

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0033_requisicaoalmoxarifado'),
    ]

    operations = [
        # Rename Cadastro to Matricula
        migrations.RenameField(
            model_name='manutentor',
            old_name='Cadastro',
            new_name='Matricula',
        ),
        # Remove Posto field
        migrations.RemoveField(
            model_name='manutentor',
            name='Posto',
        ),
        # Remove Admissao field
        migrations.RemoveField(
            model_name='manutentor',
            name='Admissao',
        ),
    ]
