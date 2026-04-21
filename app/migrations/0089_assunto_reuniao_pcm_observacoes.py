from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0088_assunto_reuniao_pcm_arquivo'),
    ]

    operations = [
        migrations.AddField(
            model_name='assuntoreuniaopcm',
            name='observacoes',
            field=models.TextField(
                blank=True,
                help_text='Texto livre (notas, contexto, detalhes adicionais sobre o assunto).',
                verbose_name='Observações',
            ),
        ),
    ]
