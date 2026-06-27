from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0115_alter_planolubrificacao_no_unique_together'),
    ]

    operations = [
        migrations.CreateModel(
            name='RequisicaoPorOsMANF0044',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome_arquivo_origem', models.CharField(db_index=True, help_text='Nome do arquivo CSV importado (identifica o snapshot da máquina/relatório)', max_length=500, verbose_name='Arquivo de Origem')),
                ('cd_unid', models.IntegerField(blank=True, null=True, verbose_name='Código Unidade')),
                ('nome_unid', models.CharField(blank=True, max_length=255, null=True, verbose_name='Nome Unidade')),
                ('cd_setormanut', models.CharField(blank=True, max_length=50, null=True, verbose_name='Código Setor Manutenção')),
                ('descr_setormanut', models.CharField(blank=True, max_length=255, null=True, verbose_name='Descrição Setor Manutenção')),
                ('cs_qtd_ord_setor', models.IntegerField(blank=True, null=True, verbose_name='Qtd. Ordens no Setor')),
                ('cd_ordemserv', models.IntegerField(blank=True, db_index=True, null=True, verbose_name='Código Ordem de Serviço')),
                ('cs_vlr', models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True, verbose_name='Valor Total OS')),
                ('cs_qtd_ord', models.IntegerField(blank=True, null=True, verbose_name='Qtd. Itens na OS')),
                ('cd_requisicao', models.BigIntegerField(blank=True, db_index=True, null=True, verbose_name='Código Requisição')),
                ('cd_item', models.BigIntegerField(blank=True, null=True, verbose_name='Código Item')),
                ('descr_item', models.CharField(blank=True, max_length=500, null=True, verbose_name='Descrição Item')),
                ('qtde_item', models.DecimalField(blank=True, decimal_places=4, max_digits=16, null=True, verbose_name='Quantidade Item')),
                ('vlr_item', models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True, verbose_name='Valor Item')),
                ('cd_unid_medida', models.CharField(blank=True, max_length=50, null=True, verbose_name='Unidade de Medida')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Data de Atualização')),
            ],
            options={
                'verbose_name': 'Requisição por OS (MANF0044)',
                'verbose_name_plural': 'Requisições por OS (MANF0044)',
                'db_table': 'requisicoes_por_os_manf0044',
                'ordering': ['nome_arquivo_origem', 'cd_ordemserv', 'cd_requisicao', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='requisicaoporosmanf0044',
            index=models.Index(fields=['nome_arquivo_origem'], name='app_requisi_nome_ar_8f3a21_idx'),
        ),
        migrations.AddIndex(
            model_name='requisicaoporosmanf0044',
            index=models.Index(fields=['cd_ordemserv'], name='app_requisi_cd_orde_4b2c10_idx'),
        ),
        migrations.AddIndex(
            model_name='requisicaoporosmanf0044',
            index=models.Index(fields=['cd_requisicao'], name='app_requisi_cd_requ_9d1e44_idx'),
        ),
    ]
