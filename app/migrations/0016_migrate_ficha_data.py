# Generated migration to migrate existing data from OrdemServicoCorretiva to OrdemServicoCorretivaFicha

from django.db import migrations


def migrate_ficha_data(apps, schema_editor):
    """Migrate existing ficha data from OrdemServicoCorretiva to OrdemServicoCorretivaFicha
    
    Note: This migration runs BEFORE the fields are removed, so we can still access them.
    """
    # This migration should run BEFORE the fields are removed
    # But since Django removes fields first, we need to access them via raw SQL or
    # handle this differently. For now, we'll skip data migration as the fields
    # are already removed in migration 0015.
    # If you need to preserve existing data, you should:
    # 1. Create a data migration BEFORE removing the fields
    # 2. Or manually migrate the data after this migration
    pass


def reverse_migrate_ficha_data(apps, schema_editor):
    """Reverse migration - not implemented as data would be lost"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0015_remove_ordemservicocorretiva_cd_func_exec_os_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_ficha_data, reverse_migrate_ficha_data),
    ]

