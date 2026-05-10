from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0109_controlercenf_torno'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssuntoReuniaoPCMArquivo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('arquivo', models.FileField(help_text='Arquivo adicional vinculado ao assunto.', upload_to='reuniao_pcm/assuntos/', verbose_name='Arquivo anexo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('assunto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='arquivos', to='app.assuntoreuniaopcm', verbose_name='Assunto Reunião PCM')),
            ],
            options={
                'verbose_name': 'Arquivo do Assunto Reunião PCM',
                'verbose_name_plural': 'Arquivos dos Assuntos Reunião PCM',
                'ordering': ['id'],
            },
        ),
    ]
