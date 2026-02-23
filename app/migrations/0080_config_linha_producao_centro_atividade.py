# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0079_paradamaquinaos'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfigLinhaProducaoCentroAtividade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descr_linha_producao', models.CharField(db_index=True, max_length=255, verbose_name='Linha de Produção')),
                ('centro_atividade', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='linhas_producao_config', to='app.centroatividade', verbose_name='Centro de Atividade')),
            ],
            options={
                'verbose_name': 'Linha de Produção × Centro de Atividade',
                'verbose_name_plural': 'Linhas de Produção × Centros de Atividade',
                'ordering': ['descr_linha_producao', 'centro_atividade__ca'],
            },
        ),
        migrations.AddConstraint(
            model_name='configlinhaproducaocentroatividade',
            constraint=models.UniqueConstraint(fields=('descr_linha_producao', 'centro_atividade'), name='unique_linha_producao_centro_atividade'),
        ),
        migrations.AddIndex(
            model_name='configlinhaproducaocentroatividade',
            index=models.Index(fields=['descr_linha_producao'], name='app_configl_descr_l_idx'),
        ),
    ]
