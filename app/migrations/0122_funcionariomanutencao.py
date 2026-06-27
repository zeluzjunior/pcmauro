from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0121_percentualdehoras'),
    ]

    operations = [
        migrations.CreateModel(
            name='FuncionarioManutencao',
            fields=[
                ('matricula', models.CharField(max_length=20, primary_key=True, serialize=False, verbose_name='Matrícula')),
                ('colaborador', models.CharField(blank=True, max_length=255, null=True, verbose_name='Colaborador')),
                ('cargo', models.CharField(blank=True, max_length=255, null=True, verbose_name='Cargo')),
                ('admissao', models.DateField(blank=True, null=True, verbose_name='Admissão')),
                ('situacao_codigo', models.CharField(blank=True, max_length=20, null=True, verbose_name='Situação (código)')),
                ('situacao_descricao', models.CharField(blank=True, max_length=100, null=True, verbose_name='Situação')),
                ('escala_turma_codigo', models.CharField(blank=True, max_length=20, null=True, verbose_name='Escala/Turma (código)')),
                ('escala_turma', models.CharField(blank=True, max_length=20, null=True, verbose_name='Escala/Turma')),
                ('setor', models.CharField(blank=True, max_length=255, null=True, verbose_name='Setor')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Data de Atualização')),
            ],
            options={
                'verbose_name': 'Funcionário Manutenção',
                'verbose_name_plural': 'Funcionários Manutenção',
                'ordering': ['colaborador', 'matricula'],
            },
        ),
    ]
