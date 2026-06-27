# Generated manually: id_excel (coluna ID do Excel) passa a ser a chave primária

from django.db import migrations, models
import django.db.models.deletion


def populate_id_excel_pk(apps, schema_editor):
    """Converte registros legados para chaves texto únicas antes de trocar a PK."""
    ProjecaoGasto = apps.get_model('app', 'ProjecaoGasto')
    for obj in ProjecaoGasto.objects.all().iterator():
        legacy_pk = getattr(obj, 'id', None)
        obj.id_excel_new = f'LEGACY_{legacy_pk}' if legacy_pk is not None else f'LEGACY_ROW_{obj.pk}'
        obj.save(update_fields=['id_excel_new'])


def reverse_populate_id_excel_pk(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('app', '0119_projecaogasto_gasto_confirmado'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='projecaogasto',
            unique_together=set(),
        ),
        migrations.RemoveIndex(
            model_name='projecaogasto',
            name='app_projeca_id_exce_b23294_idx',
        ),
        migrations.AddField(
            model_name='projecaogasto',
            name='id_excel_new',
            field=models.CharField(max_length=100, null=True, unique=True),
        ),
        migrations.RunPython(populate_id_excel_pk, reverse_populate_id_excel_pk),
        migrations.AlterUniqueTogether(
            name='relacaoprojecaonotafiscal',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='relacaoprojecaonotafiscal',
            name='projecao',
        ),
        migrations.RemoveField(
            model_name='projecaogasto',
            name='id_excel',
        ),
        migrations.RenameField(
            model_name='projecaogasto',
            old_name='id_excel_new',
            new_name='id_excel',
        ),
        migrations.RemoveField(
            model_name='projecaogasto',
            name='id',
        ),
        migrations.AlterField(
            model_name='projecaogasto',
            name='id_excel',
            field=models.CharField(
                help_text='ID único do registro na planilha Excel (chave primária)',
                max_length=100,
                primary_key=True,
                serialize=False,
                verbose_name='ID Excel',
            ),
        ),
        migrations.AddField(
            model_name='relacaoprojecaonotafiscal',
            name='projecao',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='relacoes_notas_fiscais',
                to='app.projecaogasto',
                verbose_name='Projeção de Gasto',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='relacaoprojecaonotafiscal',
            unique_together={('projecao', 'nota_fiscal', 'controle_rc_nf')},
        ),
    ]
