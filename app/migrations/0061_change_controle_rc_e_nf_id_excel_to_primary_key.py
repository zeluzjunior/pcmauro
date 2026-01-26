# Generated manually for changing id_excel to primary key

from django.db import migrations, models
from django.utils import timezone


def populate_id_excel_for_null_records(apps, schema_editor):
    """Populate id_excel for any records that have NULL id_excel"""
    ControleRCeNF = apps.get_model('app', 'ControleRCeNF')
    
    # Find all records with NULL id_excel
    records_without_id = ControleRCeNF.objects.filter(id_excel__isnull=True)
    
    # Generate unique IDs for each record
    for idx, record in enumerate(records_without_id):
        # Use a combination of existing fields or generate a unique ID
        # Try to use RC or NF Saída if available, otherwise generate
        if record.rc:
            base_id = f"RC_{record.rc}"
        elif record.nf_saida:
            base_id = f"NF_{record.nf_saida}"
        else:
            # Use the old id field if available, otherwise generate
            old_id = getattr(record, 'id', None)
            if old_id:
                base_id = f"IMPORT_{old_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}"
            else:
                base_id = f"IMPORT_{idx}_{timezone.now().strftime('%Y%m%d%H%M%S')}"
        
        # Ensure uniqueness by appending index if needed
        unique_id = base_id
        counter = 1
        while ControleRCeNF.objects.filter(id_excel=unique_id).exists():
            unique_id = f"{base_id}_{counter}"
            counter += 1
        
        record.id_excel = unique_id
        record.save()


def reverse_populate_id_excel(apps, schema_editor):
    """Reverse operation - set id_excel to NULL for records that were auto-generated"""
    # This is a no-op since we can't reliably identify which records were auto-generated
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0060_change_projecao_gasto_id_excel_to_composite_key'),
    ]

    operations = [
        # Step 1: Populate NULL id_excel values
        migrations.RunPython(populate_id_excel_for_null_records, reverse_populate_id_excel),
        
        # Step 2: Remove null=True and blank=True, make it required (but keep unique for now)
        migrations.AlterField(
            model_name='controlercenf',
            name='id_excel',
            field=models.CharField(
                db_index=True,
                help_text='ID único do registro na planilha Excel (chave primária)',
                max_length=100,
                unique=True,
                verbose_name='ID'
            ),
        ),
        
        # Step 3: Remove the old id field
        migrations.RemoveField(
            model_name='controlercenf',
            name='id',
        ),
        
        # Step 4: Set id_excel as primary key (this will automatically make it unique)
        migrations.AlterField(
            model_name='controlercenf',
            name='id_excel',
            field=models.CharField(
                db_index=True,
                help_text='ID único do registro na planilha Excel (chave primária)',
                max_length=100,
                primary_key=True,
                serialize=False,
                verbose_name='ID'
            ),
        ),
    ]
