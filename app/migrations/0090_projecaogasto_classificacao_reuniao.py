from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0089_assunto_reuniao_pcm_observacoes'),
    ]

    operations = [
        migrations.AddField(
            model_name='projecaogasto',
            name='classificacao_reuniao',
            field=models.CharField(
                blank=True,
                choices=[
                    ('confirmada', 'Confirmada'),
                    ('possivel', 'Possível'),
                    ('reprogramar', 'Reprogramar'),
                    ('ja_executada', 'Já executada'),
                    ('cancelada', 'Cancelada'),
                ],
                db_index=True,
                help_text='Classificação definida na reunião de projeções de gastos',
                max_length=20,
                null=True,
                verbose_name='Classificação Reunião',
            ),
        ),
    ]
