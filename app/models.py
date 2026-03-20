from django.db import models


# Choices para o modelo Manutentor
TURNO = (
    ('Turno A', 'Turno A'),
    ('Turno B', 'Turno B'),
    ('Turno C', 'Turno C'),
)

TIPO_MANUTENTOR = (
    ('Eletricista', 'Eletricista'),
    ('Mecânico', 'Mecânico'),
    ('Eletromecânico', 'Eletromecânico'),
    ('Operador ETE/ETA', 'Operador ETE/ETA'),
)

TIPO_MAQUINA = (
    ('Primaria', 'Primaria'),
    ('Secundaria', 'Secundaria'),
)

TIPO_MANUTENCAO = (
    ('Corretiva', 'Corretiva'),
    ('Preventiva', 'Preventiva'),
)

LOCAL_TRABALHO = (
    ('Industria', 'Industria'),
    ('Frigorífico', 'Frigorífico'),
    ('Civil', 'Civil'),
    ('Externa', 'Externa'),
    ('Indefinido', 'Indefinido'),
    ('ETE/ETA', 'ETE/ETA'),
    ('Utilidades', 'Utilidades'),
    ('Manutenção', 'Manutenção'),
)

CLASSI_CA = (
    ('OUTROS', 'OUTROS'),
    ('UTILIDADES', 'UTILIDADES'),
    ('ETA / ETE', 'ETA / ETE'),
    ('FRIGORÍFICO', 'FRIGORÍFICO'),
    ('INDUSTRIALIZADOS', 'INDUSTRIALIZADOS'),
)

RESPONSAVEL_PCM = (('JOSÉ', 'JOSÉ'),('RHUAN', 'RHUAN'),('KARINE', 'KARINE'),)


class Maquina(models.Model):
    """Modelo para armazenar informações de máquinas"""
    cd_unid = models.IntegerField('Código Unidade', blank=True, null=True)
    nome_unid = models.CharField('Nome Unidade', max_length=255, blank=True, null=True)
    cs_tt_maquina = models.IntegerField('Código Total Máquina', blank=True, null=True)
    descr_maquina = models.CharField('Descrição Máquina', max_length=500, blank=True, null=True)
    cd_maquina = models.BigIntegerField('Código Máquina', unique=True, db_index=True)
    cd_setormanut = models.CharField('Código Setor Manutenção', max_length=50, blank=True, null=True)
    descr_setormanut = models.CharField('Descrição Setor Manutenção', max_length=255, blank=True, null=True)
    cd_priomaqutv = models.IntegerField('Código Prioridade Máquina', blank=True, null=True)
    nro_patrimonio = models.CharField('Número Patrimônio', max_length=100, blank=True, null=True)
    cd_modelo = models.IntegerField('Código Modelo', blank=True, null=True)
    cd_grupo = models.IntegerField('Código Grupo', blank=True, null=True)
    cd_tpcentativ = models.IntegerField('Código Tipo Centro Atividade', blank=True, null=True)
    descr_gerenc = models.CharField('Descrição Gerência', max_length=255, blank=True, null=True)
    foto = models.ImageField('Foto da Máquina', upload_to='maquinas/fotos/', blank=True, null=True)
    placa_identificacao = models.ImageField('Placa de Identificação', upload_to='maquinas/placas/', blank=True, null=True)
    codigo_aurora = models.ImageField('Código Aurora', upload_to='maquinas/codigos/', blank=True, null=True, help_text='Foto do código Aurora')
    codigo_fabricante = models.ImageField('Código do Fabricante', upload_to='maquinas/codigos/', blank=True, null=True, help_text='Foto do código do fabricante')
    arquivo_pdf = models.FileField('Arquivo PDF', upload_to='arquivos_maquinas/', blank=True, null=True, help_text='Upload de arquivo PDF relacionado à máquina')
    diagrama_eletrico = models.FileField('Diagrama Elétrico', upload_to='arquivos_maquinas/', blank=True, null=True, help_text='Upload de arquivo PDF do diagrama elétrico')
    pecas_reposicao = models.FileField('Peças de Reposição', upload_to='arquivos_maquinas/', blank=True, null=True, help_text='Upload de arquivo PDF de peças de reposição')
    centro_atividade = models.ForeignKey(
        'CentroAtividade',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Centro de Atividade',
        help_text='Centro de Atividade relacionado ao setor de manutenção',
        related_name='maquinas'
    )
    ativo = models.BooleanField('Ativo', default=True, db_index=True, help_text='Máquina ativa (exibir em listagens)')
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Máquina'
        verbose_name_plural = 'Máquinas'
        ordering = ['cd_maquina']

    def __str__(self):
        return f"{self.cd_maquina} - {self.descr_maquina or 'Sem descrição'}"

class MaquinaDocumento(models.Model):
    """Modelo para armazenar documentos relacionados a máquinas"""
    maquina = models.ForeignKey(
        Maquina, 
        on_delete=models.CASCADE, 
        verbose_name='Máquina', 
        related_name='documentos'
    )
    arquivo = models.FileField(
        'Arquivo', 
        upload_to='maquinas/documentos/', 
        help_text='Upload de arquivo relacionado à máquina (PDF, imagens, etc.)'
    )
    comentario = models.TextField(
        'Comentário', 
        blank=True, 
        null=True, 
        help_text='Comentário sobre o documento'
    )
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Documento da Máquina'
        verbose_name_plural = 'Documentos da Máquina'
        ordering = ['-created_at']

    def __str__(self):
        nome_arquivo = self.arquivo.name.split('/')[-1] if self.arquivo else 'Sem arquivo'
        return f"{self.maquina.cd_maquina} - {nome_arquivo}"

class OrdemServicoCorretiva(models.Model):
    """Modelo para armazenar ordens de serviço corretivas e outros fechadas"""
    # Unidade
    cd_unid = models.IntegerField('Código Unidade', blank=True, null=True)
    nome_unid = models.CharField('Nome Unidade', max_length=255, blank=True, null=True)
    cd_unid_exec = models.IntegerField('Código Unidade Execução', blank=True, null=True)
    nome_unid_exec = models.CharField('Nome Unidade Execução', max_length=255, blank=True, null=True)
    
    # Setor de Manutenção
    cd_setormanut = models.CharField('Código Setor Manutenção', max_length=50, blank=True, null=True)
    descr_setormanut = models.CharField('Descrição Setor Manutenção', max_length=255, blank=True, null=True)
    
    # Centro de Atividade
    cd_tpcentativ = models.IntegerField('Código Tipo Centro Atividade', blank=True, null=True)
    descr_abrev_tpcentativ = models.CharField('Descrição Abrev Centro Atividade', max_length=255, blank=True, null=True)
    
    # Máquina
    cd_maquina = models.BigIntegerField('Código Máquina', blank=True, null=True, db_index=True)
    descr_maquina = models.CharField('Descrição Máquina', max_length=500, blank=True, null=True)
    
    # Ordem de Serviço
    cd_ordemserv = models.BigIntegerField('Código Ordem Serviço', unique=True, db_index=True)
    
    # Datas de Entrada e Abertura 
    dt_entrada = models.CharField('Data Entrada', max_length=50, blank=True, null=True)
    dt_abertura_solicita = models.CharField('Data Abertura Solicitação', max_length=50, blank=True, null=True)
    
    # Funcionário Solicitante
    cd_func_solic_os = models.CharField('Código Funcionário Solicitante OS', max_length=100, blank=True, null=True)
    nm_func_solic_os = models.CharField('Nome Funcionário Solicitante OS', max_length=255, blank=True, null=True)
    
    # Descrição da Queixa
    descr_queixa = models.TextField('Descrição Queixa', blank=True, null=True)
    
    # Execução de Tarefas
    exec_tarefas = models.TextField('Execução Tarefas', blank=True, null=True)
    
    # Funcionário Executor
    cd_func_exec = models.CharField('Código Funcionário Executor', max_length=100, blank=True, null=True)
    nm_func_exec = models.CharField('Nome Funcionário Executor', max_length=255, blank=True, null=True)
    
    # Observações da Ordem de Serviço
    descr_obsordserv = models.TextField('Descrição Observações Ordem Serviço', blank=True, null=True)
    
    # Datas de Encerramento e Abertura
    dt_encordmanu = models.CharField('Data Encerramento Ordem Manutenção', max_length=50, blank=True, null=True)
    dt_aberordser = models.CharField('Data Abertura Ordem Serviço', max_length=50, blank=True, null=True)
    
    # Datas de Parada de Manutenção
    dt_iniparmanu = models.CharField('Data Início Parada Manutenção', max_length=50, blank=True, null=True)
    dt_fimparmanu = models.CharField('Data Fim Parada Manutenção', max_length=50, blank=True, null=True)
    
    # Data Prevista Execução
    dt_prev_exec = models.CharField('Data Prevista Execução', max_length=50, blank=True, null=True)
    
    # Tipo de Ordem de Serviço
    cd_tpordservtv = models.IntegerField('Código Tipo Ordem Serviço', blank=True, null=True)
    descr_tpordservtv = models.CharField('Descrição Tipo Ordem Serviço', max_length=255, blank=True, null=True)
    descr_sitordsetv = models.CharField('Descrição Situação Ordem Serviço', max_length=255, blank=True, null=True)
    
    # Recomendações e Sequência
    descr_recomenos = models.TextField('Descrição Recomendações OS', blank=True, null=True)
    descr_seqplamanu = models.CharField('Descrição Sequência Plano Manutenção', max_length=255, blank=True, null=True)
    
    # Tipo de Manutenção
    cd_tpmanuttv = models.IntegerField('Código Tipo Manutenção', blank=True, null=True)
    descr_tpmanuttv = models.CharField('Descrição Tipo Manutenção', max_length=255, blank=True, null=True)
    
    # Classificação Origem OS
    cd_clasorigos = models.IntegerField('Código Classificação Origem OS', blank=True, null=True)
    descr_clasorigos = models.CharField('Descrição Classificação Origem OS', max_length=255, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Ordem de Serviço Corretiva'
        verbose_name_plural = 'Ordens de Serviço Corretivas'
        ordering = ['-cd_ordemserv']

    def __str__(self):
        return f"{self.cd_ordemserv} - {self.descr_maquina or 'Sem descrição'}"

class OrdemServicoCorretivaFicha(models.Model):
    """Modelo para armazenar fichas de manutenção associadas a ordens de serviço corretivas.
    Permite múltiplas fichas para a mesma ordem de serviço."""
    ordem_servico = models.ForeignKey(
        OrdemServicoCorretiva, 
        on_delete=models.CASCADE, 
        verbose_name='Ordem de Serviço', 
        related_name='fichas'
    )
    
    # Funcionário Executor OS
    cd_func_exec_os = models.CharField('Código Funcionário Executor OS', max_length=100, blank=True, null=True)
    nm_func_exec_os = models.CharField('Nome Funcionário Executor OS', max_length=255, blank=True, null=True)
    
    # Datas de Ficha de Manutenção
    dt_ficapomanu = models.CharField('Data Ficha Ponto Manutenção', max_length=50, blank=True, null=True)
    dt_inic_iteficmanu = models.CharField('Data Início Item Ficha Manutenção', max_length=50, blank=True, null=True)
    dt_fim_iteficmanu = models.CharField('Data Fim Item Ficha Manutenção', max_length=50, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Ficha de Manutenção'
        verbose_name_plural = 'Fichas de Manutenção'
        ordering = ['-created_at']

    def __str__(self):
        return f"Ficha OS {self.ordem_servico.cd_ordemserv} - {self.nm_func_exec_os or 'Sem executor'}"

class OrdemServicoPreventiva(models.Model):
    """Modelo para armazenar ordens de serviço preventivas fechadas"""
    # Unidade
    cd_unid = models.IntegerField('Código Unidade', blank=True, null=True)
    nome_unid = models.CharField('Nome Unidade', max_length=255, blank=True, null=True)
    cd_unid_exec = models.IntegerField('Código Unidade Execução', blank=True, null=True)
    nome_unid_exec = models.CharField('Nome Unidade Execução', max_length=255, blank=True, null=True)
    
    # Setor de Manutenção
    cd_setormanut = models.CharField('Código Setor Manutenção', max_length=50, blank=True, null=True)
    descr_setormanut = models.CharField('Descrição Setor Manutenção', max_length=255, blank=True, null=True)
    
    # Centro de Atividade
    cd_tpcentativ = models.IntegerField('Código Tipo Centro Atividade', blank=True, null=True)
    descr_abrev_tpcentativ = models.CharField('Descrição Abrev Centro Atividade', max_length=255, blank=True, null=True)
    
    # Máquina
    cd_maquina = models.BigIntegerField('Código Máquina', blank=True, null=True, db_index=True)
    descr_maquina = models.CharField('Descrição Máquina', max_length=500, blank=True, null=True)
    
    # Ordem de Serviço
    cd_ordemserv = models.BigIntegerField('Código Ordem Serviço', unique=True, db_index=True)
    
    # Datas de Entrada e Abertura 
    dt_entrada = models.CharField('Data Entrada', max_length=50, blank=True, null=True)
    dt_abertura_solicita = models.CharField('Data Abertura Solicitação', max_length=50, blank=True, null=True)
    
    # Funcionário Solicitante
    cd_func_solic_os = models.CharField('Código Funcionário Solicitante OS', max_length=100, blank=True, null=True)
    nm_func_solic_os = models.CharField('Nome Funcionário Solicitante OS', max_length=255, blank=True, null=True)
    
    # Descrição da Queixa
    descr_queixa = models.TextField('Descrição Queixa', blank=True, null=True)
    
    # Execução de Tarefas
    exec_tarefas = models.TextField('Execução Tarefas', blank=True, null=True)
    
    # Funcionário Executor
    cd_func_exec = models.CharField('Código Funcionário Executor', max_length=100, blank=True, null=True)
    nm_func_exec = models.CharField('Nome Funcionário Executor', max_length=255, blank=True, null=True)
    
    # Observações da Ordem de Serviço
    descr_obsordserv = models.TextField('Descrição Observações Ordem Serviço', blank=True, null=True)
    
    # Datas de Encerramento e Abertura
    dt_encordmanu = models.CharField('Data Encerramento Ordem Manutenção', max_length=50, blank=True, null=True)
    dt_aberordser = models.CharField('Data Abertura Ordem Serviço', max_length=50, blank=True, null=True)
    
    # Datas de Parada de Manutenção
    dt_iniparmanu = models.CharField('Data Início Parada Manutenção', max_length=50, blank=True, null=True)
    dt_fimparmanu = models.CharField('Data Fim Parada Manutenção', max_length=50, blank=True, null=True)
    
    # Data Prevista Execução
    dt_prev_exec = models.CharField('Data Prevista Execução', max_length=50, blank=True, null=True)
    
    # Tipo de Ordem de Serviço
    cd_tpordservtv = models.IntegerField('Código Tipo Ordem Serviço', blank=True, null=True)
    descr_tpordservtv = models.CharField('Descrição Tipo Ordem Serviço', max_length=255, blank=True, null=True)
    descr_sitordsetv = models.CharField('Descrição Situação Ordem Serviço', max_length=255, blank=True, null=True)
    
    # Recomendações e Sequência
    descr_recomenos = models.TextField('Descrição Recomendações OS', blank=True, null=True)
    descr_seqplamanu = models.CharField('Descrição Sequência Plano Manutenção', max_length=255, blank=True, null=True)
    
    # Tipo de Manutenção
    cd_tpmanuttv = models.IntegerField('Código Tipo Manutenção', blank=True, null=True)
    descr_tpmanuttv = models.CharField('Descrição Tipo Manutenção', max_length=255, blank=True, null=True)
    
    # Classificação Origem OS
    cd_clasorigos = models.IntegerField('Código Classificação Origem OS', blank=True, null=True)
    descr_clasorigos = models.CharField('Descrição Classificação Origem OS', max_length=255, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Ordem de Serviço Preventiva'
        verbose_name_plural = 'Ordens de Serviço Preventivas'
        ordering = ['-cd_ordemserv']

    def __str__(self):
        return f"{self.cd_ordemserv} - {self.descr_maquina or 'Sem descrição'}"

class OrdemServicoPreventivaFicha(models.Model):
    """Modelo para armazenar fichas de manutenção associadas a ordens de serviço preventivas.
    Permite múltiplas fichas para a mesma ordem de serviço."""
    ordem_servico = models.ForeignKey(
        OrdemServicoPreventiva, 
        on_delete=models.CASCADE, 
        verbose_name='Ordem de Serviço', 
        related_name='fichas'
    )
    
    # Funcionário Executor OS
    cd_func_exec_os = models.CharField('Código Funcionário Executor OS', max_length=100, blank=True, null=True)
    nm_func_exec_os = models.CharField('Nome Funcionário Executor OS', max_length=255, blank=True, null=True)
    
    # Datas de Ficha de Manutenção
    dt_ficapomanu = models.CharField('Data Ficha Ponto Manutenção', max_length=50, blank=True, null=True)
    dt_inic_iteficmanu = models.CharField('Data Início Item Ficha Manutenção', max_length=50, blank=True, null=True)
    dt_fim_iteficmanu = models.CharField('Data Fim Item Ficha Manutenção', max_length=50, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Ficha de Manutenção Preventiva'
        verbose_name_plural = 'Fichas de Manutenção Preventivas'
        ordering = ['-created_at']

    def __str__(self):
        return f"Ficha OS {self.ordem_servico.cd_ordemserv} - {self.nm_func_exec_os or 'Sem executor'}"

class OrdemServicoLubrificacao(models.Model):
    """Modelo para armazenar ordens de serviço de lubrificação (abertas ou fechadas).
    Importado de lubrificacao_aberta.csv e lubrificacao_fechada.csv"""
    # Unidade
    cd_unid = models.IntegerField('Código Unidade', blank=True, null=True)
    nome_unid = models.CharField('Nome Unidade', max_length=255, blank=True, null=True)
    cd_unid_exec = models.IntegerField('Código Unidade Execução', blank=True, null=True)
    nome_unid_exec = models.CharField('Nome Unidade Execução', max_length=255, blank=True, null=True)
    
    # Setor de Manutenção
    cd_setormanut = models.CharField('Código Setor Manutenção', max_length=50, blank=True, null=True)
    descr_setormanut = models.CharField('Descrição Setor Manutenção', max_length=255, blank=True, null=True)
    
    # Centro de Atividade
    cd_tpcentativ = models.IntegerField('Código Tipo Centro Atividade', blank=True, null=True)
    descr_abrev_tpcentativ = models.CharField('Descrição Abrev Centro Atividade', max_length=255, blank=True, null=True)
    
    # Máquina
    cd_maquina = models.BigIntegerField('Código Máquina', blank=True, null=True, db_index=True)
    descr_maquina = models.CharField('Descrição Máquina', max_length=500, blank=True, null=True)
    
    # Ordem de Serviço
    cd_ordemserv = models.BigIntegerField('Código Ordem Serviço', unique=True, db_index=True)
    
    # Datas de Entrada e Abertura
    dt_entrada = models.CharField('Data Entrada', max_length=50, blank=True, null=True)
    dt_abertura_solicita = models.CharField('Data Abertura Solicitação', max_length=50, blank=True, null=True)
    
    # Funcionário Solicitante
    cd_func_solic_os = models.CharField('Código Funcionário Solicitante OS', max_length=100, blank=True, null=True)
    nm_func_solic_os = models.CharField('Nome Funcionário Solicitante OS', max_length=255, blank=True, null=True)
    
    # Descrição da Queixa
    descr_queixa = models.TextField('Descrição Queixa', blank=True, null=True)
    
    # Execução de Tarefas
    exec_tarefas = models.TextField('Execução Tarefas', blank=True, null=True)
    
    # Funcionário Executor
    cd_func_exec = models.CharField('Código Funcionário Executor', max_length=100, blank=True, null=True)
    nm_func_exec = models.CharField('Nome Funcionário Executor', max_length=255, blank=True, null=True)
    
    # Observações da Ordem de Serviço
    descr_obsordserv = models.TextField('Descrição Observações Ordem Serviço', blank=True, null=True)
    
    # Datas de Encerramento e Abertura
    dt_encordmanu = models.CharField('Data Encerramento Ordem Manutenção', max_length=50, blank=True, null=True)
    dt_aberordser = models.CharField('Data Abertura Ordem Serviço', max_length=50, blank=True, null=True)
    
    # Datas de Parada de Manutenção
    dt_iniparmanu = models.CharField('Data Início Parada Manutenção', max_length=50, blank=True, null=True)
    dt_fimparmanu = models.CharField('Data Fim Parada Manutenção', max_length=50, blank=True, null=True)
    
    # Data Prevista Execução
    dt_prev_exec = models.CharField('Data Prevista Execução', max_length=50, blank=True, null=True)
    
    # Tipo de Ordem de Serviço
    cd_tpordservtv = models.IntegerField('Código Tipo Ordem Serviço', blank=True, null=True)
    descr_tpordservtv = models.CharField('Descrição Tipo Ordem Serviço', max_length=255, blank=True, null=True)
    descr_sitordsetv = models.CharField('Descrição Situação Ordem Serviço', max_length=255, blank=True, null=True)
    
    # Recomendações e Sequência
    descr_recomenos = models.TextField('Descrição Recomendações OS', blank=True, null=True)
    descr_seqplamanu = models.CharField('Descrição Sequência Plano Manutenção', max_length=255, blank=True, null=True)
    
    # Tipo de Manutenção
    cd_tpmanuttv = models.IntegerField('Código Tipo Manutenção', blank=True, null=True)
    descr_tpmanuttv = models.CharField('Descrição Tipo Manutenção', max_length=255, blank=True, null=True)
    
    # Classificação Origem OS
    cd_clasorigos = models.IntegerField('Código Classificação Origem OS', blank=True, null=True)
    descr_clasorigos = models.CharField('Descrição Classificação Origem OS', max_length=255, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Ordem de Serviço Lubrificação'
        verbose_name_plural = 'Ordens de Serviço Lubrificação'
        ordering = ['-cd_ordemserv']

    def __str__(self):
        return f"{self.cd_ordemserv} - {self.descr_maquina or 'Sem descrição'}"

class OrdemServicoLubrificacaoFicha(models.Model):
    """Modelo para armazenar fichas/apontamentos de manutenção associadas a ordens de lubrificação.
    Permite múltiplas fichas para a mesma ordem de serviço."""
    ordem_servico = models.ForeignKey(
        OrdemServicoLubrificacao,
        on_delete=models.CASCADE,
        verbose_name='Ordem de Serviço',
        related_name='fichas'
    )
    
    # Funcionário Executor OS
    cd_func_exec_os = models.CharField('Código Funcionário Executor OS', max_length=100, blank=True, null=True)
    nm_func_exec_os = models.CharField('Nome Funcionário Executor OS', max_length=255, blank=True, null=True)
    
    # Datas de Ficha de Manutenção (Apontamento)
    dt_ficapomanu = models.CharField('Data Ficha Ponto Manutenção', max_length=50, blank=True, null=True)
    dt_inic_iteficmanu = models.CharField('Data Início Item Ficha Manutenção', max_length=50, blank=True, null=True)
    dt_fim_iteficmanu = models.CharField('Data Fim Item Ficha Manutenção', max_length=50, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Ficha de Lubrificação'
        verbose_name_plural = 'Fichas de Lubrificação'
        ordering = ['-created_at']

    def __str__(self):
        return f"Ficha OS {self.ordem_servico.cd_ordemserv} - {self.nm_func_exec_os or 'Sem executor'}"

class CentroAtividade(models.Model):
    """Modelo para armazenar informações de Centros de Atividade (CA)"""
    ca = models.IntegerField('CA', unique=True, db_index=True)
    sigla = models.CharField('Sigla', max_length=50, blank=True, null=True)
    descricao = models.CharField('Descrição', max_length=500, blank=True, null=True)
    indice = models.IntegerField('Índice', blank=True, null=True)
    encarregado_responsavel = models.CharField('Encarregado Responsável', max_length=255, blank=True, null=True)
    local = models.CharField('Local', max_length=255, blank=True, null=True, help_text='Local do Centro de Atividade')
    observacoes = models.TextField('Observações', blank=True, null=True, help_text='Observações sobre o local')
    imagem = models.CharField('Imagem', max_length=500, blank=True, null=True, help_text='Caminho da imagem (relativo a static/)')
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Centro de Atividade'
        verbose_name_plural = 'Centros de Atividade'
        ordering = ['ca']

    def __str__(self):
        return f"{self.ca} - {self.sigla or self.descricao or 'Sem descrição'}"

class Semana52(models.Model):
    """Modelo para armazenar informações das 52 semanas do ano"""
    semana = models.CharField('Semana', max_length=100, db_index=True)
    inicio = models.DateField('Data Início', blank=True, null=True, db_index=True)
    fim = models.DateField('Data Fim', blank=True, null=True)
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Semana 52'
        verbose_name_plural = 'Semanas 52'
        ordering = ['inicio']
        # Constraint única composta: mesma semana com mesma data de início é considerada duplicada
        unique_together = [['semana', 'inicio']]

    def __str__(self):
        return f"{self.semana} - {self.inicio} a {self.fim}"

class Manutentor(models.Model):
    """Modelo para armazenar informações de manutentores"""
    Matricula = models.CharField('Matrícula', max_length=1000, primary_key=True)
    Nome = models.CharField('Nome', max_length=1000, null=True, blank=True)
    Cargo = models.CharField('Cargo', max_length=1000, null=True, blank=True)
    horario_inicio = models.TimeField('Horário Início', blank=True, null=True)
    horario_fim = models.TimeField('Horário Fim', blank=True, null=True)
    tempo_trabalho = models.CharField('Tempo de Trabalho', max_length=250)
    turno = models.CharField('Turno', max_length=25, choices=TURNO)
    local_trab = models.CharField('Local de Trabalho', max_length=40, choices=LOCAL_TRABALHO)
    ativo = models.BooleanField('Ativo', default=True, db_index=True, help_text='Indica se o manutentor faz parte da equipe')
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Manutentor'
        verbose_name_plural = 'Manutentores'
        ordering = ['Nome', 'Matricula']

    def __str__(self):
        return f"{self.Matricula} - {self.Nome or 'Sem nome'}"

class ManutentorMaquina(models.Model):
    """Modelo para relacionar manutentores com máquinas"""
    manutentor = models.ForeignKey(Manutentor, on_delete=models.CASCADE, verbose_name='Manutentor', related_name='maquinas')
    maquina = models.ForeignKey(Maquina, on_delete=models.CASCADE, verbose_name='Máquina', related_name='manutentores')
    observacoes = models.TextField('Observações', blank=True, null=True, help_text='Observações sobre o relacionamento')
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Máquina do Manutentor'
        verbose_name_plural = 'Máquinas dos Manutentores'
        unique_together = ['manutentor', 'maquina']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.manutentor.Matricula} - {self.maquina.cd_maquina}"

class ItemEstoque(models.Model):
    """Modelo para armazenar informações de itens de estoque"""
    estante = models.IntegerField('Estante', blank=True, null=True)
    prateleira = models.IntegerField('Prateleira', blank=True, null=True)
    coluna = models.IntegerField('Coluna', blank=True, null=True)
    sequencia = models.IntegerField('Sequência', blank=True, null=True)
    descricao_dest_uso = models.CharField('Descrição Destino Uso', max_length=255, blank=True, null=True)
    codigo_item = models.BigIntegerField('Código Item', unique=True, db_index=True)
    descricao_item = models.CharField('Descrição Item', max_length=500, blank=True, null=True)
    unidade_medida = models.CharField('Unidade Medida', max_length=50, blank=True, null=True)
    quantidade = models.DecimalField('Quantidade', max_digits=15, decimal_places=2, default=0)
    valor = models.DecimalField('Valor', max_digits=15, decimal_places=2, default=0)
    controla_estoque_minimo = models.CharField('Controla Estoque Mínimo', max_length=10, blank=True, null=True)
    classificacao_tempo_sem_consumo = models.CharField('Classificação Tempo Sem Consumo', max_length=255, blank=True, null=True)
    foto_item = models.ImageField('Foto do Item', upload_to='estoque/fotos/', blank=True, null=True, help_text='Foto do item de estoque')
    documentacao_tecnica = models.FileField('Documentação Técnica', upload_to='estoque/documentacao/', blank=True, null=True, help_text='Documentação técnica em PDF')
    foto_detalhada = models.ImageField('Foto Detalhada', upload_to='estoque/fotos_detalhadas/', blank=True, null=True, help_text='Foto detalhada do item')
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Item de Estoque'
        verbose_name_plural = 'Itens de Estoque'
        ordering = ['codigo_item']

    def __str__(self):
        return f"{self.codigo_item} - {self.descricao_item or 'Sem descrição'}"
    
    @property
    def valor_total(self):
        """Calcula o valor total (quantidade * valor unitário)"""
        from decimal import Decimal
        return Decimal(str(self.quantidade)) * Decimal(str(self.valor))

class ManutencaoCsv(models.Model):
    """Modelo temporário para referência de OS importada - ajustar conforme necessário"""
    # Este modelo precisa ser definido com os campos apropriados
    # Por enquanto, apenas um campo básico para permitir a ForeignKey
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Manutenção CSV'
        verbose_name_plural = 'Manutenções CSV'

    def __str__(self):
        return f"Manutenção CSV #{self.id}"

class ManutencaoTerceiro(models.Model):
    """Modelo para armazenar informações de manutenções de terceiros"""
    titulo = models.CharField('Título', max_length=150)
    os = models.CharField('OS', max_length=150, null=True, blank=True)
    empresa = models.CharField('Empresa', max_length=150)
    pedidodecompra = models.CharField('Pedido de Compra', max_length=150)
    requisicaodecompra = models.CharField('Requisição de Compra', max_length=150)
    manutentor = models.ForeignKey(Manutentor, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Manutentor')
    os_importada = models.ForeignKey(ManutencaoCsv, on_delete=models.CASCADE, null=True, blank=True, verbose_name='OS Importada')
    maquina = models.ForeignKey(Maquina, null=False, on_delete=models.CASCADE, verbose_name='Máquina')
    tipo = models.CharField('Tipo', max_length=25, choices=TIPO_MANUTENCAO, blank=False, default='Corretiva')
    data = models.DateTimeField('Data', blank=True, null=True)
    descricao = models.CharField('Descrição', max_length=250, null=True, blank=True)
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Manutenção Terceiro'
        verbose_name_plural = 'Manutenções Terceiros'
        ordering = ['-data', '-created_at']

    def __str__(self):
        return self.titulo

class MaquinaPeca(models.Model):
    """Modelo para relacionar máquinas com peças de estoque"""
    maquina = models.ForeignKey(Maquina, on_delete=models.CASCADE, verbose_name='Máquina', related_name='pecas')
    item_estoque = models.ForeignKey(ItemEstoque, on_delete=models.CASCADE, verbose_name='Item de Estoque', related_name='maquinas')
    quantidade = models.DecimalField('Quantidade', max_digits=15, decimal_places=2, default=1, help_text='Quantidade necessária desta peça para a máquina')
    observacoes = models.TextField('Observações', blank=True, null=True, help_text='Observações sobre o uso desta peça na máquina')
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Peça de Máquina'
        verbose_name_plural = 'Peças de Máquinas'
        unique_together = ['maquina', 'item_estoque']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.maquina.cd_maquina} - {self.item_estoque.descricao_item or self.item_estoque.codigo_item}"

class MaquinaPrimariaSecundaria(models.Model):
    """Modelo para relacionar máquinas primárias com máquinas secundárias"""
    maquina_primaria = models.ForeignKey(
        Maquina, 
        on_delete=models.CASCADE, 
        verbose_name='Máquina Primária', 
        related_name='maquinas_secundarias'
    )
    maquina_secundaria = models.ForeignKey(
        Maquina, 
        on_delete=models.CASCADE, 
        verbose_name='Máquina Secundária', 
        related_name='maquinas_primarias'
    )
    observacoes = models.TextField('Observações', blank=True, null=True, help_text='Observações sobre o relacionamento')
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Máquina Primária e Secundária'
        verbose_name_plural = 'Máquinas Primárias e Secundárias'
        unique_together = ['maquina_primaria', 'maquina_secundaria']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.maquina_primaria.cd_maquina} - {self.maquina_secundaria.cd_maquina}"

class PlanoPreventiva(models.Model):
    """Modelo para armazenar dados de plano de manutenção preventiva"""
    # Unidade
    cd_unid = models.IntegerField('Código Unidade', blank=True, null=True)
    nome_unid = models.CharField('Nome Unidade', max_length=255, blank=True, null=True)
    
    # Setor
    cd_setor = models.CharField('Código Setor', max_length=50, blank=True, null=True)
    descr_setor = models.CharField('Descrição Setor', max_length=255, blank=True, null=True)
    
    # Atividade
    cd_atividade = models.IntegerField('Código Atividade', blank=True, null=True)
    
    # Máquina
    cd_maquina = models.BigIntegerField('Código Máquina', blank=True, null=True, db_index=True)
    descr_maquina = models.CharField('Descrição Máquina', max_length=500, blank=True, null=True)
    nro_patrimonio = models.CharField('Número Patrimônio', max_length=100, blank=True, null=True)
    
    # Plano
    numero_plano = models.IntegerField('Número do Plano', blank=True, null=True)
    descr_plano = models.CharField('Descrição do Plano', max_length=255, blank=True, null=True)
    sequencia_manutencao = models.IntegerField('Sequência Manutenção', blank=True, null=True)
    
    # Execução
    dt_execucao = models.CharField('Data Execução', max_length=50, blank=True, null=True, help_text='Data no formato DD/MM/YYYY')
    quantidade_periodo = models.IntegerField('Quantidade Período', blank=True, null=True, help_text='Período em dias')
    
    # Tarefa
    sequencia_tarefa = models.IntegerField('Sequência Tarefa', blank=True, null=True)
    descr_tarefa = models.TextField('Descrição Tarefa', blank=True, null=True)
    
    # Funcionário
    cd_funcionario = models.CharField('Código Funcionário', max_length=100, blank=True, null=True)
    nome_funcionario = models.CharField('Nome Funcionário', max_length=255, blank=True, null=True)
    
    # Descrição Sequência Plano Manutenção (vinculada do RoteiroPreventiva)
    descr_seqplamanu = models.CharField('Descrição Sequência Plano Manutenção', max_length=255, blank=True, null=True, help_text='Descrição precisa da ação a ser realizada, vinculada do RoteiroPreventiva')
    
    # Relacionamento com máquina (opcional, para facilitar consultas)
    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Máquina Relacionada',
        related_name='planos_preventiva',
        help_text='Máquina relacionada baseada no código da máquina'
    )
    
    # Relacionamento com RoteiroPreventiva (opcional, para vincular descrição precisa)
    roteiro_preventiva = models.ForeignKey(
        'RoteiroPreventiva',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Roteiro Preventiva Relacionado',
        related_name='planos_preventiva',
        help_text='Roteiro preventiva relacionado que contém a descrição precisa (DESCR_SEQPLAMANU)'
    )
    
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Plano Preventiva'
        verbose_name_plural = 'Planos Preventiva'
        ordering = ['cd_maquina', 'numero_plano', 'sequencia_manutencao', 'sequencia_tarefa']
        indexes = [
            models.Index(fields=['cd_maquina']),
            models.Index(fields=['cd_unid', 'cd_setor']),
        ]

    def __str__(self):
        return f"Plano {self.numero_plano} - Máquina {self.cd_maquina} - Seq {self.sequencia_manutencao}"

class MeuPlanoPreventiva(models.Model):
    """Modelo para armazenar dados de plano de manutenção preventiva com descrição detalhada do roteiro"""
    # Unidade
    cd_unid = models.IntegerField('Código Unidade', blank=True, null=True)
    nome_unid = models.CharField('Nome Unidade', max_length=255, blank=True, null=True)
    
    # Setor
    cd_setor = models.CharField('Código Setor', max_length=50, blank=True, null=True)
    descr_setor = models.CharField('Descrição Setor', max_length=255, blank=True, null=True)
    
    # Atividade
    cd_atividade = models.IntegerField('Código Atividade', blank=True, null=True)
    
    # Máquina
    cd_maquina = models.BigIntegerField('Código Máquina', blank=True, null=True, db_index=True)
    descr_maquina = models.CharField('Descrição Máquina', max_length=500, blank=True, null=True)
    nro_patrimonio = models.CharField('Número Patrimônio', max_length=100, blank=True, null=True)
    
    # Plano
    numero_plano = models.IntegerField('Número do Plano', blank=True, null=True)
    descr_plano = models.CharField('Descrição do Plano', max_length=255, blank=True, null=True)
    sequencia_manutencao = models.IntegerField('Sequência Manutenção', blank=True, null=True)
    
    # Execução
    dt_execucao = models.CharField('Data Execução', max_length=50, blank=True, null=True, help_text='Data no formato DD/MM/YYYY')
    quantidade_periodo = models.IntegerField('Quantidade Período', blank=True, null=True, help_text='Período em dias')
    
    # Tarefa
    sequencia_tarefa = models.IntegerField('Sequência Tarefa', blank=True, null=True)
    descr_tarefa = models.TextField('Descrição Tarefa', blank=True, null=True)
    
    # Funcionário
    cd_funcionario = models.CharField('Código Funcionário', max_length=100, blank=True, null=True)
    nome_funcionario = models.CharField('Nome Funcionário', max_length=255, blank=True, null=True)
    
    # Descrição Sequência Plano Manutenção (vinculada do RoteiroPreventiva)
    descr_seqplamanu = models.CharField('Descrição Sequência Plano Manutenção', max_length=255, blank=True, null=True, help_text='Descrição precisa da ação a ser realizada, vinculada do RoteiroPreventiva')
    
    # Descrição Detalhada do Roteiro Preventiva (campo adicional)
    desc_detalhada_do_roteiro_preventiva = models.TextField('Descrição Detalhada do Roteiro Preventiva', blank=True, null=True, help_text='Descrição detalhada do roteiro de manutenção preventiva')
    
    # Relacionamento com máquina (opcional, para facilitar consultas)
    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Máquina Relacionada',
        related_name='meus_planos_preventiva',
        help_text='Máquina relacionada baseada no código da máquina'
    )
    
    # Relacionamento com RoteiroPreventiva (opcional, para vincular descrição precisa)
    roteiro_preventiva = models.ForeignKey(
        'RoteiroPreventiva',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Roteiro Preventiva Relacionado',
        related_name='meus_planos_preventiva',
        help_text='Roteiro preventiva relacionado que contém a descrição precisa (DESCR_SEQPLAMANU)'
    )
    
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Meu Plano Preventiva'
        verbose_name_plural = 'Meus Planos Preventiva'
        ordering = ['cd_maquina', 'numero_plano', 'sequencia_manutencao', 'sequencia_tarefa']
        indexes = [
            models.Index(fields=['cd_maquina']),
            models.Index(fields=['cd_unid', 'cd_setor']),
        ]

    def __str__(self):
        return f"Meu Plano {self.numero_plano} - Máquina {self.cd_maquina} - Seq {self.sequencia_manutencao}"

class MeuPlanoPreventivaDocumento(models.Model):
    """Modelo para associar documentos de máquinas (MaquinaDocumento) a MeuPlanoPreventiva"""
    meu_plano_preventiva = models.ForeignKey(
        MeuPlanoPreventiva,
        on_delete=models.CASCADE,
        verbose_name='Meu Plano Preventiva',
        related_name='documentos_associados'
    )
    maquina_documento = models.ForeignKey(
        'MaquinaDocumento',
        on_delete=models.CASCADE,
        verbose_name='Documento da Máquina',
        related_name='meus_planos_preventiva_associados',
        help_text='Documento da máquina associado a este plano'
    )
    comentario = models.TextField(
        'Comentário Adicional',
        blank=True,
        null=True,
        help_text='Comentário adicional sobre esta associação (opcional)'
    )
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Documento Associado ao Plano PCM'
        verbose_name_plural = 'Documentos Associados aos Planos PCM'
        ordering = ['-created_at']
        unique_together = ['meu_plano_preventiva', 'maquina_documento']  # Evitar duplicatas

    def __str__(self):
        nome_arquivo = self.maquina_documento.arquivo.name.split('/')[-1] if self.maquina_documento.arquivo else 'Sem arquivo'
        return f"Plano {self.meu_plano_preventiva.numero_plano} - {nome_arquivo}"

class AgendamentoCronograma(models.Model):
    """Modelo para agendar máquinas ou planos preventiva em uma data específica no cronograma planejado"""
    TIPO_AGENDAMENTO = (
        ('maquina', 'Máquina'),
        ('plano', 'Plano Preventiva'),
    )
    
    tipo_agendamento = models.CharField(
        'Tipo de Agendamento',
        max_length=10,
        choices=TIPO_AGENDAMENTO,
        help_text='Tipo de item agendado: Máquina ou Plano Preventiva'
    )
    
    # Relacionamento com Máquina (quando tipo_agendamento = 'maquina')
    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name='Máquina',
        related_name='agendamentos_cronograma',
        help_text='Máquina agendada (usado quando tipo_agendamento = "maquina")'
    )
    
    # Relacionamento com MeuPlanoPreventiva (quando tipo_agendamento = 'plano')
    plano_preventiva = models.ForeignKey(
        MeuPlanoPreventiva,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name='Plano Preventiva',
        related_name='agendamentos_cronograma',
        help_text='Plano Preventiva agendado (usado quando tipo_agendamento = "plano")'
    )
    
    # Nome do grupo de agendamento
    nome_grupo = models.CharField(
        'Nome do Grupo',
        max_length=255,
        blank=True,
        null=True,
        help_text='Nome identificador para este grupo de agendamentos (ex: "Manutenção Preventiva - Setor A")'
    )
    
    # Periodicidade em dias
    periodicidade = models.IntegerField(
        'Periodicidade (dias)',
        blank=True,
        null=True,
        help_text='Número de dias entre cada repetição do agendamento até o final do ano'
    )
    
    # Data planejada para execução
    data_planejada = models.DateField(
        'Data Planejada',
        help_text='Data planejada para execução do agendamento'
    )
    
    # Relacionamento opcional com Semana52
    semana = models.ForeignKey(
        'Semana52',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Semana',
        related_name='agendamentos',
        help_text='Semana do ano relacionada (calculada automaticamente baseada na data_planejada)'
    )
    
    # Observações adicionais
    observacoes = models.TextField(
        'Observações',
        blank=True,
        null=True,
        help_text='Observações adicionais sobre este agendamento'
    )
    
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)
    created_by = models.CharField('Criado por', max_length=255, blank=True, null=True, help_text='Usuário que criou o agendamento')
    
    class Meta:
        verbose_name = 'Agendamento de Cronograma'
        verbose_name_plural = 'Agendamentos de Cronograma'
        ordering = ['data_planejada', 'tipo_agendamento']
        indexes = [
            models.Index(fields=['data_planejada']),
            models.Index(fields=['tipo_agendamento']),
            models.Index(fields=['maquina']),
            models.Index(fields=['plano_preventiva']),
        ]
    
    def clean(self):
        """Validação: deve ter máquina OU plano, dependendo do tipo"""
        if self.tipo_agendamento == 'maquina' and not self.maquina:
            raise models.ValidationError('Quando o tipo é "maquina", é necessário informar a máquina.')
        if self.tipo_agendamento == 'plano' and not self.plano_preventiva:
            raise models.ValidationError('Quando o tipo é "plano", é necessário informar o plano preventiva.')
        if self.tipo_agendamento == 'maquina' and self.plano_preventiva:
            raise models.ValidationError('Não é possível ter máquina e plano ao mesmo tempo.')
        if self.tipo_agendamento == 'plano' and self.maquina:
            raise models.ValidationError('Não é possível ter máquina e plano ao mesmo tempo.')
    
    def save(self, *args, **kwargs):
        """Sobrescrever save para calcular semana automaticamente"""
        from app.models import Semana52
        if self.data_planejada:
            # Tentar encontrar a semana correspondente
            semana_encontrada = Semana52.objects.filter(
                inicio__lte=self.data_planejada,
                fim__gte=self.data_planejada
            ).first()
            self.semana = semana_encontrada
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.tipo_agendamento == 'maquina' and self.maquina:
            return f"Máquina {self.maquina.cd_maquina} - {self.data_planejada.strftime('%d/%m/%Y')}"
        elif self.tipo_agendamento == 'plano' and self.plano_preventiva:
            return f"Plano {self.plano_preventiva.numero_plano} - Máquina {self.plano_preventiva.cd_maquina} - {self.data_planejada.strftime('%d/%m/%Y')}"
        return f"Agendamento {self.tipo_agendamento} - {self.data_planejada.strftime('%d/%m/%Y')}"

class PlanoPreventivaDocumento(models.Model):
    """Modelo para armazenar documentos relacionados a planos de manutenção preventiva"""
    plano_preventiva = models.ForeignKey(
        PlanoPreventiva, 
        on_delete=models.CASCADE, 
        verbose_name='Plano Preventiva', 
        related_name='documentos'
    )
    arquivo = models.FileField(
        'Arquivo', 
        upload_to='planos_preventiva/documentos/', 
        help_text='Upload de arquivo relacionado ao plano preventiva (PDF, imagens, etc.)'
    )
    comentario = models.TextField(
        'Comentário', 
        blank=True, 
        null=True, 
        help_text='Comentário sobre o documento'
    )
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Documento do Plano Preventiva'
        verbose_name_plural = 'Documentos do Plano Preventiva'
        ordering = ['-created_at']

    def __str__(self):
        nome_arquivo = self.arquivo.name.split('/')[-1] if self.arquivo else 'Sem arquivo'
        return f"{self.plano_preventiva.numero_plano} - {nome_arquivo}"

class RoteiroPreventiva(models.Model):
    """Modelo para armazenar dados de roteiro de manutenção preventiva"""
    # Unidade
    cd_unid = models.IntegerField('Código Unidade', blank=True, null=True)
    nome_unid = models.CharField('Nome Unidade', max_length=255, blank=True, null=True)
    
    # Funcionário
    cd_funciomanu = models.CharField('Código Funcionário Manutenção', max_length=100, blank=True, null=True) 
    nome_funciomanu = models.CharField('Nome Funcionário Manutenção', max_length=255, blank=True, null=True) 
    funciomanu_id = models.IntegerField('ID Funcionário Manutenção', blank=True, null=True) 
    
    # Setor
    cd_setormanut = models.CharField('Código Setor Manutenção', max_length=50, blank=True, null=True) 
    descr_setormanut = models.CharField('Descrição Setor Manutenção', max_length=255, blank=True, null=True) 
    
    # Tipo Centro de Atividade
    cd_tpcentativ = models.IntegerField('Código Tipo Centro Atividade', blank=True, null=True) 
    descr_abrev_tpcentativ = models.CharField('Descrição Abreviada Tipo Centro Atividade', max_length=255, blank=True, null=True) 
    
    # Ordem de Serviço
    dt_abertura = models.CharField('Data Abertura', max_length=50, blank=True, null=True, help_text='Data no formato DD/MM/YYYY') 
    cd_ordemserv = models.IntegerField('Código Ordem Serviço', blank=True, null=True) 
    ordemserv_id = models.IntegerField('ID Ordem Serviço', blank=True, null=True) 
    
    # Máquina
    cd_maquina = models.BigIntegerField('Código Máquina', blank=True, null=True, db_index=True) 
    descr_maquina = models.CharField('Descrição Máquina', max_length=500, blank=True, null=True) 
    
    # Plano de Manutenção
    cd_planmanut = models.IntegerField('Código Plano Manutenção', blank=True, null=True)
    descr_planmanut = models.CharField('Descrição Plano Manutenção', max_length=255, blank=True, null=True)
    descr_recomenos = models.TextField('Descrição Recomendações', blank=True, null=True)
    cf_dt_final_execucao = models.CharField('Data Final Execução', max_length=50, blank=True, null=True, help_text='Data no formato DD/MM/YYYY')
    cs_qtde_periodo_max = models.IntegerField('Quantidade Período Máximo', blank=True, null=True)
    cs_tot_temp = models.CharField('Total Tempo (Calculado)', max_length=50, blank=True, null=True, help_text='Tempo no formato HH:MM')
    cf_tot_temp = models.CharField('Total Tempo (Final)', max_length=50, blank=True, null=True, help_text='Tempo no formato HH:MM')
    
    # Sequência Plano Manutenção
    seq_seqplamanu = models.IntegerField('Sequência Plano Manutenção', blank=True, null=True)
    
    # Tarefa Manutenção
    cd_tarefamanu = models.IntegerField('Código Tarefa Manutenção', blank=True, null=True)
    descr_tarefamanu = models.TextField('Descrição Tarefa Manutenção', blank=True, null=True)
    descr_periodo = models.CharField('Descrição Período', max_length=255, blank=True, null=True)
    
    # Execução
    dt_primexec = models.CharField('Data Primeira Execução', max_length=50, blank=True, null=True, help_text='Data no formato DD/MM/YYYY')
    tempo_prev = models.CharField('Tempo Preventivo', max_length=50, blank=True, null=True, help_text='Tempo no formato HH:MM')
    qtde_periodo = models.IntegerField('Quantidade Período', blank=True, null=True, help_text='Período em dias')
    descr_seqplamanu = models.CharField('Descrição Sequência Plano Manutenção', max_length=255, blank=True, null=True)
    cf_temp_prev = models.CharField('Tempo Preventivo (Final)', max_length=50, blank=True, null=True, help_text='Tempo no formato HH:MM')
    
    # Item do Plano
    itemplanma_id = models.IntegerField('ID Item Plano Manutenção', blank=True, null=True)
    cd_item = models.IntegerField('Código Item', blank=True, null=True)
    descr_item = models.CharField('Descrição Item', max_length=500, blank=True, null=True)
    item_id = models.IntegerField('ID Item', blank=True, null=True)
    qtde = models.IntegerField('Quantidade', blank=True, null=True)
    qtde_saldo = models.IntegerField('Quantidade Saldo', blank=True, null=True)
    qtde_reserva = models.IntegerField('Quantidade Reserva', blank=True, null=True)
    
    # Relacionamento com máquina (opcional, para facilitar consultas)
    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Máquina Relacionada',
        related_name='roteiros_preventiva',
        help_text='Máquina relacionada baseada no código da máquina'
    )
    
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Roteiro Preventiva'
        verbose_name_plural = 'Roteiros Preventiva'
        ordering = ['cd_maquina', 'cd_planmanut', 'seq_seqplamanu', 'cd_tarefamanu']
        indexes = [
            models.Index(fields=['cd_maquina']),
            models.Index(fields=['cd_unid', 'cd_setormanut']),
            models.Index(fields=['cd_ordemserv']),
            models.Index(fields=['cd_planmanut']),
        ]

    def __str__(self):
        return f"Roteiro - Máquina {self.cd_maquina} - Plano {self.cd_planmanut} - Seq {self.seq_seqplamanu}"

class RequisicaoAlmoxarifado(models.Model):
    """Modelo para armazenar requisições de itens retirados do almoxarifado"""
    # Data da requisição (fornecida pelo usuário durante a importação)
    data_requisicao = models.DateField(
        'Data da Requisição',
        help_text='Data em que os itens foram retirados do estoque'
    )
    
    # Dados da unidade
    cd_unid = models.IntegerField('Código Unidade', blank=True, null=True)
    nome_unid = models.CharField('Nome Unidade', max_length=255, blank=True, null=True)
    
    # Dados de uso contábil
    cd_uso_ctb = models.IntegerField('Código Uso Contábil', blank=True, null=True)
    descr_uso_ctb = models.CharField('Descrição Uso Contábil', max_length=255, blank=True, null=True)
    
    # Dados do depósito
    cd_depo = models.IntegerField('Código Depósito', blank=True, null=True)
    descr_depo = models.CharField('Descrição Depósito', max_length=255, blank=True, null=True)
    
    # Dados do local físico
    cd_local_fisic = models.IntegerField('Código Local Físico', blank=True, null=True)
    descr_local_fisic = models.CharField('Descrição Local Físico', max_length=255, blank=True, null=True)
    
    # Dados do item
    cd_item = models.BigIntegerField('Código Item', db_index=True)
    cd_embalagem = models.CharField('Código Embalagem', max_length=50, blank=True, null=True)
    descr_item = models.CharField('Descrição Item', max_length=500, blank=True, null=True)
    
    # Dados da operação
    cd_operacao = models.IntegerField('Código Operação', blank=True, null=True)
    descr_operacao = models.CharField('Descrição Operação', max_length=255, blank=True, null=True)
    
    # Dados de unidade de medida
    cd_unid_medida = models.CharField('Código Unidade Medida', max_length=50, blank=True, null=True)
    
    # Quantidade e valores
    qtde_movto_estoq = models.DecimalField(
        'Quantidade Movimento Estoque',
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Quantidade movimentada (geralmente negativa para saída)'
    )
    vlr_movto_estoq = models.DecimalField(
        'Valor Movimento Estoque',
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True
    )
    vlr_movto_estoq_reav = models.DecimalField(
        'Valor Movimento Estoque Reavaliação',
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True
    )
    
    # Dados adicionais
    cd_unid_baixa = models.IntegerField('Código Unidade Baixa', blank=True, null=True)
    cd_centro_ativ = models.IntegerField('Código Centro Atividade', blank=True, null=True)
    cd_usu_criou = models.CharField('Código Usuário Criou', max_length=255, blank=True, null=True)
    cd_usu_atend = models.CharField('Código Usuário Atendeu', max_length=255, blank=True, null=True)
    obs_rm = models.TextField('Observação RM', blank=True, null=True)
    obs_item = models.TextField('Observação Item', blank=True, null=True)
    
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Requisição Almoxarifado'
        verbose_name_plural = 'Requisições Almoxarifado'
        ordering = ['-data_requisicao', '-created_at']
        indexes = [
            models.Index(fields=['data_requisicao']),
            models.Index(fields=['cd_item']),
            models.Index(fields=['cd_centro_ativ']),
        ]
    
    @property
    def valor_total(self):
        """Calcula o valor total (quantidade * valor unitário) usando valores absolutos"""
        from decimal import Decimal
        if self.qtde_movto_estoq and self.vlr_movto_estoq:
            qtd_abs = abs(self.qtde_movto_estoq)
            vlr_abs = abs(self.vlr_movto_estoq)
            return qtd_abs * vlr_abs
        return Decimal('0.00')

    @property
    def valor_contribuicao_custo(self):
        """Valor que contribui para o custo/gasto real.
        Na tabela: vlr_movto_estoq negativo = saída (gasto), positivo = devolução (retorno ao estoque).
        Para custo: gastos somam, devoluções subtraem. Retorna -vlr_movto_estoq."""
        from decimal import Decimal
        v = self.vlr_movto_estoq or Decimal('0')
        return -v

    def __str__(self):
        return f"Requisição {self.cd_item} - {self.data_requisicao}"

class NotaFiscal(models.Model):
    """Modelo para armazenar informações de notas fiscais"""
    # Dados do Emitente
    emitente = models.CharField('Emitente (CNPJ)', max_length=100, blank=True, null=True, db_index=True)
    nome_fantasia_emitente = models.CharField('Nome Fantasia Emitente', max_length=500, blank=True, null=True)
    
    # Dados da Nota Fiscal
    nota = models.CharField('Número da Nota', max_length=50, blank=True, null=True, db_index=True)
    serie = models.CharField('Série', max_length=50, blank=True, null=True)
    modelo = models.CharField('Modelo', max_length=50, blank=True, null=True)
    total_nota = models.DecimalField('Total da Nota', max_digits=15, decimal_places=2, blank=True, null=True)
    uso_contabil = models.CharField('Uso Contábil', max_length=100, blank=True, null=True)
    
    # Datas
    data_emissao = models.CharField('Data Emissão', max_length=50, blank=True, null=True)
    data_vencimento = models.CharField('Data Vencimento', max_length=50, blank=True, null=True)
    data_inclusao = models.CharField('Data Inclusão', max_length=50, blank=True, null=True)
    data_autorizacao = models.CharField('Data Autorização', max_length=50, blank=True, null=True)
    data_ult_sit_fechada = models.CharField('Data Última Situação Fechada', max_length=50, blank=True, null=True)
    
    # Dados de Controle
    ctrle = models.CharField('Controle', max_length=50, blank=True, null=True)
    
    # Dados da Unidade
    unidade = models.CharField('Unidade', max_length=50, blank=True, null=True)
    nome_unidade = models.CharField('Nome Unidade', max_length=255, blank=True, null=True)
    unidade_autorizacao = models.CharField('Unidade Autorização', max_length=50, blank=True, null=True)
    nome_unidade_autorizacao = models.CharField('Nome Unidade Autorização', max_length=255, blank=True, null=True)
    
    # Dados do Centro de Atividade  
    centro_atividade = models.CharField('Centro Atividade', max_length=50, blank=True, null=True)
    nome_centro_atividade = models.CharField('Nome Centro Atividade', max_length=255, blank=True, null=True)
    
    # Situação
    situacao = models.CharField('Situação', max_length=100, blank=True, null=True, db_index=True)
    situacao_detalhada = models.TextField('Situação Detalhada', blank=True, null=True)
    
    # Usuário e Autorização
    nome_usuario = models.CharField('Nome Usuário', max_length=255, blank=True, null=True)
    autorizador = models.CharField('Autorizador', max_length=255, blank=True, null=True)
    
    # Observações
    observacoes = models.TextField('Observações', blank=True, null=True)
    observacoes_csc = models.TextField('Observações CSC', blank=True, null=True)
    observacoes_autorizacao = models.TextField('Observações Autorização', blank=True, null=True)
    
    # Lançamento
    lancamento_tesf0028 = models.CharField('Lançamento TESF0028', max_length=255, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Nota Fiscal'
        verbose_name_plural = 'Notas Fiscais'
        ordering = ['-data_emissao', '-created_at']
        # Constraint única composta: mesma nota com mesmo emitente, série e modelo
        unique_together = [['emitente', 'nota', 'serie', 'modelo']]
        indexes = [
            models.Index(fields=['situacao']),
            models.Index(fields=['data_emissao']),
            models.Index(fields=['unidade']),
        ]
    
    def __str__(self):
        return f"Nota {self.nota} - {self.nome_fantasia_emitente or self.emitente or 'Sem emitente'}"

class Visitas(models.Model):
    """Modelo para armazenar informações de visitas"""
    titulo = models.CharField('Título', max_length=250)
    data = models.DateTimeField('Data', blank=True, null=True)
    descricao = models.CharField('Descrição', max_length=1000, blank=True, null=True)
    nome_contato = models.CharField('Nome do Contato', max_length=250, null=True, blank=True)
    numero_contato = models.CharField('Número do Contato', max_length=250, null=True, blank=True)
    documento = models.FileField(
        'Documento',
        upload_to='evento/documento/',
        blank=True,
        null=True
    )
    
    # Timestamps
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Visita'
        verbose_name_plural = 'Visitas'
        ordering = ['-data', '-created_at']
        indexes = [
            models.Index(fields=['data']),
            models.Index(fields=['titulo']),
        ]
    
    def __str__(self):
        return f"{self.titulo} - {self.data.strftime('%d/%m/%Y') if self.data else 'Sem data'}"

class ProjecaoGasto(models.Model):
    """Modelo para armazenar informações de projeções de gastos e requisições de serviço"""
    # ID do Excel (identificador único do Excel combinado com setor)
    id_excel = models.IntegerField('ID Excel', db_index=True, null=False)  # ID do Excel - usado em combinação com setor para identificação única
    
    # Dados básicos
    setor = models.CharField('Setor', max_length=100, blank=True, null=True, db_index=True)  # SETOR do Excel
    solicitante = models.CharField('Solicitante', max_length=100, blank=True, null=True)  # SOLICITANTE (CNPJ)
    descricao = models.CharField('Descrição do Serviço', max_length=500, blank=True, null=True)  # DESCRIÇÃO DO SERVIÇO
    tipo_solicitacao = models.CharField('Tipo de Solicitação', max_length=100, blank=True, null=True, db_index=True)  # TIPO DE SOLICITAÇÃO do Excel
    
    # Dados financeiros
    valor_total = models.DecimalField('Valor Total', max_digits=15, decimal_places=2, blank=True, null=True)  # VALOR TOTAL
    
    # Datas
    data_abertura_requisicao = models.DateField('Data de Abertura da Requisição', blank=True, null=True, db_index=True)  # DATA DE ABERTURA DA REQUISIÇÃO
    previsao_execucao = models.CharField('Previsão para Execução', max_length=50, blank=True, null=True)  # PREVISÃO P/ EXECUÇÃO (ex: "DEZEMBRO / 2025")
    mes_referencia = models.CharField('Mês Referência', max_length=20, blank=True, null=True, db_index=True)  # Extraído de PREVISÃO
    ano_referencia = models.IntegerField('Ano Referência', blank=True, null=True, db_index=True)  # Extraído de PREVISÃO
    
    # Fornecedor
    fornecedor_nome_fantasia = models.CharField('Fornecedor Nome Fantasia', max_length=255, blank=True, null=True)  # FORNECEDOR\nNOME FANTASIA
    fornecedor_cnpj = models.CharField('Fornecedor CNPJ', max_length=20, blank=True, null=True)  # FORNECEDOR\nCNPJ
    
    # Dados adicionais
    uso_contabil = models.CharField('Uso Contábil', max_length=100, blank=True, null=True)  # USO CONTÁBIL
    numero_nf = models.CharField('Número da NF', max_length=100, blank=True, null=True)  # NÚMERO DA NF
    numero_ordem_servico = models.CharField('Número Ordem de Serviço', max_length=100, blank=True, null=True, db_index=True)  # ORDEM DE SERVIÇO
    numero_requisicao_compra = models.CharField('Número da Requisição de Compra', max_length=100, blank=True, null=True, db_index=True)  # NÚMERO DA REQUISIÇÃO DE COMPRA
    numero_pedido_compra = models.CharField('Número do Pedido de Compra', max_length=100, blank=True, null=True)  # NÚMERO DO PEDIDO DE COMPRA
    servico_concluido = models.CharField('Serviço Concluído', max_length=255, blank=True, null=True)  # SERVIÇO CONCLUÍDO (texto)
    nf_servico_recebida = models.CharField('NF de Serviço Recebida', max_length=255, blank=True, null=True)  # NF DE SERVIÇO RECEBIDA (texto)
    nf_enviada_lancamento = models.CharField('NF Enviada para Lançamento', max_length=255, blank=True, null=True)  # NF ENVIADA PARA LANÇAMENTO (texto)
    observacoes = models.TextField('Observações', blank=True, null=True)  # OBSERVAÇÕES do Excel
    
    # Campos flexíveis para armazenar dados adicionais do Excel
    dados_adicionais = models.JSONField('Dados Adicionais', blank=True, null=True, default=dict)
    
    # Timestamps
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Projeção de Gasto'
        verbose_name_plural = 'Projeções de Gastos'
        ordering = ['-ano_referencia', '-mes_referencia', '-data_abertura_requisicao', '-created_at']
        # Constraint única composta: id_excel + setor (mesmo ID pode existir para setores diferentes)
        unique_together = [['id_excel', 'setor']]
        indexes = [
            models.Index(fields=['setor']),
            models.Index(fields=['mes_referencia', 'ano_referencia']),
            models.Index(fields=['data_abertura_requisicao']),
            models.Index(fields=['numero_requisicao_compra']),
            models.Index(fields=['id_excel', 'setor']),  # Índice para a chave composta
        ]
    
    def __str__(self):
        id_str = f"ID {self.id_excel}" if self.id_excel else "Sem ID"
        tipo_str = self.tipo_solicitacao or 'Sem tipo'
        descricao_str = self.descricao or 'Sem descrição'
        return f"{id_str} - {tipo_str} - {descricao_str[:50]}"

class RelacaoProjecaoNotaFiscal(models.Model):
    """Modelo para armazenar relações confirmadas entre Projeções de Gastos, Notas Fiscais e Controle RC e NF"""
    projecao = models.ForeignKey(
        ProjecaoGasto,
        on_delete=models.CASCADE,
        related_name='relacoes_notas_fiscais',
        verbose_name='Projeção de Gasto'
    )
    nota_fiscal = models.ForeignKey(
        NotaFiscal,
        on_delete=models.CASCADE,
        related_name='relacoes_projecoes',
        verbose_name='Nota Fiscal'
    )
    controle_rc_nf = models.ForeignKey(
        'ControleRCeNF',
        on_delete=models.CASCADE,
        related_name='relacoes_projecoes_notas',
        verbose_name='Controle RC e NF',
        blank=True,
        null=True,
        help_text='Registro do Controle RC e NF relacionado (opcional)'
    )
    
    # Informações sobre a confirmação
    score_match = models.DecimalField(
        'Score do Match',
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Score percentual do match quando foi confirmado'
    )
    confirmado_por = models.CharField(
        'Confirmado por',
        max_length=255,
        blank=True,
        null=True,
        help_text='Usuário que confirmou a relação'
    )
    observacoes = models.TextField(
        'Observações',
        blank=True,
        null=True,
        help_text='Observações sobre a relação confirmada'
    )
    
    # Status da relação
    STATUS_CHOICES = [
        ('confirmado', 'Confirmado'),
        ('rejeitado', 'Rejeitado'),
        ('pendente', 'Pendente'),
    ]
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='confirmado',
        db_index=True
    )
    
    # Timestamps
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Relação Projeção vs Nota Fiscal'
        verbose_name_plural = 'Relações Projeção vs Nota Fiscal'
        ordering = ['-created_at']
        # Evitar duplicatas: uma projeção pode ter apenas uma relação confirmada com uma nota fiscal
        # Se controle_rc_nf for fornecido, também deve ser único na combinação
        unique_together = [['projecao', 'nota_fiscal', 'controle_rc_nf']]
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['projecao']),
            models.Index(fields=['nota_fiscal']),
            models.Index(fields=['controle_rc_nf']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.projecao} ↔ {self.nota_fiscal} ({self.get_status_display()})"

class DadosOrcamento(models.Model):
    """Modelo para armazenar dados de orçamento por ano, mês e conta orçamentária"""
    MES_CHOICES = [
        (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
        (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
        (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro'),
    ]
    
    ano = models.IntegerField('Ano', db_index=True)
    mes = models.IntegerField('Mês', choices=MES_CHOICES, db_index=True)
    conta_orcamentaria = models.CharField('Conta Orçamentária', max_length=255)
    valor_orcamento = models.DecimalField('Valor do Orçamento', max_digits=15, decimal_places=2, default=0)
    valor_final_desejado = models.DecimalField('Valor Final Desejado', max_digits=15, decimal_places=2, default=0)
    
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)
    created_by = models.CharField('Criado por', max_length=255, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Dado de Orçamento'
        verbose_name_plural = 'Dados de Orçamento'
        ordering = ['ano', 'mes', 'conta_orcamentaria']
        unique_together = [['ano', 'mes', 'conta_orcamentaria']]
        indexes = [
            models.Index(fields=['ano', 'mes']),
            models.Index(fields=['conta_orcamentaria']),
        ]
    
    def __str__(self):
        return f"{self.ano}/{self.mes:02d} - {self.conta_orcamentaria}"

class SaldoOrcamentarioSemanal(models.Model):
    """Modelo para armazenar o saldo orçamentário desejado por semana"""
    # Relacionamento com DadosOrcamento (ano, mês, conta orçamentária)
    ano = models.IntegerField('Ano', db_index=True)
    mes = models.IntegerField('Mês', choices=DadosOrcamento.MES_CHOICES, db_index=True)
    conta_orcamentaria = models.CharField('Conta Orçamentária', max_length=255, db_index=True)
    
    # Relacionamento com Semana52
    semana = models.ForeignKey(Semana52, on_delete=models.CASCADE, related_name='saldos_orcamentarios', verbose_name='Semana')
    
    # Valor do saldo orçamentário desejado para esta semana
    saldo_orcamentario_desejado = models.DecimalField('Saldo Orçamentário Desejado', max_digits=15, decimal_places=2, default=0)
    
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Saldo Orçamentário Semanal'
        verbose_name_plural = 'Saldos Orçamentários Semanais'
        ordering = ['ano', 'mes', 'conta_orcamentaria', 'semana__inicio']
        unique_together = [['ano', 'mes', 'conta_orcamentaria', 'semana']]
        indexes = [
            models.Index(fields=['ano', 'mes', 'conta_orcamentaria']),
            models.Index(fields=['semana']),
        ]
    
    def __str__(self):
        return f"{self.ano}/{self.mes:02d} - {self.conta_orcamentaria} - {self.semana.semana}: {self.saldo_orcamentario_desejado}"

class ControleRCeNF(models.Model): # Planilha de Controle RC e NF
    """Modelo para armazenar dados do controle de RC e NF"""
    # ID único do Excel (chave primária do registro na planilha)
    id_excel = models.CharField('ID', max_length=100, primary_key=True, db_index=True, help_text='ID único do registro na planilha Excel (chave primária)')
    
    # Dados básicos
    solicitante = models.CharField('Solicitante', max_length=255, blank=True, null=True)
    empresa = models.CharField('Empresa', max_length=255, blank=True, null=True)
    nf_saida = models.CharField('NF Saída', max_length=100, blank=True, null=True, db_index=True)
    descricao_servico = models.TextField('Descrição do Serviço', blank=True, null=True)
    ca_rateio = models.CharField('C.A/Rateio', max_length=100, blank=True, null=True)
    uso = models.CharField('Uso', max_length=50, blank=True, null=True)
    quem_abriu_rc = models.CharField('Quem Abriu a RC', max_length=255, blank=True, null=True)
    orcamento = models.CharField('Orçamento', max_length=500, blank=True, null=True)
    os = models.CharField('O.S', max_length=100, blank=True, null=True)
    classificacao = models.CharField('Classificação', max_length=50, blank=True, null=True)
    justificativa_classificacao = models.TextField('Justificativa Classificação', blank=True, null=True)
    spaf0009_acesso_portaria = models.CharField('SPAF0009 - Acesso portaria p/ classif. 5 e 8', max_length=255, blank=True, null=True)
    rc = models.CharField('RC', max_length=100, blank=True, null=True, db_index=True)
    data_rc = models.DateTimeField('Data RC', blank=True, null=True)
    
    # Dados do pedido
    pedido = models.CharField('Pedido', max_length=100, blank=True, null=True, db_index=True)
    valor_total_pedido = models.DecimalField('Valor Total do Pedido', max_digits=15, decimal_places=2, blank=True, null=True)
    previsao_para_uso = models.DateTimeField('Previsão para Uso', blank=True, null=True)
    
    # Dados da NF
    nf_servico = models.CharField('NF Serviço', max_length=100, blank=True, null=True)
    nf_retorno_e_data_lancamento = models.CharField('NF Retorno e Data Lançamento', max_length=255, blank=True, null=True)
    cnpj_aurora = models.CharField('CNPJ Aurora', max_length=50, blank=True, null=True)
    simples_nacional = models.CharField('Simples Nacional', max_length=50, blank=True, null=True)
    valor_nf = models.DecimalField('Valor NF', max_digits=15, decimal_places=2, blank=True, null=True)
    emissao = models.DateTimeField('Emissão', blank=True, null=True)
    inclusao_198 = models.DateTimeField('Inclusão 198', blank=True, null=True)
    status = models.CharField('Status', max_length=255, blank=True, null=True)
    obs = models.TextField('Observações', blank=True, null=True)
    saldo_residual_pedido = models.DecimalField('Saldo Residual Pedido', max_digits=15, decimal_places=2, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Controle RC e NF'
        verbose_name_plural = 'Controles RC e NF'
        ordering = ['-data_rc', '-created_at']
        indexes = [
            models.Index(fields=['nf_saida']),
            models.Index(fields=['rc']),
            models.Index(fields=['pedido']),
            models.Index(fields=['data_rc']),
        ]
    
    def __str__(self):
        return f"ID: {self.id_excel or 'N/A'} - RC: {self.rc or 'N/A'} - NF: {self.nf_saida or 'N/A'} - {self.empresa or 'N/A'}"

class ParadaMaquina(models.Model):
    """
    Modelo para armazenar paradas de máquinas.

    Primary key: id (Django AutoField, único por registro).
    Identificação de duplicados / chave natural para atualização: (data, cod_recurso, horario_inicial)
    — uma parada por recurso por data por horário inicial. O import usa essa combinação
    para update_or_create (atualizar se já existir, criar se não).
    """
    # Dados da Unidade
    unid = models.IntegerField('Unidade', blank=True, null=True)
    nome_unidade = models.CharField('Nome Unidade', max_length=255, blank=True, null=True)
    
    # Dados da Linha de Produção
    linha_producao = models.IntegerField('Linha de Produção', blank=True, null=True)
    descr_linha_producao = models.CharField('Descrição Linha de Produção', max_length=255, blank=True, null=True)
    turno = models.CharField('Turno', max_length=10, blank=True, null=True)
    
    # Data da Parada
    data = models.DateField('Data', blank=True, null=True, db_index=True)
    
    # Dados do Item
    cod_item = models.CharField('Código Item', max_length=100, blank=True, null=True)
    descr_item = models.CharField('Descrição Item', max_length=500, blank=True, null=True)
    
    # Dados do Grupo de Recurso
    cod_grupo_recurso = models.IntegerField('Código Grupo de Recurso', blank=True, null=True)
    grupo_recurso = models.CharField('Grupo Recurso', max_length=255, blank=True, null=True)
    
    # Dados da Parada
    cod_parada = models.CharField('Código Parada', max_length=50, blank=True, null=True)
    descr_parada = models.CharField('Descrição Parada', max_length=255, blank=True, null=True)
    nro = models.CharField('Número', max_length=50, blank=True, null=True)
    
    # Dados do Recurso
    cod_recurso = models.IntegerField('Código Recurso', blank=True, null=True)
    descr_recurso = models.CharField('Descrição Recurso', max_length=255, blank=True, null=True)
    
    # Horários
    horario_inicial = models.TimeField('Horário Inicial', blank=True, null=True)
    horario_final = models.TimeField('Horário Final', blank=True, null=True)
    dif_hora = models.DecimalField('Diferença Hora', max_digits=10, decimal_places=8, blank=True, null=True)
    
    # Capacidade
    capacidade = models.DecimalField('Capacidade', max_digits=15, decimal_places=3, blank=True, null=True)
    
    # Motivo e Ação
    motivo = models.TextField('Motivo', blank=True, null=True)
    acao = models.TextField('Ação', blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Parada de Máquina'
        verbose_name_plural = 'Paradas de Máquinas'
        ordering = ['-data', '-horario_inicial']
        indexes = [
            models.Index(fields=['data']),
            models.Index(fields=['cod_recurso']),
            models.Index(fields=['linha_producao']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['data', 'cod_recurso', 'horario_inicial'],
                name='unique_parada_data_recurso_horario',
            ),
        ]

    def __str__(self):
        return f"Parada {self.cod_recurso} - {self.data} {self.horario_inicial}"

class ParadaMaquinaOS(models.Model):
    """
    Associação confirmada entre ParadaMaquina e Ordem de Serviço (OS).
    Usuário confirma na página Analise Máquina por Parada; dados ficam disponíveis para outras análises.
    """
    parada_maquina = models.ForeignKey(
        ParadaMaquina,
        on_delete=models.CASCADE,
        related_name='os_confirmadas'
    )
    os_numero = models.CharField('Ordem de Serviço', max_length=10)
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)

    class Meta:
        verbose_name = 'Parada Máquina - OS Confirmada'
        verbose_name_plural = 'Paradas Máquina - OS Confirmadas'
        ordering = ['parada_maquina', 'os_numero']
        constraints = [
            models.UniqueConstraint(
                fields=['parada_maquina', 'os_numero'],
                name='unique_parada_maquina_os',
            ),
        ]
        indexes = [
            models.Index(fields=['os_numero']),
        ]

    def __str__(self):
        return f"Parada #{self.parada_maquina_id} ↔ OS {self.os_numero}"

SECAO_CONFIG_PARADA = (('frigorifico', 'Frigorífico'),('industria', 'Indústria'),)

class ConfigParadaMaquina(models.Model):
    """Configuração mensal de paradas de máquina por seção (Frigorífico / Indústria)."""
    ano = models.IntegerField('Ano', db_index=True)
    mes = models.IntegerField('Mês', choices=[(i, i) for i in range(1, 13)])
    secao = models.CharField('Seção', max_length=20, choices=SECAO_CONFIG_PARADA)

    # Parâmetros Frigorífico
    suinos_abatidos = models.IntegerField('Suínos Abatidos', blank=True, null=True)
    dias_uteis = models.IntegerField('Dias úteis', blank=True, null=True)
    total_abate_planejado = models.IntegerField('Total de Abate Planejado', blank=True, null=True)
    perda_maximo = models.DecimalField('% de Perda Máximo', max_digits=6, decimal_places=2, blank=True, null=True)
    fator_eficiencia = models.DecimalField('Fator de Eficiência %', max_digits=6, decimal_places=2, blank=True, null=True)
    carcacas_por_minuto = models.DecimalField('Nº Carcaças por Minuto', max_digits=10, decimal_places=2, blank=True, null=True)

    # Parâmetros Indústria
    dias_uteis_industria = models.IntegerField('Dias úteis (Indústria)', blank=True, null=True)
    total_producao_planejada_industria = models.IntegerField('Total de Produção Planejada (Indústria)', blank=True, null=True)
    perda_maximo_industria = models.DecimalField('% de Perda Máximo (Indústria)', max_digits=6, decimal_places=2, blank=True, null=True)
    fator_eficiencia_industria = models.DecimalField('Fator de Eficiência % (Indústria)', max_digits=6, decimal_places=2, blank=True, null=True)

    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Configuração Parada de Máquina'
        verbose_name_plural = 'Configurações Paradas de Máquina'
        ordering = ['ano', 'mes', 'secao']
        constraints = [
            models.UniqueConstraint(fields=['ano', 'mes', 'secao'], name='unique_config_parada_ano_mes_secao'),
        ]
        indexes = [
            models.Index(fields=['ano', 'mes']),
        ]

    def __str__(self):
        return f"Config {self.ano}/{self.mes} - {self.get_secao_display()}"

class ConfigRecursoParadaMaquina(models.Model):
    """
    Define quais valores de descr_recurso (da tabela ParadaMaquina) são incluídos
    na análise de paradas por seção (Frigorífico / Indústria).
    Se existir registro (secao, descr_recurso), esse recurso é usado no cálculo da análise.
    Ex.: Frigorífico = apenas registros com descr_recurso em (NORIA ABATE, ...).
    """
    secao = models.CharField('Seção', max_length=20, choices=SECAO_CONFIG_PARADA)
    descr_recurso = models.CharField('Descrição Recurso', max_length=255)

    class Meta:
        verbose_name = 'Recurso incluído na Análise de Paradas'
        verbose_name_plural = 'Recursos incluídos na Análise de Paradas'
        ordering = ['secao', 'descr_recurso']
        constraints = [
            models.UniqueConstraint(fields=['secao', 'descr_recurso'], name='unique_config_recurso_parada_secao_descr'),
        ]
        indexes = [
            models.Index(fields=['secao']),
        ]

    def __str__(self):
        return f"{self.get_secao_display()} – {self.descr_recurso}"

class ConfigLinhaProducaoCentroAtividade(models.Model):
    """
    Relaciona descr_linha_producao (da tabela ParadaMaquina) com CentroAtividade.
    Permite associar linhas de produção (ex: ABATE, EMBALAGEM) aos Centros de Atividade
    que as compõem. Uma linha pode ter vários CAs; um CA pode estar em várias linhas.
    """
    descr_linha_producao = models.CharField('Linha de Produção', max_length=255, db_index=True)
    centro_atividade = models.ForeignKey(
        'CentroAtividade',
        on_delete=models.CASCADE,
        verbose_name='Centro de Atividade',
        related_name='linhas_producao_config'
    )

    class Meta:
        verbose_name = 'Linha de Produção × Centro de Atividade'
        verbose_name_plural = 'Linhas de Produção × Centros de Atividade'
        ordering = ['descr_linha_producao', 'centro_atividade__ca']
        constraints = [
            models.UniqueConstraint(
                fields=['descr_linha_producao', 'centro_atividade'],
                name='unique_linha_producao_centro_atividade'
            ),
        ]
        indexes = [
            models.Index(fields=['descr_linha_producao']),
        ]

    def __str__(self):
        return f"{self.descr_linha_producao} – {self.centro_atividade}"

class ProducaoDiaria(models.Model):
    """
    Dados de produção diária por dia do mês: Suínos Abatidos e Produção Indústria.
    Um registro por (ano, mes, dia).
    """
    ano = models.IntegerField('Ano', db_index=True)
    mes = models.IntegerField('Mês', choices=[(i, i) for i in range(1, 13)])
    dia = models.IntegerField('Dia', help_text='Dia do mês (1-31)')
    suinos_abatidos = models.IntegerField('Suínos Abatidos', blank=True, null=True)
    producao_industria = models.DecimalField(
        'Produção Indústria', max_digits=15, decimal_places=3, blank=True, null=True
    )

    class Meta:
        verbose_name = 'Produção Diária'
        verbose_name_plural = 'Produções Diárias'
        ordering = ['ano', 'mes', 'dia']
        constraints = [
            models.UniqueConstraint(
                fields=['ano', 'mes', 'dia'],
                name='unique_producao_diaria_ano_mes_dia',
            ),
        ]
        indexes = [
            models.Index(fields=['ano', 'mes']),
        ]

    def __str__(self):
        return f"{self.ano}/{self.mes:02d}/{self.dia:02d} – Suínos: {self.suinos_abatidos or '-'} | Indústria: {self.producao_industria or '-'}"

class Evento(models.Model):
    """Modelo para armazenar eventos com descrição, data, responsável e arquivo anexo"""
    descricao = models.TextField('Descrição', blank=True, null=True)
    data = models.DateField('Data', blank=True, null=True)
    responsavel = models.CharField('Responsável', max_length=255, blank=True, null=True)
    arquivo = models.FileField(
        'Arquivo',
        upload_to='eventos/arquivos/',
        blank=True,
        null=True,
        help_text='Upload de arquivo relacionado ao evento'
    )
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'
        ordering = ['-data', '-created_at']
        indexes = [
            models.Index(fields=['data']),
            models.Index(fields=['responsavel']),
        ]

    def __str__(self):
        return f"{self.descricao[:50] if self.descricao else 'Sem descrição'} - {self.data.strftime('%d/%m/%Y') if self.data else 'Sem data'}"