from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0118_configindicadoresmanutencao'),
    ]

    operations = [
        migrations.AddField(
            model_name='projecaogasto',
            name='gasto_confirmado',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Gasto Confirmado'),
        ),
    ]

