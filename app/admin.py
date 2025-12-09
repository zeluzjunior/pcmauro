from django.contrib import admin
from .models import (
    Maquina, 
    MaquinaDocumento,
    OrdemServicoCorretiva, 
    OrdemServicoCorretivaFicha,
    CentroAtividade, 
    LocalCentroAtividade,
    Manutentor, 
    ManutentorMaquina,
    ItemEstoque, 
    ManutencaoCsv, 
    ManutencaoTerceiro,
    MaquinaPeca,
    MaquinaPrimariaSecundaria,
    PlanoPreventiva,
    PlanoPreventivaDocumento,
    MeuPlanoPreventiva,
    MeuPlanoPreventivaDocumento,
    RoteiroPreventiva,
    Semana52
)


@admin.register(Maquina)
class MaquinaAdmin(admin.ModelAdmin):
    """Admin configuration for Maquina model"""
    list_display = ('cd_maquina', 'descr_maquina', 'cd_setormanut', 'nome_unid', 'created_at')
    list_filter = ('cd_setormanut', 'cd_tpcentativ', 'created_at')
    search_fields = ('cd_maquina', 'descr_maquina', 'nome_unid', 'cd_setormanut')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50
    
    fieldsets = (
        ('Informações da Máquina', {
            'fields': ('cd_maquina', 'descr_maquina', 'cs_tt_maquina', 'cd_priomaqutv')
        }),
        ('Unidade', {
            'fields': ('cd_unid', 'nome_unid')
        }),
        ('Setor de Manutenção', {
            'fields': ('cd_setormanut', 'descr_setormanut')
        }),
        ('Informações Adicionais', {
            'fields': ('nro_patrimonio', 'cd_modelo', 'cd_grupo', 'cd_tpcentativ', 'descr_gerenc')
        }),
        ('Arquivos e Imagens', {
            'fields': ('foto', 'placa_identificacao', 'arquivo_pdf', 'diagrama_eletrico', 'pecas_reposicao')
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrdemServicoCorretiva)
class OrdemServicoCorretivaAdmin(admin.ModelAdmin):
    """Admin configuration for OrdemServicoCorretiva model"""
    list_display = ('cd_ordemserv', 'cd_maquina', 'descr_maquina', 'cd_setormanut', 'dt_entrada', 'dt_encordmanu')
    list_filter = ('cd_setormanut', 'cd_tpordservtv', 'cd_tpmanuttv', 'created_at')
    search_fields = ('cd_ordemserv', 'cd_maquina', 'descr_maquina', 'nm_func_solic_os', 'nm_func_exec')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50
    
    fieldsets = (
        ('Ordem de Serviço', {
            'fields': ('cd_ordemserv', 'cd_tpordservtv', 'descr_tpordservtv', 'descr_sitordsetv')
        }),
        ('Máquina', {
            'fields': ('cd_maquina', 'descr_maquina')
        }),
        ('Unidade', {
            'fields': ('cd_unid', 'nome_unid', 'cd_unid_exec', 'nome_unid_exec')
        }),
        ('Setor de Manutenção', {
            'fields': ('cd_setormanut', 'descr_setormanut')
        }),
        ('Centro de Atividade', {
            'fields': ('cd_tpcentativ', 'descr_abrev_tpcentativ')
        }),
        ('Solicitação', {
            'fields': ('dt_entrada', 'dt_abertura_solicita', 'cd_func_solic_os', 'nm_func_solic_os', 'descr_queixa')
        }),
        ('Execução', {
            'fields': ('cd_func_exec', 'nm_func_exec', 'exec_tarefas', 'descr_obsordserv')
        }),
        ('Datas', {
            'fields': ('dt_encordmanu', 'dt_aberordser', 'dt_iniparmanu', 'dt_fimparmanu', 'dt_prev_exec')
        }),
        ('Tipo de Manutenção', {
            'fields': ('cd_tpmanuttv', 'descr_tpmanuttv', 'cd_clasorigos', 'descr_clasorigos')
        }),
        ('Outros', {
            'fields': ('descr_recomenos', 'descr_seqplamanu')
        }),
        ('Sistema', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class LocalCentroAtividadeInline(admin.TabularInline):
    """Inline admin para Locais do Centro de Atividade"""
    model = LocalCentroAtividade
    extra = 1
    fields = ('local', 'observacoes')
    verbose_name = 'Local'
    verbose_name_plural = 'Locais'


@admin.register(CentroAtividade)
class CentroAtividadeAdmin(admin.ModelAdmin):
    """Admin configuration for CentroAtividade model"""
    inlines = [LocalCentroAtividadeInline]
    list_display = ('ca', 'sigla', 'descricao', 'indice', 'encarregado_responsavel', 'get_locais', 'created_at')
    list_filter = ('sigla', 'created_at')
    search_fields = ('ca', 'sigla', 'descricao', 'encarregado_responsavel', 'locais__local')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50
    
    fieldsets = (
        ('Informações Principais', {
            'fields': ('ca', 'sigla', 'descricao')
        }),
        ('Informações Adicionais', {
            'fields': ('indice', 'encarregado_responsavel')
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_locais(self, obj):
        """Retorna os locais do Centro de Atividade como string"""
        locais = obj.locais.all()
        if locais:
            return ', '.join([local.local for local in locais])
        return '-'
    get_locais.short_description = 'Locais'


@admin.register(LocalCentroAtividade)
class LocalCentroAtividadeAdmin(admin.ModelAdmin):
    """Admin configuration for LocalCentroAtividade model"""
    list_display = ('centro_atividade', 'local', 'observacoes', 'created_at')
    list_filter = ('centro_atividade', 'created_at')
    search_fields = ('centro_atividade__ca', 'centro_atividade__sigla', 'local', 'observacoes')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50
    
    fieldsets = (
        ('Informações', {
            'fields': ('centro_atividade', 'local', 'observacoes')
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Manutentor)
class ManutentorAdmin(admin.ModelAdmin):
    """Admin configuration for Manutentor model"""
    list_display = ('Matricula', 'Nome', 'Cargo', 'turno', 'local_trab', 'created_at')
    list_filter = ('turno', 'local_trab', 'created_at')
    search_fields = ('Matricula', 'Nome', 'Cargo')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('Matricula', 'Nome', 'Cargo')
        }),
        ('Horários e Tempo de Trabalho', {
            'fields': ('horario_inicio', 'horario_fim', 'tempo_trabalho')
        }),
        ('Classificações', {
            'fields': ('tipo', 'turno', 'local_trab')
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ItemEstoque)
class ItemEstoqueAdmin(admin.ModelAdmin):
    """Admin configuration for ItemEstoque model"""
    list_display = ('codigo_item', 'descricao_item', 'estante', 'prateleira', 'unidade_medida', 'quantidade', 'valor', 'created_at')
    list_filter = ('unidade_medida', 'controla_estoque_minimo', 'estante', 'prateleira', 'created_at')
    search_fields = ('codigo_item', 'descricao_item', 'descricao_dest_uso', 'classificacao_tempo_sem_consumo')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50
    
    fieldsets = (
        ('Informações do Item', {
            'fields': ('codigo_item', 'descricao_item', 'unidade_medida', 'quantidade', 'valor')
        }),
        ('Localização', {
            'fields': ('estante', 'prateleira', 'coluna', 'sequencia')
        }),
        ('Informações Adicionais', {
            'fields': ('descricao_dest_uso', 'controla_estoque_minimo', 'classificacao_tempo_sem_consumo')
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ManutencaoCsv)
class ManutencaoCsvAdmin(admin.ModelAdmin):
    """Admin configuration for ManutencaoCsv model"""
    list_display = ('id', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50
    
    fieldsets = (
        ('Informações', {
            'fields': ('id',)
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ManutencaoTerceiro)
class ManutencaoTerceiroAdmin(admin.ModelAdmin):
    """Admin configuration for ManutencaoTerceiro model"""
    list_display = ('titulo', 'os', 'empresa', 'maquina', 'tipo', 'manutentor', 'data', 'created_at')
    list_filter = ('tipo', 'empresa', 'data', 'created_at')
    search_fields = ('titulo', 'os', 'empresa', 'pedidodecompra', 'requisicaodecompra', 'descricao')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50
    
    fieldsets = (
        ('Informações Principais', {
            'fields': ('titulo', 'os', 'empresa', 'pedidodecompra', 'requisicaodecompra')
        }),
        ('Relacionamentos', {
            'fields': ('maquina', 'manutentor', 'os_importada', 'tipo')
        }),
        ('Data e Descrição', {
            'fields': ('data', 'descricao')
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ManutentorMaquina)
class ManutentorMaquinaAdmin(admin.ModelAdmin):
    """Admin configuration for ManutentorMaquina model"""
    list_display = ('manutentor', 'maquina', 'created_at')
    list_filter = ('manutentor', 'maquina', 'created_at')
    search_fields = ('manutentor__Matricula', 'manutentor__Nome', 'maquina__cd_maquina', 'maquina__descr_maquina')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('manutentor', 'maquina')  # Para facilitar a seleção em muitos registros
    list_per_page = 50


@admin.register(MaquinaPeca)
class MaquinaPecaAdmin(admin.ModelAdmin):
    """Admin configuration for MaquinaPeca model"""
    list_display = ('maquina', 'item_estoque', 'quantidade', 'created_at')
    list_filter = ('maquina', 'item_estoque')
    search_fields = ('maquina__cd_maquina', 'maquina__descr_maquina', 'item_estoque__codigo_item', 'item_estoque__descricao_item')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('maquina', 'item_estoque')  # Para facilitar a seleção em muitos registros


@admin.register(OrdemServicoCorretivaFicha)
class OrdemServicoCorretivaFichaAdmin(admin.ModelAdmin):
    """Admin configuration for OrdemServicoCorretivaFicha model"""
    list_display = ('ordem_servico', 'nm_func_exec_os', 'cd_func_exec_os', 'dt_ficapomanu', 'dt_inic_iteficmanu', 'dt_fim_iteficmanu', 'created_at')
    list_filter = ('ordem_servico', 'created_at')
    search_fields = ('ordem_servico__cd_ordemserv', 'nm_func_exec_os', 'cd_func_exec_os')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('ordem_servico',)  # Para facilitar a seleção em muitos registros
    list_per_page = 50
    
    fieldsets = (
        ('Ordem de Serviço', {
            'fields': ('ordem_servico',)
        }),
        ('Funcionário Executor OS', {
            'fields': ('cd_func_exec_os', 'nm_func_exec_os')
        }),
        ('Ficha de Manutenção', {
            'fields': ('dt_ficapomanu', 'dt_inic_iteficmanu', 'dt_fim_iteficmanu')
        }),
        ('Sistema', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MaquinaPrimariaSecundaria)
class MaquinaPrimariaSecundariaAdmin(admin.ModelAdmin):
    """Admin configuration for MaquinaPrimariaSecundaria model"""
    list_display = ('maquina_primaria', 'maquina_secundaria', 'observacoes', 'created_at')
    list_filter = ('maquina_primaria', 'created_at')
    search_fields = ('maquina_primaria__cd_maquina', 'maquina_primaria__descr_maquina', 'maquina_secundaria__cd_maquina', 'maquina_secundaria__descr_maquina')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('maquina_primaria', 'maquina_secundaria')
    list_per_page = 50
    
    fieldsets = (
        ('Máquinas', {
            'fields': ('maquina_primaria', 'maquina_secundaria')
        }),
        ('Observações', {
            'fields': ('observacoes',)
        }),
        ('Sistema', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PlanoPreventiva)
class PlanoPreventivaAdmin(admin.ModelAdmin):
    """Admin configuration for PlanoPreventiva model"""
    list_display = ('cd_maquina', 'descr_maquina', 'numero_plano', 'sequencia_manutencao', 'dt_execucao', 'nome_funcionario', 'created_at')
    list_filter = ('cd_unid', 'cd_setor', 'numero_plano', 'descr_plano', 'created_at')
    search_fields = ('cd_maquina', 'descr_maquina', 'cd_setor', 'descr_setor', 'descr_tarefa', 'nome_funcionario', 'cd_funcionario')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('maquina',)
    list_per_page = 50
    
    fieldsets = (
        ('Unidade e Setor', {
            'fields': ('cd_unid', 'nome_unid', 'cd_setor', 'descr_setor', 'cd_atividade')
        }),
        ('Máquina', {
            'fields': ('cd_maquina', 'descr_maquina', 'nro_patrimonio', 'maquina')
        }),
        ('Plano', {
            'fields': ('numero_plano', 'descr_plano', 'sequencia_manutencao')
        }),
        ('Execução', {
            'fields': ('dt_execucao', 'quantidade_periodo')
        }),
        ('Tarefa', {
            'fields': ('sequencia_tarefa', 'descr_tarefa')
        }),
        ('Funcionário', {
            'fields': ('cd_funcionario', 'nome_funcionario')
        }),
        ('Sistema', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MeuPlanoPreventiva)
class MeuPlanoPreventivaAdmin(admin.ModelAdmin):
    """Admin configuration for MeuPlanoPreventiva model"""
    list_display = ('cd_maquina', 'descr_maquina', 'numero_plano', 'sequencia_manutencao', 'dt_execucao', 'nome_funcionario', 'created_at')
    list_filter = ('cd_unid', 'cd_setor', 'numero_plano', 'descr_plano', 'created_at')
    search_fields = ('cd_maquina', 'descr_maquina', 'cd_setor', 'descr_setor', 'descr_tarefa', 'nome_funcionario', 'cd_funcionario', 'desc_detalhada_do_roteiro_preventiva')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('maquina', 'roteiro_preventiva')
    list_per_page = 50
    
    fieldsets = (
        ('Unidade e Setor', {
            'fields': ('cd_unid', 'nome_unid', 'cd_setor', 'descr_setor', 'cd_atividade')
        }),
        ('Máquina', {
            'fields': ('cd_maquina', 'descr_maquina', 'nro_patrimonio', 'maquina')
        }),
        ('Plano', {
            'fields': ('numero_plano', 'descr_plano', 'sequencia_manutencao')
        }),
        ('Execução', {
            'fields': ('dt_execucao', 'quantidade_periodo')
        }),
        ('Tarefa', {
            'fields': ('sequencia_tarefa', 'descr_tarefa')
        }),
        ('Funcionário', {
            'fields': ('cd_funcionario', 'nome_funcionario')
        }),
        ('Roteiro Preventiva', {
            'fields': ('roteiro_preventiva', 'descr_seqplamanu', 'desc_detalhada_do_roteiro_preventiva')
        }),
        ('Sistema', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MeuPlanoPreventivaDocumento)
class MeuPlanoPreventivaDocumentoAdmin(admin.ModelAdmin):
    """Admin configuration for MeuPlanoPreventivaDocumento model"""
    list_display = ('meu_plano_preventiva', 'maquina_documento', 'comentario', 'created_at')
    list_filter = ('meu_plano_preventiva', 'created_at')
    search_fields = ('meu_plano_preventiva__numero_plano', 'maquina_documento__arquivo', 'comentario')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('meu_plano_preventiva', 'maquina_documento')
    list_per_page = 50

    fieldsets = (
        ('Associação', {
            'fields': ('meu_plano_preventiva', 'maquina_documento')
        }),
        ('Informações', {
            'fields': ('comentario',)
        }),
        ('Sistema', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RoteiroPreventiva)
class RoteiroPreventivaAdmin(admin.ModelAdmin):
    """Admin configuration for RoteiroPreventiva model"""
    list_display = ('cd_maquina', 'descr_maquina', 'cd_planmanut', 'descr_planmanut', 'seq_seqplamanu', 'cd_tarefamanu', 'cd_ordemserv', 'created_at')
    list_filter = ('cd_unid', 'cd_setormanut', 'cd_planmanut', 'created_at')
    search_fields = ('cd_maquina', 'descr_maquina', 'cd_planmanut', 'descr_planmanut', 'descr_tarefamanu', 'cd_ordemserv', 'nome_funciomanu')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('maquina',)
    list_per_page = 50
    
    fieldsets = (
        ('Unidade', {
            'fields': ('cd_unid', 'nome_unid')
        }),
        ('Funcionário', {
            'fields': ('cd_funciomanu', 'nome_funciomanu', 'funciomanu_id')
        }),
        ('Setor', {
            'fields': ('cd_setormanut', 'descr_setormanut')
        }),
        ('Tipo Centro de Atividade', {
            'fields': ('cd_tpcentativ', 'descr_abrev_tpcentativ')
        }),
        ('Ordem de Serviço', {
            'fields': ('dt_abertura', 'cd_ordemserv', 'ordemserv_id')
        }),
        ('Máquina', {
            'fields': ('maquina', 'cd_maquina', 'descr_maquina')
        }),
        ('Plano de Manutenção', {
            'fields': ('cd_planmanut', 'descr_planmanut', 'descr_recomenos', 'cf_dt_final_execucao', 'cs_qtde_periodo_max', 'cs_tot_temp', 'cf_tot_temp')
        }),
        ('Sequência e Tarefa', {
            'fields': ('seq_seqplamanu', 'cd_tarefamanu', 'descr_tarefamanu', 'descr_periodo')
        }),
        ('Execução', {
            'fields': ('dt_primexec', 'tempo_prev', 'qtde_periodo', 'descr_seqplamanu', 'cf_temp_prev')
        }),
        ('Item do Plano', {
            'fields': ('itemplanma_id', 'cd_item', 'descr_item', 'item_id', 'qtde', 'qtde_saldo', 'qtde_reserva'),
            'classes': ('collapse',)
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PlanoPreventivaDocumento)
class PlanoPreventivaDocumentoAdmin(admin.ModelAdmin):
    """Admin configuration for PlanoPreventivaDocumento model"""
    list_display = ('plano_preventiva', 'arquivo', 'comentario', 'created_at')
    list_filter = ('plano_preventiva', 'created_at')
    search_fields = ('plano_preventiva__numero_plano', 'plano_preventiva__cd_maquina', 'comentario', 'arquivo')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('plano_preventiva',)
    list_per_page = 50
    
    fieldsets = (
        ('Plano Preventiva', {
            'fields': ('plano_preventiva',)
        }),
        ('Documento', {
            'fields': ('arquivo', 'comentario')
        }),
        ('Sistema', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MaquinaDocumento)
class MaquinaDocumentoAdmin(admin.ModelAdmin):
    """Admin configuration for MaquinaDocumento model"""
    list_display = ('maquina', 'arquivo', 'comentario', 'created_at')
    list_filter = ('maquina', 'created_at')
    search_fields = ('maquina__cd_maquina', 'maquina__descr_maquina', 'comentario', 'arquivo')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('maquina',)
    list_per_page = 50
    
    fieldsets = (
        ('Máquina', {
            'fields': ('maquina',)
        }),
        ('Documento', {
            'fields': ('arquivo', 'comentario')
        }),
        ('Sistema', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Semana52)
class Semana52Admin(admin.ModelAdmin):
    """Admin configuration for Semana52 model"""
    list_display = ('semana', 'inicio', 'fim', 'created_at')
    list_filter = ('inicio', 'fim', 'created_at')
    search_fields = ('semana',)
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 52
    
    fieldsets = (
        ('Informações da Semana', {
            'fields': ('semana', 'inicio', 'fim')
        }),
        ('Sistema', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
