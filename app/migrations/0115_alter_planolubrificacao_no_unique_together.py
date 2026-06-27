from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0114_planolubrificacao'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='planolubrificacao',
            unique_together=set(),
        ),
    ]
