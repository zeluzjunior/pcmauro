# Catálogo compartilhado de peças + FK em PecaMaquinaCitadoManual

from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Count, Min


def forwards_populate_catalogo(apps, schema_editor):
    PMCM = apps.get_model('app', 'PecaMaquinaCitadoManual')
    Cat = apps.get_model('app', 'PecaManualCatalogo')

    for pm in PMCM.objects.iterator():
        fab = (pm.fabricante or '').strip()[:255]
        cod = (pm.codigo_fabricante or '').strip()[:120]
        if not cod:
            cod = '?'
        desc = pm.peca_fornecedor
        if len(desc or '') > 500:
            desc = desc[:500]
        cat, _ = Cat.objects.get_or_create(
            fabricante=fab,
            codigo_fabricante=cod,
            defaults={'peca_fornecedor': desc},
        )
        PMCM.objects.filter(pk=pm.pk).update(peca_catalogo_id=cat.pk)

    dup_groups = (
        PMCM.objects.values('maquina_id', 'peca_catalogo_id')
        .annotate(n=Count('id'), keep=Min('id'))
        .filter(n__gt=1)
    )
    for g in dup_groups:
        PMCM.objects.filter(
            maquina_id=g['maquina_id'],
            peca_catalogo_id=g['peca_catalogo_id'],
        ).exclude(pk=g['keep']).delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0105_remove_pecafornecedor_texto_peca_fornecedor'),
    ]

    operations = [
        migrations.CreateModel(
            name='PecaManualCatalogo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fabricante', models.CharField(db_index=True, help_text='Coluna «FABRICANTE» (C) na LISTA COMPLETA.', max_length=255, verbose_name='Fabricante')),
                ('codigo_fabricante', models.CharField(db_index=True, help_text='Coluna «Cód. do fabricante» (D) na LISTA COMPLETA.', max_length=120, verbose_name='Código do fabricante')),
                ('peca_fornecedor', models.CharField(blank=True, help_text='Coluna «DESCRIÇÃO DO FABRICANTE» (E) na LISTA COMPLETA.', max_length=500, null=True, verbose_name='Descrição do fabricante')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Data de Atualização')),
            ],
            options={
                'verbose_name': 'Peça manual (catálogo)',
                'verbose_name_plural': 'Peças manuais (catálogo)',
                'ordering': ['fabricante', 'codigo_fabricante'],
            },
        ),
        migrations.AddConstraint(
            model_name='pecamanualcatalogo',
            constraint=models.UniqueConstraint(fields=('fabricante', 'codigo_fabricante'), name='uniq_pecamanualcatalogo_fabricante_codigo'),
        ),
        migrations.AddField(
            model_name='pecamaquinacitadomanual',
            name='peca_catalogo',
            field=models.ForeignKey(
                help_text='Definição da peça no fabricante; compartilhada entre máquinas quando for a mesma referência.',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='citacoes_em_maquinas',
                to='app.pecamanualcatalogo',
                verbose_name='Peça (catálogo)',
            ),
        ),
        migrations.RunPython(forwards_populate_catalogo, noop_reverse),
        migrations.RemoveIndex(
            model_name='pecamaquinacitadomanual',
            name='app_pecamaq_maquina_8b2c91_idx',
        ),
        migrations.RemoveField(
            model_name='pecamaquinacitadomanual',
            name='fabricante',
        ),
        migrations.RemoveField(
            model_name='pecamaquinacitadomanual',
            name='codigo_fabricante',
        ),
        migrations.RemoveField(
            model_name='pecamaquinacitadomanual',
            name='peca_fornecedor',
        ),
        migrations.AlterField(
            model_name='pecamaquinacitadomanual',
            name='peca_catalogo',
            field=models.ForeignKey(
                help_text='Definição da peça no fabricante; compartilhada entre máquinas quando for a mesma referência.',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='citacoes_em_maquinas',
                to='app.pecamanualcatalogo',
                verbose_name='Peça (catálogo)',
            ),
        ),
        migrations.AddConstraint(
            model_name='pecamaquinacitadomanual',
            constraint=models.UniqueConstraint(fields=('maquina', 'peca_catalogo'), name='uniq_pmcm_maquina_peca_catalogo'),
        ),
        migrations.AddIndex(
            model_name='pecamaquinacitadomanual',
            index=models.Index(fields=['maquina', 'peca_catalogo'], name='app_pmcm_maquina_cat_idx'),
        ),
    ]
