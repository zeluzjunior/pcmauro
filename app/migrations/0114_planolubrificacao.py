from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0113_manutentor_setor_trabalho'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlanoLubrificacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cd_unid', models.IntegerField(blank=True, null=True, verbose_name='Código Unidade')),
                ('nome_unid', models.CharField(blank=True, max_length=255, null=True, verbose_name='Nome Unidade')),
                ('cd_setor', models.CharField(blank=True, max_length=50, null=True, verbose_name='Código Setor')),
                ('descr_setor', models.CharField(blank=True, max_length=255, null=True, verbose_name='Descrição Setor')),
                ('cd_atividade', models.IntegerField(blank=True, null=True, verbose_name='Código Atividade')),
                ('cd_maquina', models.BigIntegerField(blank=True, db_index=True, null=True, verbose_name='Código Máquina')),
                ('descr_maquina', models.CharField(blank=True, max_length=500, null=True, verbose_name='Descrição Máquina')),
                ('nro_patrimonio', models.CharField(blank=True, max_length=100, null=True, verbose_name='Número Patrimônio')),
                ('ponto', models.IntegerField(blank=True, null=True, verbose_name='Ponto')),
                ('descr_ponto', models.CharField(blank=True, max_length=500, null=True, verbose_name='Descrição Ponto')),
                ('numero_plano', models.IntegerField(blank=True, null=True, verbose_name='Número do Plano')),
                ('descr_plano', models.CharField(blank=True, max_length=255, null=True, verbose_name='Descrição do Plano')),
                ('sequencia_manutencao', models.IntegerField(blank=True, null=True, verbose_name='Sequência Manutenção')),
                ('dt_execucao', models.CharField(blank=True, help_text='Data no formato DD/MM/YYYY', max_length=50, null=True, verbose_name='Data Execução')),
                ('quantidade_periodo', models.IntegerField(blank=True, null=True, verbose_name='Quantidade Período')),
                ('quantidade_previsto', models.DecimalField(blank=True, decimal_places=4, max_digits=16, null=True, verbose_name='Quantidade Previsto')),
                ('sequencia_tarefa', models.IntegerField(blank=True, null=True, verbose_name='Sequência Tarefa')),
                ('descr_tarefa', models.TextField(blank=True, null=True, verbose_name='Descrição Tarefa')),
                ('item', models.BigIntegerField(blank=True, null=True, verbose_name='Item')),
                ('descr_item', models.CharField(blank=True, max_length=500, null=True, verbose_name='Descrição Item')),
                ('unidade_medida', models.CharField(blank=True, max_length=50, null=True, verbose_name='Unidade Medida')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Data de Atualização')),
            ],
            options={
                'verbose_name': 'Plano de Lubrificação',
                'verbose_name_plural': 'Planos de Lubrificação',
                'ordering': ['cd_maquina', 'numero_plano', 'sequencia_manutencao', 'sequencia_tarefa'],
            },
        ),
        migrations.AddIndex(
            model_name='planolubrificacao',
            index=models.Index(fields=['cd_maquina'], name='app_planolu_cd_maqui_b17d56_idx'),
        ),
        migrations.AddIndex(
            model_name='planolubrificacao',
            index=models.Index(fields=['numero_plano'], name='app_planolu_numero__97adca_idx'),
        ),
    ]
