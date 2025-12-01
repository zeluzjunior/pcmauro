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

RESPONSAVEL_PCM = (
    ('JOSÉ', 'JOSÉ'),
    ('RHUAN', 'RHUAN'),
    ('KARINE', 'KARINE'),
)


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
    local_centro_atividade = models.ForeignKey(
        'LocalCentroAtividade',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Local do Centro de Atividade',
        help_text='Local do Centro de Atividade relacionado ao setor de manutenção'
    )
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

class CentroAtividade(models.Model):
    """Modelo para armazenar informações de Centros de Atividade (CA)"""
    ca = models.IntegerField('CA', unique=True, db_index=True)
    sigla = models.CharField('Sigla', max_length=50, blank=True, null=True)
    descricao = models.CharField('Descrição', max_length=500, blank=True, null=True)
    indice = models.IntegerField('Índice', blank=True, null=True)
    encarregado_responsavel = models.CharField('Encarregado Responsável', max_length=255, blank=True, null=True)
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Centro de Atividade'
        verbose_name_plural = 'Centros de Atividade'
        ordering = ['ca']

    def __str__(self):
        return f"{self.ca} - {self.sigla or self.descricao or 'Sem descrição'}"

class LocalCentroAtividade(models.Model):
    """Modelo para armazenar múltiplos locais associados a um Centro de Atividade"""
    centro_atividade = models.ForeignKey(
        CentroAtividade,
        on_delete=models.CASCADE,
        verbose_name='Centro de Atividade',
        related_name='locais'
    )
    local = models.CharField('Local', max_length=255)
    observacoes = models.TextField('Observações', blank=True, null=True, help_text='Observações sobre o local')
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Local do Centro de Atividade'
        verbose_name_plural = 'Locais dos Centros de Atividade'
        ordering = ['local']

    def __str__(self):
        return f"{self.centro_atividade.ca} - {self.local}"

class Semana52(models.Model):
    """Modelo para armazenar informações das 52 semanas do ano"""
    semana = models.CharField('Semana', max_length=100, unique=True, db_index=True)
    inicio = models.DateField('Data Início', blank=True, null=True)
    fim = models.DateField('Data Fim', blank=True, null=True)
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Semana 52'
        verbose_name_plural = 'Semanas 52'
        ordering = ['inicio']

    def __str__(self):
        return f"{self.semana} - {self.inicio} a {self.fim}"

class Manutentor(models.Model):
    """Modelo para armazenar informações de manutentores"""
    Cadastro = models.CharField('Cadastro', max_length=1000, primary_key=True)
    Nome = models.CharField('Nome', max_length=1000, null=True, blank=True)
    Admissao = models.DateField('Admissão', blank=True, null=True)
    Cargo = models.CharField('Cargo', max_length=1000, null=True, blank=True)
    Posto = models.CharField('Posto', max_length=1000, null=True, blank=True)
    horario_inicio = models.TimeField('Horário Início', blank=True, null=True)
    horario_fim = models.TimeField('Horário Fim', blank=True, null=True)
    tempo_trabalho = models.CharField('Tempo de Trabalho', max_length=250)
    tipo = models.CharField('Tipo', max_length=25, choices=TIPO_MANUTENTOR)
    turno = models.CharField('Turno', max_length=25, choices=TURNO)
    local_trab = models.CharField('Local de Trabalho', max_length=40, choices=LOCAL_TRABALHO)
    created_at = models.DateTimeField('Data de Criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Manutentor'
        verbose_name_plural = 'Manutentores'
        ordering = ['Nome', 'Cadastro']

    def __str__(self):
        return f"{self.Cadastro} - {self.Nome or 'Sem nome'}"

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
        return f"{self.manutentor.Cadastro} - {self.maquina.cd_maquina}"

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
