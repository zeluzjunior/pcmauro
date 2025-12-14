# Generated migration to merge LocalCentroAtividade into CentroAtividade

from django.db import migrations, models
import django.db.models.deletion


def migrate_local_data_to_centro_atividade(apps, schema_editor):
    """Migrate data from LocalCentroAtividade to CentroAtividade"""
    CentroAtividade = apps.get_model('app', 'CentroAtividade')
    LocalCentroAtividade = apps.get_model('app', 'LocalCentroAtividade')
    Maquina = apps.get_model('app', 'Maquina')
    
    # Copy local and observacoes from LocalCentroAtividade to CentroAtividade
    for local_ca in LocalCentroAtividade.objects.all():
        centro_atividade = local_ca.centro_atividade
        if local_ca.local:
            centro_atividade.local = local_ca.local
        if local_ca.observacoes:
            centro_atividade.observacoes = local_ca.observacoes
        centro_atividade.save()
    
    # Update Maquina.local_centro_atividade to Maquina.centro_atividade
    for maquina in Maquina.objects.filter(local_centro_atividade__isnull=False):
        if maquina.local_centro_atividade:
            maquina.centro_atividade = maquina.local_centro_atividade.centro_atividade
            maquina.save()


def reverse_migration(apps, schema_editor):
    """Reverse migration - recreate LocalCentroAtividade from CentroAtividade"""
    CentroAtividade = apps.get_model('app', 'CentroAtividade')
    LocalCentroAtividade = apps.get_model('app', 'LocalCentroAtividade')
    Maquina = apps.get_model('app', 'Maquina')
    
    # Recreate LocalCentroAtividade records
    for centro_atividade in CentroAtividade.objects.filter(local__isnull=False).exclude(local=''):
        local_ca, created = LocalCentroAtividade.objects.get_or_create(
            centro_atividade=centro_atividade,
            defaults={
                'local': centro_atividade.local or '',
                'observacoes': centro_atividade.observacoes or ''
            }
        )
        if not created:
            local_ca.local = centro_atividade.local or ''
            local_ca.observacoes = centro_atividade.observacoes or ''
            local_ca.save()
    
    # Update Maquina.centro_atividade back to Maquina.local_centro_atividade
    for maquina in Maquina.objects.filter(centro_atividade__isnull=False):
        if maquina.centro_atividade:
            # Find or create LocalCentroAtividade for this CentroAtividade
            local_ca = LocalCentroAtividade.objects.filter(
                centro_atividade=maquina.centro_atividade
            ).first()
            if local_ca:
                maquina.local_centro_atividade = local_ca
                maquina.save()


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0046_dadosorcamento'),
    ]

    operations = [
        # Step 1: Add local and observacoes fields to CentroAtividade
        migrations.AddField(
            model_name='centroatividade',
            name='local',
            field=models.CharField(blank=True, help_text='Local do Centro de Atividade', max_length=255, null=True, verbose_name='Local'),
        ),
        migrations.AddField(
            model_name='centroatividade',
            name='observacoes',
            field=models.TextField(blank=True, help_text='Observações sobre o local', null=True, verbose_name='Observações'),
        ),
        
        # Step 2: Add centro_atividade field to Maquina (temporary, will replace local_centro_atividade)
        migrations.AddField(
            model_name='maquina',
            name='centro_atividade',
            field=models.ForeignKey(blank=True, help_text='Centro de Atividade relacionado ao setor de manutenção', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='maquinas', to='app.centroatividade', verbose_name='Centro de Atividade'),
        ),
        
        # Step 3: Migrate data
        migrations.RunPython(migrate_local_data_to_centro_atividade, reverse_migration),
        
        # Step 4: Remove old local_centro_atividade field from Maquina
        migrations.RemoveField(
            model_name='maquina',
            name='local_centro_atividade',
        ),
        
        # Step 5: Delete LocalCentroAtividade model
        migrations.DeleteModel(
            name='LocalCentroAtividade',
        ),
    ]
