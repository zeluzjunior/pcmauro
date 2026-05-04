# Generated manually — remove PecaFornecedor; guardar descrição do fabricante em PecaMaquinaCitadoManual.peca_fornecedor

from django.db import migrations, models


def copiar_descricao_peca_fornecedor(apps, schema_editor):
    PMCM = apps.get_model('app', 'PecaMaquinaCitadoManual')
    PF = apps.get_model('app', 'PecaFornecedor')
    for pm in PMCM.objects.iterator():
        desc = None
        pid = getattr(pm, 'peca_fornecedor_id', None)
        if pid:
            pf = PF.objects.filter(pk=pid).first()
            if pf and pf.descricao_fabricante:
                desc = (pf.descricao_fabricante or '').strip()[:500] or None
        PMCM.objects.filter(pk=pm.pk).update(peca_fornecedor_desc=desc)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0104_pecamaquinacitadomanual_fabricante_posicao'),
    ]

    operations = [
        migrations.AddField(
            model_name='pecamaquinacitadomanual',
            name='peca_fornecedor_desc',
            field=models.CharField(
                blank=True,
                help_text='Temporário na migração — renomeado para peca_fornecedor',
                max_length=500,
                null=True,
                verbose_name='Descrição fabricante (migração)',
            ),
        ),
        migrations.RunPython(copiar_descricao_peca_fornecedor, noop_reverse),
        migrations.RemoveIndex(
            model_name='pecamaquinacitadomanual',
            name='app_pecamaq_maquina_5a4507_idx',
        ),
        migrations.RemoveField(
            model_name='pecamaquinacitadomanual',
            name='peca_fornecedor',
        ),
        migrations.RenameField(
            model_name='pecamaquinacitadomanual',
            old_name='peca_fornecedor_desc',
            new_name='peca_fornecedor',
        ),
        migrations.AlterField(
            model_name='pecamaquinacitadomanual',
            name='peca_fornecedor',
            field=models.CharField(
                blank=True,
                help_text='Texto da coluna «DESCRIÇÃO DO FABRICANTE» na planilha LISTA COMPLETA (coluna E no layout padrão).',
                max_length=500,
                null=True,
                verbose_name='Descrição do fabricante (peça fornecedor)',
            ),
        ),
        migrations.AddIndex(
            model_name='pecamaquinacitadomanual',
            index=models.Index(fields=['maquina', 'codigo_fabricante'], name='app_pecamaq_maquina_8b2c91_idx'),
        ),
        migrations.DeleteModel(
            name='PecaFornecedor',
        ),
    ]
