from django import forms
from django.forms import inlineformset_factory
from .models import Maquina, MaquinaDocumento, OrdemServicoCorretiva, OrdemServicoCorretivaFicha, CentroAtividade, LocalCentroAtividade, Manutentor, ManutencaoTerceiro, PlanoPreventivaDocumento, MeuPlanoPreventiva, AgendamentoCronograma, Visitas


class MaquinaForm(forms.ModelForm):
    """Formulário para cadastro de máquinas"""
    
    class Meta:
        model = Maquina
        fields = [
            'cd_maquina',
            'cd_unid',
            'nome_unid',
            'cs_tt_maquina',
            'descr_maquina',
            'cd_setormanut',
            'descr_setormanut',
            'cd_priomaqutv',
            'nro_patrimonio',
            'cd_modelo',
            'cd_grupo',
            'cd_tpcentativ',
            'descr_gerenc',
            'foto',
            'placa_identificacao',
            'arquivo_pdf',
            'diagrama_eletrico',
            'pecas_reposicao',
            'local_centro_atividade',
        ]
        widgets = {
            'cd_maquina': forms.NumberInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': 'Código da Máquina'
            }),
            'cd_unid': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código Unidade'
            }),
            'nome_unid': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '255',
                'placeholder': 'Nome Unidade'
            }),
            'cs_tt_maquina': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código Total Máquina'
            }),
            'descr_maquina': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'maxlength': '500',
                'placeholder': 'Descrição da Máquina'
            }),
            'cd_setormanut': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '50',
                'placeholder': 'Código Setor Manutenção'
            }),
            'descr_setormanut': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '255',
                'placeholder': 'Descrição Setor Manutenção'
            }),
            'cd_priomaqutv': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código Prioridade Máquina'
            }),
            'nro_patrimonio': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '100',
                'placeholder': 'Número Patrimônio'
            }),
            'cd_modelo': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código Modelo'
            }),
            'cd_grupo': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código Grupo'
            }),
            'cd_tpcentativ': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código Tipo Centro Atividade'
            }),
            'descr_gerenc': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '255',
                'placeholder': 'Descrição Gerência'
            }),
            'foto': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'placa_identificacao': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'arquivo_pdf': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf',
            }),
            'diagrama_eletrico': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf',
            }),
            'pecas_reposicao': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf',
            }),
            'local_centro_atividade': forms.Select(attrs={
                'class': 'form-control',
                'data-setormanut-filter': 'true',
            }),
        }
        labels = {
            'cd_maquina': 'Código da Máquina *',
            'cd_unid': 'Código Unidade',
            'nome_unid': 'Nome Unidade',
            'cs_tt_maquina': 'Código Total Máquina',
            'descr_maquina': 'Descrição Máquina',
            'cd_setormanut': 'Código Setor Manutenção',
            'descr_setormanut': 'Descrição Setor Manutenção',
            'cd_priomaqutv': 'Código Prioridade Máquina',
            'nro_patrimonio': 'Número Patrimônio',
            'cd_modelo': 'Código Modelo',
            'cd_grupo': 'Código Grupo',
            'cd_tpcentativ': 'Código Tipo Centro Atividade',
            'descr_gerenc': 'Descrição Gerência',
            'foto': 'Foto da Máquina',
            'placa_identificacao': 'Placa de Identificação',
            'arquivo_pdf': 'Arquivo PDF',
            'diagrama_eletrico': 'Diagrama Elétrico',
            'pecas_reposicao': 'Peças de Reposição',
            'local_centro_atividade': 'Local do Centro de Atividade',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Torna cd_maquina obrigatório
        self.fields['cd_maquina'].required = True
        # Torna os campos de imagem e arquivo não obrigatórios
        self.fields['foto'].required = False
        self.fields['placa_identificacao'].required = False
        self.fields['arquivo_pdf'].required = False
        self.fields['diagrama_eletrico'].required = False
        self.fields['pecas_reposicao'].required = False
        
        # Filtrar LocalCentroAtividade baseado no cd_setormanut
        # Assumindo que cd_setormanut corresponde ao ca do CentroAtividade
        if self.instance and self.instance.pk and self.instance.cd_setormanut:
            try:
                # Tentar converter cd_setormanut para inteiro para comparar com ca
                cd_setormanut = self.instance.cd_setormanut
                # Se cd_setormanut é numérico, usar como CA
                if cd_setormanut.isdigit():
                    ca_value = int(cd_setormanut)
                    centros = CentroAtividade.objects.filter(ca=ca_value)
                    if centros.exists():
                        self.fields['local_centro_atividade'].queryset = LocalCentroAtividade.objects.filter(
                            centro_atividade__in=centros
                        ).order_by('local')
                    else:
                        self.fields['local_centro_atividade'].queryset = LocalCentroAtividade.objects.none()
                else:
                    # Se não é numérico, não filtrar (mostrar todos)
                    self.fields['local_centro_atividade'].queryset = LocalCentroAtividade.objects.all().order_by('local')
            except (ValueError, AttributeError):
                # Se houver erro, mostrar todos
                self.fields['local_centro_atividade'].queryset = LocalCentroAtividade.objects.all().order_by('local')
        else:
            # Se não há instância ou cd_setormanut, mostrar todos
            self.fields['local_centro_atividade'].queryset = LocalCentroAtividade.objects.all().order_by('local')


class OrdemServicoCorretivaForm(forms.ModelForm):
    """Formulário para cadastro de ordens de serviço corretivas"""
    
    class Meta:
        model = OrdemServicoCorretiva
        fields = '__all__'
        exclude = ['created_at', 'updated_at']
        
        widgets = {
            # Ordem de Serviço
            'cd_ordemserv': forms.NumberInput(attrs={'class': 'form-control', 'required': True}),
            'cd_tpordservtv': forms.NumberInput(attrs={'class': 'form-control'}),
            'descr_tpordservtv': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '255'}),
            'descr_sitordsetv': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '255'}),
            
            # Máquina
            'cd_maquina': forms.NumberInput(attrs={'class': 'form-control'}),
            'descr_maquina': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'maxlength': '500'}),
            
            # Unidades
            'cd_unid': forms.NumberInput(attrs={'class': 'form-control'}),
            'nome_unid': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '255'}),
            'cd_unid_exec': forms.NumberInput(attrs={'class': 'form-control'}),
            'nome_unid_exec': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '255'}),
            
            # Setor de Manutenção
            'cd_setormanut': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '50'}),
            'descr_setormanut': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '255'}),
            
            # Centro de Atividade
            'cd_tpcentativ': forms.NumberInput(attrs={'class': 'form-control'}),
            'descr_abrev_tpcentativ': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '255'}),
            
            # Datas
            'dt_entrada': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '50', 'placeholder': 'dd/mm/aaaa hh:mm'}),
            'dt_abertura_solicita': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '50', 'placeholder': 'dd/mm/aaaa hh:mm'}),
            'dt_encordmanu': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '50', 'placeholder': 'dd/mm/aaaa hh:mm'}),
            'dt_aberordser': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '50', 'placeholder': 'dd/mm/aaaa hh:mm'}),
            'dt_iniparmanu': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '50', 'placeholder': 'dd/mm/aaaa hh:mm'}),
            'dt_fimparmanu': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '50', 'placeholder': 'dd/mm/aaaa hh:mm'}),
            'dt_prev_exec': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '50', 'placeholder': 'dd/mm/aaaa hh:mm'}),
            
            # Funcionários
            'cd_func_solic_os': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '100'}),
            'nm_func_solic_os': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '255'}),
            'cd_func_exec': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '100'}),
            'nm_func_exec': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '255'}),
            
            # Descrições e Textos
            'descr_queixa': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'exec_tarefas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'descr_obsordserv': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'descr_recomenos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'descr_seqplamanu': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '255'}),
            
            # Tipos e Classificações
            'cd_tpmanuttv': forms.NumberInput(attrs={'class': 'form-control'}),
            'descr_tpmanuttv': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '255'}),
            'cd_clasorigos': forms.NumberInput(attrs={'class': 'form-control'}),
            'descr_clasorigos': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '255'}),
        }
        
        labels = {
            'cd_ordemserv': 'Código Ordem de Serviço *',
            'cd_maquina': 'Código Máquina',
            'descr_maquina': 'Descrição Máquina',
            'cd_unid': 'Código Unidade',
            'nome_unid': 'Nome Unidade',
            'cd_setormanut': 'Código Setor Manutenção',
            'descr_setormanut': 'Descrição Setor Manutenção',
            'dt_entrada': 'Data Entrada',
            'dt_abertura_solicita': 'Data Abertura Solicitação',
            'cd_func_solic_os': 'Código Funcionário Solicitante',
            'nm_func_solic_os': 'Nome Funcionário Solicitante',
            'descr_queixa': 'Descrição da Queixa',
            'exec_tarefas': 'Execução de Tarefas',
            'cd_func_exec': 'Código Funcionário Executor',
            'nm_func_exec': 'Nome Funcionário Executor',
            'descr_obsordserv': 'Observações da Ordem de Serviço',
            'dt_encordmanu': 'Data Encerramento',
            'dt_aberordser': 'Data Abertura Ordem Serviço',
            'dt_iniparmanu': 'Data Início Parada',
            'dt_fimparmanu': 'Data Fim Parada',
            'dt_prev_exec': 'Data Prevista Execução',
            'cd_tpordservtv': 'Código Tipo Ordem Serviço',
            'descr_tpordservtv': 'Descrição Tipo Ordem Serviço',
            'descr_sitordsetv': 'Situação Ordem Serviço',
            'descr_recomenos': 'Recomendações',
            'descr_seqplamanu': 'Sequência Plano Manutenção',
            'cd_tpmanuttv': 'Código Tipo Manutenção',
            'descr_tpmanuttv': 'Descrição Tipo Manutenção',
            'cd_clasorigos': 'Código Classificação Origem',
            'descr_clasorigos': 'Descrição Classificação Origem',
            'cd_unid_exec': 'Código Unidade Execução',
            'nome_unid_exec': 'Nome Unidade Execução',
            'cd_tpcentativ': 'Código Tipo Centro Atividade',
            'descr_abrev_tpcentativ': 'Descrição Centro Atividade',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Torna cd_ordemserv obrigatório
        self.fields['cd_ordemserv'].required = True


class OrdemServicoCorretivaFichaForm(forms.ModelForm):
    """Formulário para Fichas de Manutenção de Ordens de Serviço Corretivas"""
    class Meta:
        model = OrdemServicoCorretivaFicha
        fields = [
            'ordem_servico',
            'cd_func_exec_os',
            'nm_func_exec_os',
            'dt_ficapomanu',
            'dt_inic_iteficmanu',
            'dt_fim_iteficmanu',
        ]
        widgets = {
            'ordem_servico': forms.Select(attrs={'class': 'form-select'}),
            'cd_func_exec_os': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '100'}),
            'nm_func_exec_os': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '255'}),
            'dt_ficapomanu': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '50'}),
            'dt_inic_iteficmanu': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '50'}),
            'dt_fim_iteficmanu': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '50'}),
        }
        labels = {
            'ordem_servico': 'Ordem de Serviço *',
            'cd_func_exec_os': 'Código Funcionário Executor OS',
            'nm_func_exec_os': 'Nome Funcionário Executor OS',
            'dt_ficapomanu': 'Data Ficha Ponto Manutenção',
            'dt_inic_iteficmanu': 'Data Início Item Ficha Manutenção',
            'dt_fim_iteficmanu': 'Data Fim Item Ficha Manutenção',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Torna ordem_servico obrigatório
        self.fields['ordem_servico'].required = True


class CentroAtividadeForm(forms.ModelForm):
    """Formulário para cadastro de Centros de Atividade (CA)"""
    
    class Meta:
        model = CentroAtividade
        fields = [
            'ca',
            'sigla',
            'descricao',
            'indice',
            'encarregado_responsavel',
        ]
        widgets = {
            'ca': forms.NumberInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': 'Código do Centro de Atividade'
            }),
            'sigla': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '50',
                'placeholder': 'Sigla do CA'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'maxlength': '500',
                'placeholder': 'Descrição do Centro de Atividade'
            }),
            'indice': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Índice'
            }),
            'encarregado_responsavel': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '255',
                'placeholder': 'Nome do Encarregado Responsável'
            }),
        }
        labels = {
            'ca': 'CA *',
            'sigla': 'Sigla',
            'descricao': 'Descrição',
            'indice': 'Índice',
            'encarregado_responsavel': 'Encarregado Responsável',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Torna ca obrigatório
        self.fields['ca'].required = True


class LocalCentroAtividadeForm(forms.ModelForm):
    """Formulário para cadastro de Locais do Centro de Atividade"""
    
    class Meta:
        model = LocalCentroAtividade
        fields = ['local', 'observacoes']
        widgets = {
            'local': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '255',
                'placeholder': 'Local do Centro de Atividade'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observações sobre o local (opcional)'
            }),
        }
        labels = {
            'local': 'Local',
            'observacoes': 'Observações',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['local'].required = True


# Formset factory para múltiplos locais
LocalCentroAtividadeFormSet = inlineformset_factory(
    CentroAtividade,
    LocalCentroAtividade,
    form=LocalCentroAtividadeForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
    can_order=False,
    fk_name='centro_atividade'
)


class ManutentorForm(forms.ModelForm):
    """Formulário para cadastro de manutentores"""

    class Meta:
        model = Manutentor
        fields = [
            'Matricula',
            'Nome',
            'Cargo',
            'horario_inicio',
            'horario_fim',
            'tempo_trabalho',
            'turno',
            'local_trab',
        ]
        widgets = {
            'Matricula': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': 'Matrícula'
            }),
            'Nome': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '1000',
                'placeholder': 'Nome Completo'
            }),
            'Cargo': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '1000',
                'placeholder': 'Cargo'
            }),
            'horario_inicio': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
                'placeholder': 'Horário de Início'
            }),
            'horario_fim': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
                'placeholder': 'Horário de Fim'
            }),
            'tempo_trabalho': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '250',
                'placeholder': 'Tempo de Trabalho'
            }),
            'turno': forms.Select(attrs={
                'class': 'form-select',
            }),
            'local_trab': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
        labels = {
            'Matricula': 'Matrícula *',
            'Nome': 'Nome',
            'Cargo': 'Cargo',
            'horario_inicio': 'Horário Início',
            'horario_fim': 'Horário Fim',
            'tempo_trabalho': 'Tempo de Trabalho',
            'turno': 'Turno',
            'local_trab': 'Local de Trabalho',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Torna campos obrigatórios
        self.fields['Matricula'].required = True
        self.fields['tempo_trabalho'].required = True
        self.fields['turno'].required = True
        self.fields['local_trab'].required = True


class ManutencaoTerceiroForm(forms.ModelForm):
    """Formulário para cadastro de manutenções de terceiros"""
    
    class Meta:
        model = ManutencaoTerceiro
        fields = [
            'titulo',
            'os',
            'empresa',
            'pedidodecompra',
            'requisicaodecompra',
            'manutentor',
            'os_importada',
            'maquina',
            'tipo',
            'data',
            'descricao',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'maxlength': '150',
                'placeholder': 'Título da Manutenção'
            }),
            'os': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '150',
                'placeholder': 'Número da OS'
            }),
            'empresa': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'maxlength': '150',
                'placeholder': 'Nome da Empresa'
            }),
            'pedidodecompra': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'maxlength': '150',
                'placeholder': 'Pedido de Compra'
            }),
            'requisicaodecompra': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'maxlength': '150',
                'placeholder': 'Requisição de Compra'
            }),
            'manutentor': forms.Select(attrs={
                'class': 'form-select',
            }),
            'os_importada': forms.Select(attrs={
                'class': 'form-select',
            }),
            'maquina': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-select',
            }),
            'data': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }, format='%Y-%m-%dT%H:%M'),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'maxlength': '250',
                'placeholder': 'Descrição da manutenção'
            }),
        }
        labels = {
            'titulo': 'Título *',
            'os': 'OS',
            'empresa': 'Empresa *',
            'pedidodecompra': 'Pedido de Compra *',
            'requisicaodecompra': 'Requisição de Compra *',
            'manutentor': 'Manutentor',
            'os_importada': 'OS Importada',
            'maquina': 'Máquina *',
            'tipo': 'Tipo *',
            'data': 'Data',
            'descricao': 'Descrição',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Torna campos obrigatórios
        self.fields['titulo'].required = True
        self.fields['empresa'].required = True
        self.fields['pedidodecompra'].required = True
        self.fields['requisicaodecompra'].required = True
        self.fields['maquina'].required = True
        self.fields['tipo'].required = True
        # Torna campos opcionais
        self.fields['manutentor'].required = False
        self.fields['os_importada'].required = False
        self.fields['os'].required = False
        self.fields['data'].required = False
        self.fields['descricao'].required = False
        
        # Configurar formato de data para datetime-local
        self.fields['data'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']
        
        # Personalizar o campo manutentor para ordenar por Nome e exibir Nome
        from app.models import Manutentor
        self.fields['manutentor'].queryset = Manutentor.objects.all().order_by('Nome')
        self.fields['manutentor'].label_from_instance = lambda obj: f"{obj.Nome or 'Sem nome'} ({obj.Matricula})" if obj.Nome else f"Sem nome ({obj.Matricula})"
    
    def clean_data(self):
        """Permitir que o campo data seja vazio"""
        data = self.cleaned_data.get('data')
        # Se estiver vazio, retornar None (permitido pelo modelo)
        if not data:
            return None
        if isinstance(data, str) and not data.strip():
            return None
        return data


class PlanoPreventivaDocumentoForm(forms.ModelForm):
    """Formulário para upload de documentos relacionados a planos preventiva"""
    class Meta:
        model = PlanoPreventivaDocumento
        fields = ['arquivo', 'comentario']
        widgets = {
            'arquivo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.gif,.xlsx,.xls,.xlsm,.txt',
            }),
            'comentario': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Comentário sobre o documento (opcional)'
            }),
        }
        labels = {
            'arquivo': 'Arquivo *',
            'comentario': 'Comentário',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['arquivo'].required = True
        self.fields['comentario'].required = False


class MeuPlanoPreventivaForm(forms.ModelForm):
    """Formulário para edição de MeuPlanoPreventiva"""
    
    class Meta:
        model = MeuPlanoPreventiva
        fields = [
            'cd_unid',
            'nome_unid',
            'cd_setor',
            'descr_setor',
            'cd_atividade',
            'cd_maquina',
            'descr_maquina',
            'nro_patrimonio',
            'numero_plano',
            'descr_plano',
            'sequencia_manutencao',
            'dt_execucao',
            'quantidade_periodo',
            'sequencia_tarefa',
            'descr_tarefa',
            'cd_funcionario',
            'nome_funcionario',
            'descr_seqplamanu',
            'desc_detalhada_do_roteiro_preventiva',
            'maquina',
            'roteiro_preventiva',
        ]
        widgets = {
            'cd_unid': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código Unidade'
            }),
            'nome_unid': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '255',
                'placeholder': 'Nome Unidade'
            }),
            'cd_setor': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '50',
                'placeholder': 'Código Setor'
            }),
            'descr_setor': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '255',
                'placeholder': 'Descrição Setor'
            }),
            'cd_atividade': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código Atividade'
            }),
            'cd_maquina': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código Máquina'
            }),
            'descr_maquina': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'maxlength': '500',
                'placeholder': 'Descrição da Máquina'
            }),
            'nro_patrimonio': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '100',
                'placeholder': 'Número Patrimônio'
            }),
            'numero_plano': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número do Plano'
            }),
            'descr_plano': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '255',
                'placeholder': 'Descrição do Plano'
            }),
            'sequencia_manutencao': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sequência Manutenção'
            }),
            'dt_execucao': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '50',
                'placeholder': 'Data Execução (DD/MM/YYYY)'
            }),
            'quantidade_periodo': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Quantidade Período (dias)'
            }),
            'sequencia_tarefa': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sequência Tarefa'
            }),
            'descr_tarefa': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descrição da Tarefa'
            }),
            'cd_funcionario': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '100',
                'placeholder': 'Código Funcionário'
            }),
            'nome_funcionario': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '255',
                'placeholder': 'Nome Funcionário'
            }),
            'descr_seqplamanu': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '255',
                'placeholder': 'Descrição Sequência Plano Manutenção'
            }),
            'desc_detalhada_do_roteiro_preventiva': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Descrição Detalhada do Roteiro Preventiva'
            }),
            'maquina': forms.Select(attrs={
                'class': 'form-control',
            }),
            'roteiro_preventiva': forms.Select(attrs={
                'class': 'form-control',
            }),
        }
        labels = {
            'cd_unid': 'Código Unidade',
            'nome_unid': 'Nome Unidade',
            'cd_setor': 'Código Setor',
            'descr_setor': 'Descrição Setor',
            'cd_atividade': 'Código Atividade',
            'cd_maquina': 'Código Máquina',
            'descr_maquina': 'Descrição da Máquina',
            'nro_patrimonio': 'Número Patrimônio',
            'numero_plano': 'Número do Plano',
            'descr_plano': 'Descrição do Plano',
            'sequencia_manutencao': 'Sequência Manutenção',
            'dt_execucao': 'Data Execução',
            'quantidade_periodo': 'Quantidade Período (dias)',
            'sequencia_tarefa': 'Sequência Tarefa',
            'descr_tarefa': 'Descrição da Tarefa',
            'cd_funcionario': 'Código Funcionário',
            'nome_funcionario': 'Nome Funcionário',
            'descr_seqplamanu': 'Descrição Sequência Plano Manutenção',
            'desc_detalhada_do_roteiro_preventiva': 'Descrição Detalhada do Roteiro Preventiva',
            'maquina': 'Máquina Relacionada',
            'roteiro_preventiva': 'Roteiro Preventiva Relacionado',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configurar querysets para os campos ForeignKey
        from .models import Maquina, RoteiroPreventiva
        
        # Limitar querysets para melhor performance
        self.fields['maquina'].queryset = Maquina.objects.all().order_by('cd_maquina')[:500]
        self.fields['roteiro_preventiva'].queryset = RoteiroPreventiva.objects.all().order_by('cd_maquina', 'cd_planmanut')[:500]
        
        # Tornar campos opcionais
        self.fields['maquina'].required = False
        self.fields['roteiro_preventiva'].required = False


class AgendamentoCronogramaForm(forms.ModelForm):
    """Formulário para cadastro de agendamentos de cronograma"""
    
    class Meta:
        model = AgendamentoCronograma
        fields = [
            'tipo_agendamento',
            'maquina',
            'plano_preventiva',
            'nome_grupo',
            'periodicidade',
            'data_planejada',
            'observacoes',
        ]
        widgets = {
            'tipo_agendamento': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
            }),
            'maquina': forms.Select(attrs={
                'class': 'form-control',
            }),
            'plano_preventiva': forms.Select(attrs={
                'class': 'form-control',
            }),
            'nome_grupo': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '255',
                'placeholder': 'Nome do grupo de agendamentos'
            }),
            'periodicidade': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Periodicidade em dias'
            }),
            'data_planejada': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Observações adicionais sobre este agendamento'
            }),
        }
        labels = {
            'tipo_agendamento': 'Tipo de Agendamento',
            'maquina': 'Máquina',
            'plano_preventiva': 'Plano Preventiva',
            'nome_grupo': 'Nome do Grupo',
            'periodicidade': 'Periodicidade (dias)',
            'data_planejada': 'Data Planejada',
            'observacoes': 'Observações',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Maquina, MeuPlanoPreventiva
        
        # Configurar querysets
        self.fields['maquina'].queryset = Maquina.objects.all().order_by('cd_maquina')
        self.fields['plano_preventiva'].queryset = MeuPlanoPreventiva.objects.all().order_by('cd_maquina', 'numero_plano')
        
        # Tornar campos opcionais inicialmente
        self.fields['maquina'].required = False
        self.fields['plano_preventiva'].required = False
        self.fields['nome_grupo'].required = False
        self.fields['periodicidade'].required = False
        self.fields['observacoes'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_agendamento = cleaned_data.get('tipo_agendamento')
        maquina = cleaned_data.get('maquina')
        plano_preventiva = cleaned_data.get('plano_preventiva')
        
        if tipo_agendamento == 'maquina' and not maquina:
            raise forms.ValidationError('Quando o tipo é "Máquina", é necessário informar a máquina.')
        
        if tipo_agendamento == 'plano' and not plano_preventiva:
            raise forms.ValidationError('Quando o tipo é "Plano Preventiva", é necessário informar o plano.')
        
        if tipo_agendamento == 'maquina' and plano_preventiva:
            raise forms.ValidationError('Não é possível ter máquina e plano ao mesmo tempo.')
        
        if tipo_agendamento == 'plano' and maquina:
            raise forms.ValidationError('Não é possível ter máquina e plano ao mesmo tempo.')
        
        return cleaned_data


class VisitasForm(forms.ModelForm):
    """Formulário para cadastro de visitas"""
    
    class Meta:
        model = Visitas
        fields = [
            'titulo',
            'data',
            'descricao',
            'nome_contato',
            'numero_contato',
            'documento',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '250',
                'placeholder': 'Título da visita',
                'required': True,
            }),
            'data': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }, format='%Y-%m-%dT%H:%M'),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'maxlength': '1000',
                'placeholder': 'Descrição da visita'
            }),
            'nome_contato': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '250',
                'placeholder': 'Nome do contato'
            }),
            'numero_contato': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '250',
                'placeholder': 'Número do contato'
            }),
            'documento': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.gif',
            }),
        }
        labels = {
            'titulo': 'Título',
            'data': 'Data',
            'descricao': 'Descrição',
            'nome_contato': 'Nome do Contato',
            'numero_contato': 'Número do Contato',
            'documento': 'Documento',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tornar campos opcionais exceto título
        self.fields['titulo'].required = True
        self.fields['data'].required = False
        self.fields['descricao'].required = False
        self.fields['nome_contato'].required = False
        self.fields['numero_contato'].required = False
        self.fields['documento'].required = False
        
        # Configurar formato de data para datetime-local
        self.fields['data'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']
    
    def clean_data(self):
        """Permitir que o campo data seja vazio"""
        data = self.cleaned_data.get('data')
        # Se estiver vazio ou for uma string vazia, retornar None (permitido pelo modelo)
        if not data:
            return None
        if isinstance(data, str) and not data.strip():
            return None
        return data
    
    def clean_titulo(self):
        """Limpar e validar título"""
        titulo = self.cleaned_data.get('titulo')
        if titulo:
            titulo = titulo.strip()
            if not titulo:
                raise forms.ValidationError('O título não pode estar vazio.')
        return titulo
    
    def clean(self):
        """Validação geral do formulário"""
        cleaned_data = super().clean()
        return cleaned_data

