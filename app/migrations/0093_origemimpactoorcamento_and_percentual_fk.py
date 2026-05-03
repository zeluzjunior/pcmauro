from django.db import migrations, models
import django.db.models.deletion


def populate_origens(apps, schema_editor):
    PercentualImpactoSetor = apps.get_model('app', 'PercentualImpactoSetor')
    OrigemImpactoOrcamento = apps.get_model('app', 'OrigemImpactoOrcamento')
    ProjecaoGasto = apps.get_model('app', 'ProjecaoGasto')

    setores_projecao = {
        str(s).strip().upper()
        for s in ProjecaoGasto.objects.exclude(setor__isnull=True).exclude(setor='').values_list('setor', flat=True)
        if str(s).strip()
    }

    for item in PercentualImpactoSetor.objects.all():
        nome = (item.origem_setor or '').strip()
        if not nome:
            continue
        nome_upper = nome.upper()

        if nome_upper in setores_projecao:
            tipo = 'SETOR_PROJECAO'
            setor_projecao = nome
        elif 'REQUISI' in nome_upper:
            tipo = 'REQUISICOES'
            setor_projecao = None
        elif 'NOTA' in nome_upper:
            tipo = 'NOTAS_FISCAIS'
            setor_projecao = None
        else:
            tipo = 'OUTROS'
            setor_projecao = None

        origem, _ = OrigemImpactoOrcamento.objects.get_or_create(
            nome=nome,
            defaults={
                'tipo_origem': tipo,
                'setor_projecao': setor_projecao,
                'ativo': True,
            }
        )
        item.origem_id = origem.id
        item.save(update_fields=['origem'])


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0092_percentualimpactosetor'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrigemImpactoOrcamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(db_index=True, max_length=120, unique=True, verbose_name='Nome da Origem')),
                ('tipo_origem', models.CharField(choices=[('SETOR_PROJECAO', 'Setor de Projeção'), ('REQUISICOES', 'Requisições'), ('NOTAS_FISCAIS', 'Notas Fiscais'), ('OUTROS', 'Outros')], db_index=True, default='OUTROS', max_length=20, verbose_name='Tipo da Origem')),
                ('setor_projecao', models.CharField(blank=True, db_index=True, max_length=100, null=True, verbose_name='Setor no Projeção de Gasto')),
                ('ativo', models.BooleanField(db_index=True, default=True, verbose_name='Ativo')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Data de Atualização')),
            ],
            options={
                'verbose_name': 'Origem de Impacto no Orçamento',
                'verbose_name_plural': 'Origens de Impacto no Orçamento',
                'ordering': ['nome'],
                'indexes': [
                    models.Index(fields=['tipo_origem', 'ativo'], name='app_origemi_tipo_or_b24f79_idx'),
                    models.Index(fields=['setor_projecao'], name='app_origemi_setor_p_3364ef_idx'),
                ],
            },
        ),
        migrations.AddField(
            model_name='percentualimpactosetor',
            name='origem',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='percentuais', to='app.origemimpactoorcamento', verbose_name='Origem'),
        ),
        migrations.RunPython(populate_origens, migrations.RunPython.noop),
    ]
