from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
import os


def handle_form_errors(form, request):
    """Helper function to handle form validation errors with improved messages"""
    missing_required = []
    for field, errors in form.errors.items():
        field_label = form.fields[field].label
        for error in errors:
            error_str = str(error).lower()
            if 'required' in error_str or 'obrigatório' in error_str or 'este campo é obrigatório' in error_str:
                if field_label not in missing_required:
                    missing_required.append(field_label)
                messages.warning(request, f'<strong>{field_label}</strong>: Este campo é obrigatório e deve ser preenchido.')
            else:
                messages.error(request, f'<strong>{field_label}</strong>: {error}')
    
    if missing_required:
        messages.warning(request, f'<strong>Atenção:</strong> {len(missing_required)} campo(s) obrigatório(s) não preenchido(s). Por favor, preencha todos os campos marcados com <span class="text-danger">*</span>.')
    elif form.errors:
        messages.error(request, 'Por favor, corrija os erros no formulário antes de continuar.')


def home(request):
    """Home page view"""
    from app.models import OrdemServicoCorretiva
    from datetime import datetime, timedelta
    
    # Buscar ordens de serviço para exibir no calendário
    ordens = OrdemServicoCorretiva.objects.exclude(
        dt_entrada__isnull=True
    ).exclude(
        dt_entrada=''
    )[:50]  # Limitar a 50 para performance
    
    eventos = []
    for ordem in ordens:
        # Tentar parsear a data de entrada
        try:
            # Formato esperado: dd/mm/yyyy hh:mm ou dd/mm/yyyy
            dt_str = ordem.dt_entrada.strip()
            if ' ' in dt_str:
                date_part = dt_str.split(' ')[0]
            else:
                date_part = dt_str
            
            # Parsear data dd/mm/yyyy
            if '/' in date_part:
                parts = date_part.split('/')
                if len(parts) == 3:
                    day, month, year = parts
                    # Converter para formato ISO (yyyy-mm-dd)
                    start_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    
                    eventos.append({
                        'title': f'OS {ordem.cd_ordemserv} - {ordem.descr_maquina[:30] if ordem.descr_maquina else "Sem descrição"}',
                        'start': start_date,
                        'color': '#3788d8',  # Azul
                        'url': f'/manutencao-corretiva/consultar/?search={ordem.cd_ordemserv}'
                    })
        except:
            # Se não conseguir parsear, continuar
            continue
    
    # Adicionar exemplo de evento de manutenção preventiva (você pode adicionar mais eventos aqui)
    hoje = datetime.now()
    eventos.append({
        'title': 'Manutenção Preventiva - Exemplo',
        'start': hoje.strftime('%Y-%m-%d'),
        'color': '#28a745',  # Verde
        'url': ''
    })
    
    context = {
        'page_title': 'Home',
        'active_page': 'home',
        'eventos': eventos
    }
    return render(request, 'home.html', context)


def centros_de_atividade(request):
    """Centros de Atividade listing page view"""
    context = {
        'page_title': 'Centros de Atividade',
        'active_page': 'centros_de_atividade'
    }
    return render(request, 'analise/analise_centro_de_atividade.html', context)


def about(request):
    """About page view"""
    context = {
        'page_title': 'Sobre',
        'active_page': 'about'
    }
    return render(request, 'about.html', context)


def em_desenvolvimento(request):
    """Página em desenvolvimento"""
    context = {
        'page_title': 'Página em Desenvolvimento',
        'active_page': 'em_desenvolvimento'
    }
    return render(request, 'em_desenvolvimento.html', context)


def analise_plano_preventiva(request):
    """Análise de Plano Preventiva"""
    context = {
        'page_title': 'Análise de Plano Preventiva',
        'active_page': 'analise_plano_preventiva'
    }
    return render(request, 'analise/analise_plano_preventiva.html', context)


def _match_plano_roteiro(plano, roteiro):
    """
    Verifica se um plano e um roteiro correspondem baseado em múltiplos campos.
    Retorna um score de correspondência (0-100) e lista de campos que correspondem.
    """
    score = 0
    campos_match = []
    campos_total = 0
    
    # Campos para comparação (com pesos)
    campos_comparacao = [
        ('cd_maquina', 'cd_maquina', 30),
        ('cd_funcionario', 'cd_funciomanu', 20),
        ('nome_funcionario', 'nome_funciomanu', 15),
        ('cd_atividade', 'cd_tpcentativ', 15),
        ('numero_plano', 'cd_planmanut', 10),
        ('sequencia_manutencao', 'seq_seqplamanu', 5),
        ('sequencia_tarefa', 'cd_tarefamanu', 5),
    ]
    
    for campo_plano, campo_roteiro, peso in campos_comparacao:
        campos_total += peso
        valor_plano = getattr(plano, campo_plano, None)
        valor_roteiro = getattr(roteiro, campo_roteiro, None)
        
        # Normalizar valores para comparação
        if valor_plano is not None and valor_roteiro is not None:
            # Para strings, comparar ignorando case e espaços
            if isinstance(valor_plano, str) and isinstance(valor_roteiro, str):
                if valor_plano.strip().upper() == valor_roteiro.strip().upper():
                    score += peso
                    campos_match.append(campo_plano)
            # Para números, comparação direta
            elif isinstance(valor_plano, (int, float)) and isinstance(valor_roteiro, (int, float)):
                if valor_plano == valor_roteiro:
                    score += peso
                    campos_match.append(campo_plano)
            # Comparação direta
            elif valor_plano == valor_roteiro:
                score += peso
                campos_match.append(campo_plano)
    
    # Calcular percentual de match
    percentual_match = (score / campos_total * 100) if campos_total > 0 else 0
    
    return percentual_match, campos_match


def analise_roteiro_plano_preventiva(request):
    """Análise de Roteiro e Plano de Preventiva - Encontrar relações entre as tabelas"""
    from app.models import PlanoPreventiva, RoteiroPreventiva
    from django.core.paginator import Paginator
    from django.db import transaction
    
    # Verificar se é uma ação de link
    if request.method == 'POST' and 'link_records' in request.POST:
        plano_id = request.POST.get('plano_id')
        roteiro_id = request.POST.get('roteiro_id')
        
        try:
            plano = PlanoPreventiva.objects.get(id=plano_id)
            roteiro = RoteiroPreventiva.objects.get(id=roteiro_id)
            
            # Vincular roteiro ao plano e atualizar DESCR_SEQPLAMANU
            with transaction.atomic():
                plano.roteiro_preventiva = roteiro
                plano.descr_seqplamanu = roteiro.descr_seqplamanu
                plano.save()
            
            messages.success(request, f'Plano {plano.id} vinculado ao Roteiro {roteiro.id} com sucesso! DESCR_SEQPLAMANU atualizado.')
        except PlanoPreventiva.DoesNotExist:
            messages.error(request, 'Plano não encontrado.')
        except RoteiroPreventiva.DoesNotExist:
            messages.error(request, 'Roteiro não encontrado.')
        except Exception as e:
            messages.error(request, f'Erro ao vincular registros: {str(e)}')
    
    # Buscar todos os registros
    planos = PlanoPreventiva.objects.all()
    roteiros = RoteiroPreventiva.objects.all()
    
    # Estatísticas gerais
    total_planos = planos.count()
    total_roteiros = roteiros.count()
    
    # Encontrar relacionamentos usando matching flexível
    relacionamentos = []
    relacionamentos_sugeridos = []  # Matches com score alto mas não perfeito
    planos_sem_relacao = []
    roteiros_sem_relacao = []
    
    # Threshold para considerar match (70% de correspondência)
    threshold_match = 70.0
    
    # Processar planos e encontrar relacionamentos
    planos_processados = set()
    roteiros_processados = set()
    
    for plano in planos:
        melhor_match = None
        melhor_score = 0
        melhor_campos_match = []
        
        # Buscar roteiros que podem corresponder
        for roteiro in roteiros:
            score, campos_match = _match_plano_roteiro(plano, roteiro)
            
            if score >= threshold_match and score > melhor_score:
                melhor_score = score
                melhor_match = roteiro
                melhor_campos_match = campos_match
        
        if melhor_match:
            relacionamentos.append({
                'plano': plano,
                'roteiro': melhor_match,
                'descr_seqplamanu': melhor_match.descr_seqplamanu,
                'match_score': melhor_score,
                'campos_match': melhor_campos_match,
                'ja_vinculado': plano.roteiro_preventiva_id == melhor_match.id,
                'match_perfect': melhor_score >= 95.0
            })
            planos_processados.add(plano.id)
            roteiros_processados.add(melhor_match.id)
        else:
            # Verificar se já está vinculado
            if plano.roteiro_preventiva:
                relacionamentos.append({
                    'plano': plano,
                    'roteiro': plano.roteiro_preventiva,
                    'descr_seqplamanu': plano.roteiro_preventiva.descr_seqplamanu,
                    'match_score': 100.0,
                    'campos_match': ['vinculado_manual'],
                    'ja_vinculado': True,
                    'match_perfect': True
                })
                planos_processados.add(plano.id)
                roteiros_processados.add(plano.roteiro_preventiva.id)
            else:
                planos_sem_relacao.append(plano)
    
    # Encontrar roteiros sem plano correspondente
    for roteiro in roteiros:
        if roteiro.id not in roteiros_processados:
            roteiros_sem_relacao.append(roteiro)
    
    # Estatísticas de relacionamentos
    total_relacionamentos = len(relacionamentos)
    total_planos_sem_relacao = len(planos_sem_relacao)
    total_roteiros_sem_relacao = len(roteiros_sem_relacao)
    
    # Agrupar por descr_seqplamanu para análise
    agrupado_por_descr_seqplamanu = {}
    for rel in relacionamentos:
        descr = rel['descr_seqplamanu'] or 'Sem Descrição'
        if descr not in agrupado_por_descr_seqplamanu:
            agrupado_por_descr_seqplamanu[descr] = []
        agrupado_por_descr_seqplamanu[descr].append(rel)
    
    # Calcular percentuais para agrupamento
    agrupado_com_percentuais = {}
    for descr, rels in agrupado_por_descr_seqplamanu.items():
        quantidade = len(rels)
        percentual = (quantidade * 100.0 / total_relacionamentos) if total_relacionamentos > 0 else 0
        agrupado_com_percentuais[descr] = {
            'quantidade': quantidade,
            'percentual': round(percentual, 1)
        }
    
    # Filtros
    filter_maquina = request.GET.get('filter_maquina', '').strip()
    filter_descr_seqplamanu = request.GET.get('filter_descr_seqplamanu', '').strip()
    filter_tipo = request.GET.get('filter_tipo', 'all')  # all, matched, planos_sem, roteiros_sem
    
    # Aplicar filtros
    if filter_maquina:
        try:
            maquina_num = int(float(filter_maquina))
            relacionamentos = [r for r in relacionamentos if r['plano'].cd_maquina == maquina_num or r['roteiro'].cd_maquina == maquina_num]
            planos_sem_relacao = [p for p in planos_sem_relacao if p.cd_maquina == maquina_num]
            roteiros_sem_relacao = [r for r in roteiros_sem_relacao if r.cd_maquina == maquina_num]
        except (ValueError, TypeError):
            relacionamentos = [r for r in relacionamentos if str(r['plano'].cd_maquina).find(filter_maquina) != -1 or str(r['roteiro'].cd_maquina).find(filter_maquina) != -1]
            planos_sem_relacao = [p for p in planos_sem_relacao if str(p.cd_maquina).find(filter_maquina) != -1]
            roteiros_sem_relacao = [r for r in roteiros_sem_relacao if str(r.cd_maquina).find(filter_maquina) != -1]
    
    if filter_descr_seqplamanu:
        relacionamentos = [r for r in relacionamentos if r['descr_seqplamanu'] and filter_descr_seqplamanu.lower() in r['descr_seqplamanu'].lower()]
    
    # Paginação para relacionamentos
    if filter_tipo == 'matched':
        items_to_paginate = relacionamentos
    elif filter_tipo == 'planos_sem':
        items_to_paginate = planos_sem_relacao
    elif filter_tipo == 'roteiros_sem':
        items_to_paginate = roteiros_sem_relacao
    else:
        items_to_paginate = relacionamentos
    
    paginator = Paginator(items_to_paginate, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Preparar dados para o contexto baseado no tipo de filtro
    if filter_tipo == 'matched':
        relacionamentos_display = list(page_obj)
        planos_sem_display = planos_sem_relacao[:50]  # Mostrar alguns mesmo quando não é o foco
        roteiros_sem_display = roteiros_sem_relacao[:50]
    elif filter_tipo == 'planos_sem':
        relacionamentos_display = relacionamentos[:50]
        planos_sem_display = list(page_obj)
        roteiros_sem_display = roteiros_sem_relacao[:50]
    elif filter_tipo == 'roteiros_sem':
        relacionamentos_display = relacionamentos[:50]
        planos_sem_display = planos_sem_relacao[:50]
        roteiros_sem_display = list(page_obj)
    else:  # all
        relacionamentos_display = relacionamentos[:100]  # Limitar a 100 para performance
        planos_sem_display = planos_sem_relacao[:100]
        roteiros_sem_display = roteiros_sem_relacao[:100]
    
    # Contar relacionamentos já vinculados
    total_vinculados = sum(1 for rel in relacionamentos if rel.get('ja_vinculado', False))
    
    context = {
        'page_title': 'Análise de Roteiro e Plano de Preventiva',
        'active_page': 'analise_roteiro_plano_preventiva',
        'relacionamentos': relacionamentos_display,
        'planos_sem_relacao': planos_sem_display,
        'roteiros_sem_relacao': roteiros_sem_display,
        'agrupado_por_descr_seqplamanu': dict(list(agrupado_por_descr_seqplamanu.items())[:20]),  # Top 20
        'agrupado_com_percentuais': dict(list(agrupado_com_percentuais.items())[:20]),  # Top 20 com percentuais
        'total_planos': total_planos,
        'total_roteiros': total_roteiros,
        'total_relacionamentos': total_relacionamentos,
        'total_planos_sem_relacao': total_planos_sem_relacao,
        'total_roteiros_sem_relacao': total_roteiros_sem_relacao,
        'total_vinculados': total_vinculados,
        'filter_maquina': filter_maquina,
        'filter_descr_seqplamanu': filter_descr_seqplamanu,
        'filter_tipo': filter_tipo,
        'page_obj': page_obj,
        'threshold_match': threshold_match,
    }
    return render(request, 'planejamento/analise_roteiro_plano_preventiva.html', context)


def maquina_primaria_secundaria(request):
    """Agrupar Máquinas Primárias e Secundárias"""
    from .models import Maquina, MaquinaPrimariaSecundaria
    from django.contrib import messages
    
    # Buscar máquinas primárias (descr_gerenc = "MÁQUINAS PRINCIPAL")
    maquinas_primarias = Maquina.objects.filter(descr_gerenc__iexact='MÁQUINAS PRINCIPAL').order_by('cd_maquina')
    
    # Buscar máquinas secundárias que ainda não estão relacionadas
    # Excluir máquinas que já são primárias E máquinas que já estão relacionadas como secundárias
    maquinas_secundarias_relacionadas = MaquinaPrimariaSecundaria.objects.values_list('maquina_secundaria_id', flat=True)
    maquinas_secundarias = Maquina.objects.exclude(
        descr_gerenc__iexact='MÁQUINAS PRINCIPAL'
    ).exclude(
        id__in=maquinas_secundarias_relacionadas
    ).order_by('cd_maquina')
    
    # Buscar relacionamentos existentes
    relacionamentos = MaquinaPrimariaSecundaria.objects.select_related('maquina_primaria', 'maquina_secundaria').order_by('-created_at')
    
    # Processar POST para criar relacionamentos
    if request.method == 'POST':
        # Debug: imprimir dados recebidos
        import traceback
        print(f"=== DEBUG MAQUINA PRIMARIA SECUNDARIA ===")
        print(f"POST data: {request.POST}")
        print(f"POST keys: {list(request.POST.keys())}")
        print(f"criar_relacionamento: {'criar_relacionamento' in request.POST}")
        print(f"remover_relacionamento: {'remover_relacionamento' in request.POST}")
        
        if 'criar_relacionamento' in request.POST:
            maquina_primaria_id = request.POST.get('maquina_primaria')
            maquinas_secundarias_ids = request.POST.getlist('maquinas_secundarias')
            observacoes = request.POST.get('observacoes', '').strip()
            
            print(f"maquina_primaria_id: {maquina_primaria_id}")
            print(f"maquinas_secundarias_ids: {maquinas_secundarias_ids}")
            print(f"observacoes: {observacoes}")
            
            if not maquina_primaria_id:
                messages.error(request, 'Por favor, selecione uma máquina primária.')
            elif not maquinas_secundarias_ids or (len(maquinas_secundarias_ids) == 1 and not maquinas_secundarias_ids[0]):
                messages.error(request, 'Por favor, selecione pelo menos uma máquina secundária.')
            else:
                try:
                    maquina_primaria = Maquina.objects.get(id=maquina_primaria_id)
                    if maquina_primaria.descr_gerenc and maquina_primaria.descr_gerenc.upper() != 'MÁQUINAS PRINCIPAL':
                        messages.error(request, 'A máquina selecionada não é uma máquina primária.')
                    else:
                        relacionamentos_criados = 0
                        relacionamentos_duplicados = 0
                        
                        for secundaria_id in maquinas_secundarias_ids:
                            try:
                                maquina_secundaria = Maquina.objects.get(id=secundaria_id)
                                
                                # Verificar se já existe o relacionamento
                                if MaquinaPrimariaSecundaria.objects.filter(
                                    maquina_primaria=maquina_primaria,
                                    maquina_secundaria=maquina_secundaria
                                ).exists():
                                    relacionamentos_duplicados += 1
                                else:
                                    MaquinaPrimariaSecundaria.objects.create(
                                        maquina_primaria=maquina_primaria,
                                        maquina_secundaria=maquina_secundaria,
                                        observacoes=observacoes if observacoes else None
                                    )
                                    relacionamentos_criados += 1
                            except Maquina.DoesNotExist:
                                continue
                        
                        if relacionamentos_criados > 0:
                            messages.success(request, f'{relacionamentos_criados} relacionamento(s) criado(s) com sucesso.')
                        if relacionamentos_duplicados > 0:
                            messages.warning(request, f'{relacionamentos_duplicados} relacionamento(s) já existia(m) e foi(ram) ignorado(s).')
                except Maquina.DoesNotExist:
                    messages.error(request, 'Máquina primária não encontrada.')
                except Exception as e:
                    messages.error(request, f'Erro ao criar relacionamento: {str(e)}')
        
        elif 'remover_relacionamento' in request.POST:
            relacionamento_id = request.POST.get('relacionamento_id')
            if relacionamento_id:
                try:
                    relacionamento = MaquinaPrimariaSecundaria.objects.get(id=relacionamento_id)
                    relacionamento.delete()
                    messages.success(request, 'Relacionamento removido com sucesso.')
                except MaquinaPrimariaSecundaria.DoesNotExist:
                    messages.error(request, 'Relacionamento não encontrado.')
                except Exception as e:
                    messages.error(request, f'Erro ao remover relacionamento: {str(e)}')
        
        return redirect('maquina_primaria_secundaria')
    
    context = {
        'page_title': 'Agrupar Máquinas Primárias e Secundárias',
        'active_page': 'maquina_primaria_secundaria',
        'maquinas_primarias': maquinas_primarias,
        'maquinas_secundarias': maquinas_secundarias,
        'relacionamentos': relacionamentos
    }
    return render(request, 'planejamento/maquina_primaria_secundaria.html', context)


def contact(request):
    """Contact page view"""
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        newsletter = request.POST.get('newsletter', False)
        
        # Basic validation
        if not all([name, email, subject, message]):
            messages.error(request, 'Por favor, preencha todos os campos obrigatórios.')
        else:
            # Here you would typically save to database or send email
            # For now, we'll just show a success message
            messages.success(request, f'Obrigado {name}! Sua mensagem foi enviada com sucesso. Entraremos em contato em breve.')
            
            # Optional: Send email notification
            try:
                send_mail(
                    f'Contato via site - {subject}',
                    f'Nome: {name}\nEmail: {email}\nTelefone: {phone}\nAssunto: {subject}\nMensagem: {message}',
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.DEFAULT_FROM_EMAIL],
                    fail_silently=False,
                )
            except Exception as e:
                # Log the error but don't show it to the user
                print(f"Email sending failed: {e}")
            
            return redirect('contact')
    
    context = {
        'page_title': 'Contato',
        'active_page': 'contact'
    }
    return render(request, 'contact.html', context)


def services(request):
    """Services page view"""
    context = {
        'page_title': 'Serviços',
        'active_page': 'services'
    }
    return render(request, 'services.html', context)


def abate_area_suja(request):
    """ABT - 2488 - Abate e Resfriamento - Área Suja page view"""
    context = {
        'page_title': 'ABT - 2488 - Abate e Resfriamento - Área Suja',
        'active_page': 'abate_area_suja'
    }
    return render(request, 'centros_de_atividade/abate_area_suja.html', context)


def recepcao(request):
    """REC - 2216 - Recepção de Suínos page view"""
    context = {
        'page_title': 'REC - 2216 - Recepção de Suínos',
        'active_page': 'recepcao'
    }
    return render(request, 'centros_de_atividade/recepcao.html', context)


def area_limpa(request):
    """ABT - 2488 - Abate e Resfriamento - Área Limpa page view"""
    context = {
        'page_title': 'ABT - 2488 - Abate e Resfriamento - Área Limpa',
        'active_page': 'area_limpa'
    }
    return render(request, 'centros_de_atividade/area_limpa.html', context)


def camaras(request):
    """ABT - 2488 - Abate e Resfriamento - Câmaras de Resfriamento page view"""
    context = {
        'page_title': 'ABT - 2488 - Abate e Resfriamento - Câmaras de Resfriamento',
        'active_page': 'camaras'
    }
    return render(request, 'centros_de_atividade/camaras.html', context)


def bet(request):
    """BET - 2232 - Beneficiamento de Tripas page view"""
    context = {
        'page_title': 'BET - 2232 - Beneficiamento de Tripas',
        'active_page': 'bet'
    }
    return render(request, 'centros_de_atividade/bet.html', context)


def salga(request):
    """SLG - 2241 - Salga page view"""
    context = {
        'page_title': 'SLG - 2241 - Salga',
        'active_page': 'salga'
    }
    return render(request, 'centros_de_atividade/salga.html', context)


def min(request):
    """MIN - 2721 - Miúdos Internos page view"""
    context = {
        'page_title': 'MIN - 2721 - Miúdos Internos',
        'active_page': 'min'
    }
    return render(request, 'centros_de_atividade/min.html', context)


def mex(request):
    """MEX - 2729 - Miúdos Externos page view"""
    context = {
        'page_title': 'MEX - 2729 - Miúdos Externos',
        'active_page': 'mex'
    }
    return render(request, 'centros_de_atividade/mex.html', context)


def epj(request):
    """EPJ - 2224 - Espostejamento page view"""
    from .models import Maquina, MaquinaPrimariaSecundaria
    
    # Buscar máquinas primárias com cd_tpcentativ = 2224 e descr_setormanut = "MÁQUINAS PRINCIPAL"
    maquinas_primarias = Maquina.objects.filter(
        cd_tpcentativ=2224,
        descr_setormanut__iexact='MÁQUINAS PRINCIPAL'
    ).order_by('cd_maquina')
    
    # Para cada máquina primária, buscar suas máquinas secundárias relacionadas
    maquinas_com_relacionamentos = []
    for maquina_primaria in maquinas_primarias:
        relacionamentos = MaquinaPrimariaSecundaria.objects.filter(
            maquina_primaria=maquina_primaria
        ).select_related('maquina_secundaria').order_by('maquina_secundaria__cd_maquina')
        
        maquinas_secundarias = [rel.maquina_secundaria for rel in relacionamentos]
        
        maquinas_com_relacionamentos.append({
            'primaria': maquina_primaria,
            'secundarias': maquinas_secundarias,
            'relacionamentos': relacionamentos
        })
    
    context = {
        'page_title': 'EPJ - 2224 - Espostejamento',
        'active_page': 'epj',
        'maquinas_com_relacionamentos': maquinas_com_relacionamentos
    }
    return render(request, 'centros_de_atividade/epj.html', context)


def epj_maquinas(request):
    """EPJ - Máquinas do Centro de Atividade 2224 page view"""
    from .models import Maquina
    
    # Buscar todas as máquinas com cd_tpcentativ = 2224
    # Forçar avaliação do QuerySet para garantir dados atualizados a cada requisição
    maquinas_ca_2224 = list(Maquina.objects.filter(cd_tpcentativ=2224).order_by('cd_maquina'))
    
    # Buscar máquinas primárias com cd_tpcentativ = 2224 e descr_gerenc = "MÁQUINAS PRINCIPAL"
    # Forçar avaliação do QuerySet para garantir dados atualizados a cada requisição
    maquinas_primarias = list(Maquina.objects.filter(
        cd_tpcentativ=2224,
        descr_gerenc__iexact='MÁQUINAS PRINCIPAL'
    ).order_by('cd_maquina'))
    
    context = {
        'page_title': 'EPJ - Máquinas do Centro de Atividade 2224',
        'active_page': 'epj_maquinas',
        'maquinas_ca_2224': maquinas_ca_2224,
        'maquinas_primarias': maquinas_primarias
    }
    
    response = render(request, 'ca_maquinas/epj_maquinas.html', context)
    # Adicionar headers para evitar cache do navegador
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


def cms(request):
    """CMS - 4120 - Produção CMS page view"""
    context = {
        'page_title': 'CMS - 4120 - Produção CMS',
        'active_page': 'cms'
    }
    return render(request, 'centros_de_atividade/cms.html', context)


def lbm(request):
    """LBM - 2470 - Lavagem Bacias / Monoblocos page view"""
    context = {
        'page_title': 'LBM - 2470 - Lavagem Bacias / Monoblocos',
        'active_page': 'lbm'
    }
    return render(request, 'centros_de_atividade/lbm.html', context)


def dpe(request):
    """DPE - 2461 - Depósito e Preparação de Embalagens page view"""
    context = {
        'page_title': 'DPE - 2461 - Depósito e Preparação de Embalagens',
        'active_page': 'dpe'
    }
    return render(request, 'centros_de_atividade/dpe.html', context)


def secundaria(request):
    """EMB - 4138 - Embalagem Secundária page view"""
    context = {
        'page_title': 'EMB - 4138 - Embalagem Secundária',
        'active_page': 'secundaria'
    }
    return render(request, 'centros_de_atividade/secundaria.html', context)


def tca(request):
    """TCA - 2313 - Túneis e Câmaras page view"""
    context = {
        'page_title': 'TCA - 2313 - Túneis e Câmaras',
        'active_page': 'tca'
    }
    return render(request, 'centros_de_atividade/tca.html', context)


def tca_gea(request):
    """TCA - 2313 - Túneis e Câmaras - Túnel GEA page view"""
    context = {
        'page_title': 'TCA - 2313 - Túneis e Câmaras - Túnel GEA',
        'active_page': 'tca_gea'
    }
    return render(request, 'centros_de_atividade/tca_gea.html', context)


def expedicao(request):
    """EXD - 2348 - Expedição page view"""
    context = {
        'page_title': 'EXD - 2348 - Expedição',
        'active_page': 'expedicao'
    }
    return render(request, 'centros_de_atividade/expedicao.html', context)


def frescal(request):
    """SFR - 4057 - Embutideos Frescais page view"""
    context = {
        'page_title': 'SFR - 4057 - Embutideos Frescais',
        'active_page': 'frescal'
    }
    return render(request, 'centros_de_atividade/frescal.html', context)


def presunto(request):
    """PRU - 2291 - Presuntaria page view"""
    context = {
        'page_title': 'PRU - 2291 - Presuntaria',
        'active_page': 'presunto'
    }
    return render(request, 'centros_de_atividade/presunto.html', context)


def estufa(request):
    """EST - 4588 - Estufas page view"""
    context = {
        'page_title': 'EST - 4588 - Estufas',
        'active_page': 'estufa'
    }
    return render(request, 'centros_de_atividade/estufa.html', context)


def fatiados(request):
    """SFT - 4600 - Fatiados page view"""
    context = {
        'page_title': 'SFT - 4600 - Fatiados',
        'active_page': 'fatiados'
    }
    return render(request, 'centros_de_atividade/fatiados.html', context)


def condimentaria(request):
    """COD - 4472 - Condimentaria page view"""
    context = {
        'page_title': 'COD - 4472 - Condimentaria',
        'active_page': 'condimentaria'
    }
    return render(request, 'centros_de_atividade/condimentaria.html', context)


def defumados(request):
    """DEF - 2496 - Defumados page view"""
    context = {
        'page_title': 'DEF - 2496 - Defumados',
        'active_page': 'defumados'
    }
    return render(request, 'centros_de_atividade/defumados.html', context)


def marinados(request):
    """SMR - 2267 - Marinados page view"""
    context = {
        'page_title': 'SMR - 2267 - Marinados',
        'active_page': 'marinados'
    }
    return render(request, 'centros_de_atividade/marinados.html', context)


def cozidos(request):
    """2283 - CEB - Embutidos Cozidos page view"""
    context = {
        'page_title': '2283 - CEB - Embutidos Cozidos',
        'active_page': 'cozidos'
    }
    return render(request, 'centros_de_atividade/cozidos.html', context)


def preparo_de_massa(request):
    """2276 - SPM - Preparo de Massa page view"""
    context = {
        'page_title': '2276 - SPM - Preparo de Massa',
        'active_page': 'preparo_de_massa'
    }
    return render(request, 'centros_de_atividade/preparo_de_massa.html', context)


def curados(request):
    """CUR - 2267 - Embutidos Curados page view"""
    context = {
        'page_title': 'CUR - 2267 - Embutidos Curados',
        'active_page': 'curados'
    }
    return render(request, 'centros_de_atividade/curados.html', context)


def embalagem_industrializados(request):
    """5345 - SEI - Embalagem Industrializados page view"""
    context = {
        'page_title': '5345 - SEI - Embalagem Industrializados',
        'active_page': 'embalagem_industrializados'
    }
    return render(request, 'centros_de_atividade/embalagem_industrializados.html', context)


def importar_maquinas(request):
    """Importar Máquinas page view"""
    if request.method == 'POST':
        # Verificar se há arquivo enviado
        if 'file' not in request.FILES:
            messages.error(request, 'Por favor, selecione um arquivo para importar.')
            context = {
                'page_title': 'Importar Máquinas',
                'active_page': 'importar_maquinas'
            }
            return render(request, 'importar/maquinas.html', context)
        
        file = request.FILES['file']
        
        # Validar extensão do arquivo
        allowed_extensions = ['.xlsx', '.xls', '.xlsm', '.csv']
        file_extension = '.' + file.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            messages.error(
                request, 
                f'Formato de arquivo não suportado. Use: {", ".join(allowed_extensions)}'
            )
            context = {
                'page_title': 'Importar Máquinas',
                'active_page': 'importar_maquinas'
            }
            return render(request, 'importar/maquinas.html', context)
        
        # Verificar se deve apenas adicionar novos registros (ignorar duplicados)
        only_new_records = request.POST.get('only_new_records', 'off') == 'on'
        
        # Verificar se deve atualizar registros existentes
        # Se only_new_records estiver marcado, update_existing será ignorado
        update_existing = False
        if not only_new_records:
            update_existing = request.POST.get('update_existing', 'off') == 'on'
        
        try:
            from app.utils import upload_maquinas_from_file
            
            # Fazer upload dos dados
            # Se only_new_records estiver marcado, update_existing será False (ignora duplicados)
            created_count, updated_count, errors = upload_maquinas_from_file(
                file, 
                update_existing=update_existing
            )
            
            # Preparar mensagens
            if errors:
                for error in errors[:10]:  # Mostrar apenas os primeiros 10 erros
                    messages.warning(request, error)
                if len(errors) > 10:
                    messages.warning(
                        request, 
                        f'... e mais {len(errors) - 10} erro(s). Verifique o arquivo.'
                    )
            
            if created_count > 0 or updated_count > 0:
                success_msg = f'Importação concluída com sucesso! '
                if created_count > 0:
                    success_msg += f'{created_count} registro(s) criado(s). '
                if updated_count > 0:
                    success_msg += f'{updated_count} registro(s) atualizado(s).'
                messages.success(request, success_msg)
            elif not errors:
                messages.info(request, 'Nenhum registro foi importado.')
            
        except Exception as e:
            messages.error(request, f'Erro ao importar arquivo: {str(e)}')
    
    context = {
        'page_title': 'Importar Máquinas',
        'active_page': 'importar_maquinas'
    }
    return render(request, 'importar/maquinas.html', context)


def importar_manutentores(request):
    """Importar Manutentores page view"""
    if request.method == 'POST':
        print(f"DEBUG - POST recebido! Files: {list(request.FILES.keys())}")
        # Verificar se há arquivo enviado
        if 'file' not in request.FILES:
            messages.error(request, 'Por favor, selecione um arquivo para importar.')
            context = {
                'page_title': 'Importar Manutentores',
                'active_page': 'importar_manutentores'
            }
            return render(request, 'importar/manutentores.html', context)
        
        file = request.FILES['file']
        print(f"DEBUG - Arquivo recebido: {file.name}, Tamanho: {file.size}")
        
        # Validar extensão do arquivo
        allowed_extensions = ['.xlsx', '.xls', '.xlsm', '.csv']
        file_extension = '.' + file.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            messages.error(
                request, 
                f'Formato de arquivo não suportado. Use: {", ".join(allowed_extensions)}'
            )
            context = {
                'page_title': 'Importar Manutentores',
                'active_page': 'importar_manutentores'
            }
            return render(request, 'importar/manutentores.html', context)
        
        # Verificar se deve atualizar registros existentes
        update_existing = request.POST.get('update_existing', 'off') == 'on'
        print(f"DEBUG - Update existing: {update_existing}")
        
        try:
            from app.utils import upload_manutentores_from_file
            
            # Fazer upload dos dados
            print("DEBUG - Iniciando upload...")
            created_count, updated_count, errors = upload_manutentores_from_file(
                file,
                update_existing=update_existing
            )
            
            print(f"DEBUG - Upload concluído: {created_count} criados, {updated_count} atualizados, {len(errors)} erros")
            
            # Exibir mensagens
            if created_count > 0:
                messages.success(request, f'{created_count} manutentor(es) criado(s) com sucesso!')
            if updated_count > 0:
                messages.info(request, f'{updated_count} manutentor(es) atualizado(s) com sucesso!')
            if errors:
                for error in errors[:10]:  # Limitar a 10 erros para não sobrecarregar
                    messages.warning(request, error)
                if len(errors) > 10:
                    messages.warning(request, f'... e mais {len(errors) - 10} erro(s). Verifique o arquivo.')
            if created_count == 0 and updated_count == 0 and not errors:
                messages.info(request, 'Nenhum registro foi importado. Verifique se o arquivo contém dados válidos.')
        
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"DEBUG - Erro durante upload: {error_detail}")
            messages.error(request, f'Erro ao importar arquivo: {str(e)}')
        
        # Sempre redirecionar para consultar_manutentores após importação
        return redirect('consultar_manutentores')
    
    context = {
        'page_title': 'Importar Manutentores',
        'active_page': 'importar_manutentores'
    }
    return render(request, 'importar/manutentores.html', context)


def importar_ordens_corretivas_e_outros(request):
    """Importar Ordens Corretivas e Outros page view"""
    if request.method == 'POST':
        print(f"DEBUG - POST recebido! Files: {list(request.FILES.keys())}")
        # Verificar se há arquivo enviado
        if 'file' not in request.FILES:
            messages.error(request, 'Por favor, selecione um arquivo para importar.')
            context = {
                'page_title': 'Importar Ordens Corretivas e Outros',
                'active_page': 'importar_ordens_corretivas_e_outros'
            }
            return render(request, 'importar/ordens_corretivas_e_outros.html', context)
        
        file = request.FILES['file']
        print(f"DEBUG - Arquivo recebido: {file.name}, Tamanho: {file.size}")
        
        # Validar extensão do arquivo
        allowed_extensions = ['.xlsx', '.xls', '.xlsm', '.csv']
        file_extension = '.' + file.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            messages.error(
                request, 
                f'Formato de arquivo não suportado. Use: {", ".join(allowed_extensions)}'
            )
            context = {
                'page_title': 'Importar Ordens Corretivas e Outros',
                'active_page': 'importar_ordens_corretivas_e_outros'
            }
            return render(request, 'importar/ordens_corretivas_e_outros.html', context)
        
        # Verificar se deve atualizar registros existentes
        update_existing = request.POST.get('update_existing', 'off') == 'on'
        print(f"DEBUG - Update existing: {update_existing}")
        
        try:
            from app.utils import upload_ordens_corretivas_from_file
            
            # Fazer upload dos dados
            print("DEBUG - Iniciando upload...")
            created_count, updated_count, errors = upload_ordens_corretivas_from_file(
                file, 
                update_existing=update_existing
            )
            print(f"DEBUG - Upload concluído: criados={created_count}, atualizados={updated_count}, erros={len(errors)}")
            
            # Preparar mensagens
            if errors:
                for error in errors[:10]:  # Mostrar apenas os primeiros 10 erros
                    messages.warning(request, error)
                if len(errors) > 10:
                    messages.warning(
                        request, 
                        f'... e mais {len(errors) - 10} erro(s). Verifique o arquivo.'
                    )
            
            # Sempre redirecionar após tentativa de importação, independente do resultado
            if created_count > 0 or updated_count > 0:
                success_msg = f'Importação concluída com sucesso! '
                if created_count > 0:
                    success_msg += f'{created_count} registro(s) criado(s). '
                if updated_count > 0:
                    success_msg += f'{updated_count} registro(s) atualizado(s).'
                messages.success(request, success_msg)
            elif not errors:
                messages.info(request, 'Nenhum registro foi importado.')
            else:
                # Se houver apenas erros, ainda redireciona mas mostra os erros
                messages.warning(request, 'Importação concluída com erros. Verifique as mensagens acima.')
            
            # Redirecionar para a página de consulta após importação
            return redirect('consultar_corretivas_outros')
            
        except Exception as e:
            import traceback
            print(f"DEBUG - Erro: {str(e)}")
            print(f"DEBUG - Traceback: {traceback.format_exc()}")
            messages.error(request, f'Erro ao importar arquivo: {str(e)}')
            # Redirecionar mesmo em caso de erro para não ficar na página de importação
            return redirect('consultar_corretivas_outros')
    
    context = {
        'page_title': 'Importar Ordens Corretivas e Outros',
        'active_page': 'importar_ordens_corretivas_e_outros'
    }
    return render(request, 'importar/ordens_corretivas_e_outros.html', context)


def importar_ordens_preventivas(request):
    """Importar Ordens Preventivas page view"""
    context = {
        'page_title': 'Importar Ordens Preventivas',
        'active_page': 'importar_ordens_preventivas'
    }
    return render(request, 'importar/ordens_preventivas.html', context)


def importar_plano_preventiva(request):
    """Importar Plano Preventiva page view"""
    if request.method == 'POST':
        # Verificar se há arquivo enviado
        if 'file' not in request.FILES:
            messages.error(request, 'Por favor, selecione um arquivo para importar.')
            context = {
                'page_title': 'Importar Plano Preventiva',
                'active_page': 'importar_plano_preventiva'
            }
            return render(request, 'importar/importar_plano_preventiva.html', context)
        
        file = request.FILES['file']
        
        # Validar extensão do arquivo
        allowed_extensions = ['.xlsx', '.xls', '.xlsm', '.csv']
        file_extension = '.' + file.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            messages.error(
                request, 
                f'Formato de arquivo não suportado. Use: {", ".join(allowed_extensions)}'
            )
            context = {
                'page_title': 'Importar Plano Preventiva',
                'active_page': 'importar_plano_preventiva'
            }
            return render(request, 'importar/importar_plano_preventiva.html', context)
        
        # Verificar se deve apenas adicionar novos registros (ignorar duplicados)
        only_new_records = request.POST.get('only_new_records', 'off') == 'on'
        
        # Verificar se deve atualizar registros existentes
        # Se only_new_records estiver marcado, update_existing será ignorado
        update_existing = False
        if not only_new_records:
            update_existing = request.POST.get('update_existing', 'off') == 'on'
        
        try:
            from app.utils import upload_plano_preventiva_from_file
            
            # Fazer upload dos dados
            # Se only_new_records estiver marcado, update_existing será False (ignora duplicados)
            created_count, updated_count, errors = upload_plano_preventiva_from_file(
                file, 
                update_existing=update_existing
            )
            
            # Preparar mensagens
            if errors:
                for error in errors[:10]:  # Mostrar apenas os primeiros 10 erros
                    messages.warning(request, error)
                if len(errors) > 10:
                    messages.warning(request, f'... e mais {len(errors) - 10} erros.')
            
            if created_count > 0:
                messages.success(request, f'{created_count} registro(s) de plano preventiva criado(s) com sucesso!')
            if updated_count > 0:
                messages.info(request, f'{updated_count} registro(s) de plano preventiva atualizado(s)!')
            if created_count == 0 and updated_count == 0 and not errors:
                messages.info(request, 'Nenhum registro novo foi importado. Todos os registros já existem no banco de dados.')
            
        except Exception as e:
            messages.error(request, f'Erro ao importar arquivo: {str(e)}')
    
    context = {
        'page_title': 'Importar Plano Preventiva',
        'active_page': 'importar_plano_preventiva'
    }
    return render(request, 'importar/importar_plano_preventiva.html', context)


def importar_roteiro_preventiva(request):
    """Importar Roteiro Preventiva page view"""
    if request.method == 'POST':
        # Verificar se há arquivo enviado
        if 'file' not in request.FILES:
            messages.error(request, 'Por favor, selecione um arquivo para importar.')
            context = {
                'page_title': 'Importar Roteiro Preventiva',
                'active_page': 'importar_roteiro_preventiva'
            }
            return render(request, 'importar/importar_roteiro_preventiva.html', context)
        
        file = request.FILES['file']
        
        # Validar extensão do arquivo
        allowed_extensions = ['.xlsx', '.xls', '.xlsm', '.csv']
        file_extension = '.' + file.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            messages.error(
                request, 
                f'Formato de arquivo não suportado. Use: {", ".join(allowed_extensions)}'
            )
            context = {
                'page_title': 'Importar Roteiro Preventiva',
                'active_page': 'importar_roteiro_preventiva'
            }
            return render(request, 'importar/importar_roteiro_preventiva.html', context)
        
        # Verificar se deve apenas adicionar novos registros (ignorar duplicados)
        only_new_records = request.POST.get('only_new_records', 'off') == 'on'
        
        # Verificar se deve atualizar registros existentes
        # Se only_new_records estiver marcado, update_existing será ignorado
        update_existing = False
        if not only_new_records:
            update_existing = request.POST.get('update_existing', 'off') == 'on'
        
        try:
            from app.utils import upload_roteiro_preventiva_from_file
            
            # Fazer upload dos dados
            # Se only_new_records estiver marcado, update_existing será False (ignora duplicados)
            created_count, updated_count, errors = upload_roteiro_preventiva_from_file(
                file, 
                update_existing=update_existing
            )
            
            # Preparar mensagens
            if errors:
                for error in errors[:10]:  # Mostrar apenas os primeiros 10 erros
                    messages.warning(request, error)
                if len(errors) > 10:
                    messages.warning(request, f'... e mais {len(errors) - 10} erros.')
            
            if created_count > 0:
                messages.success(request, f'{created_count} registro(s) de roteiro preventiva criado(s) com sucesso!')
            if updated_count > 0:
                messages.info(request, f'{updated_count} registro(s) de roteiro preventiva atualizado(s)!')
            if created_count == 0 and updated_count == 0 and not errors:
                messages.info(request, 'Nenhum registro novo foi importado. Todos os registros já existem no banco de dados.')
            
        except Exception as e:
            messages.error(request, f'Erro ao importar arquivo: {str(e)}')
    
    context = {
        'page_title': 'Importar Roteiro Preventiva',
        'active_page': 'importar_roteiro_preventiva'
    }
    return render(request, 'importar/importar_roteiro_preventiva.html', context)


def importar_estoque(request):
    """Importar Estoque page view"""
    if request.method == 'POST':
        # Verificar se há arquivo enviado
        if 'file' not in request.FILES:
            messages.error(request, 'Por favor, selecione um arquivo para importar.')
            context = {
                'page_title': 'Importar Estoque',
                'active_page': 'importar_estoque'
            }
            return render(request, 'importar/estoque.html', context)
        
        file = request.FILES['file']
        
        # Validar extensão do arquivo
        allowed_extensions = ['.xlsx', '.xls', '.xlsm', '.csv']
        file_extension = '.' + file.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            messages.error(
                request, 
                f'Formato de arquivo não suportado. Use: {", ".join(allowed_extensions)}'
            )
            context = {
                'page_title': 'Importar Estoque',
                'active_page': 'importar_estoque'
            }
            return render(request, 'importar/estoque.html', context)
        
        # Verificar se deve atualizar registros existentes
        update_existing = request.POST.get('update_existing', 'off') == 'on'
        
        try:
            from app.utils import upload_itens_estoque_from_file
            
            # Fazer upload dos dados
            created_count, updated_count, errors = upload_itens_estoque_from_file(
                file,
                update_existing=update_existing
            )
            
            # Preparar mensagens
            if errors:
                for error in errors[:10]:  # Mostrar apenas os primeiros 10 erros
                    messages.warning(request, error)
                if len(errors) > 10:
                    messages.warning(
                        request,
                        f'... e mais {len(errors) - 10} erro(s). Verifique o arquivo.'
                    )
            
            if created_count > 0 or updated_count > 0:
                success_msg = f'Importação concluída com sucesso! '
                if created_count > 0:
                    success_msg += f'{created_count} registro(s) criado(s). '
                if updated_count > 0:
                    success_msg += f'{updated_count} registro(s) atualizado(s).'
                messages.success(request, success_msg)
            elif not errors:
                messages.info(request, 'Nenhum registro foi importado.')
            else:
                messages.warning(request, 'Importação concluída com erros. Verifique as mensagens acima.')
            
        except Exception as e:
            import traceback
            messages.error(request, f'Erro ao importar arquivo: {str(e)}')
            print(f"DEBUG - Erro: {str(e)}")
            print(f"DEBUG - Traceback: {traceback.format_exc()}")
    
    context = {
        'page_title': 'Importar Estoque',
        'active_page': 'importar_estoque'
    }
    return render(request, 'importar/estoque.html', context)


def consultar_estoque(request):
    """Consultar/listar itens de estoque cadastrados com filtros avançados"""
    from app.models import ItemEstoque
    from decimal import Decimal
    
    # Buscar todos os itens de estoque
    itens_list = ItemEstoque.objects.all()
    
    # Filtro de busca geral (texto)
    search_query = request.GET.get('search', '').strip()
    print(f"DEBUG consultar_estoque - search_query: '{search_query}'")
    print(f"DEBUG consultar_estoque - request.GET: {dict(request.GET)}")
    if search_query:
        # Criar lista de condições Q
        search_conditions = Q()
        
        # Para campos numéricos, tentar converter e fazer busca exata
        try:
            search_num = int(float(search_query))
            search_conditions |= Q(codigo_item=search_num)
            print(f"DEBUG consultar_estoque - Added numeric search for codigo_item={search_num}")
        except (ValueError, TypeError):
            print(f"DEBUG consultar_estoque - Could not convert '{search_query}' to number")
            pass
        
        # Para campos de texto, usar icontains
        text_conditions = (
            Q(descricao_item__icontains=search_query) |
            Q(unidade_medida__icontains=search_query) |
            Q(descricao_dest_uso__icontains=search_query) |
            Q(classificacao_tempo_sem_consumo__icontains=search_query)
        )
        search_conditions |= text_conditions
        print(f"DEBUG consultar_estoque - Added text search conditions")
        
        itens_list = itens_list.filter(search_conditions)
        print(f"DEBUG consultar_estoque - Filtered count: {itens_list.count()}")
    
    # Filtros específicos
    # Filtro por Unidade de Medida
    filtro_unidade_medida = request.GET.get('filtro_unidade_medida', '')
    if filtro_unidade_medida:
        itens_list = itens_list.filter(unidade_medida__icontains=filtro_unidade_medida)
    
    # Filtro por Destino de Uso
    filtro_destino_uso = request.GET.get('filtro_destino_uso', '')
    if filtro_destino_uso:
        itens_list = itens_list.filter(descricao_dest_uso__icontains=filtro_destino_uso)
    
    # Filtro por Controla Estoque Mínimo
    filtro_controla_estoque = request.GET.get('filtro_controla_estoque', '')
    if filtro_controla_estoque:
        itens_list = itens_list.filter(controla_estoque_minimo__icontains=filtro_controla_estoque)
    
    # Filtro por Classificação Tempo Sem Consumo
    filtro_classificacao = request.GET.get('filtro_classificacao', '')
    if filtro_classificacao:
        itens_list = itens_list.filter(classificacao_tempo_sem_consumo__icontains=filtro_classificacao)
    
    # Filtro por Estante
    filtro_estante = request.GET.get('filtro_estante', '')
    if filtro_estante:
        try:
            estante_num = int(filtro_estante)
            itens_list = itens_list.filter(estante=estante_num)
        except ValueError:
            pass
    
    # Filtro por Prateleira
    filtro_prateleira = request.GET.get('filtro_prateleira', '')
    if filtro_prateleira:
        try:
            prateleira_num = int(filtro_prateleira)
            itens_list = itens_list.filter(prateleira=prateleira_num)
        except ValueError:
            pass
    
    # Filtro por Quantidade (mínima e máxima)
    quantidade_min = request.GET.get('quantidade_min', '')
    quantidade_max = request.GET.get('quantidade_max', '')
    if quantidade_min:
        try:
            qtd_min = Decimal(quantidade_min)
            itens_list = itens_list.filter(quantidade__gte=qtd_min)
        except (ValueError, TypeError):
            pass
    if quantidade_max:
        try:
            qtd_max = Decimal(quantidade_max)
            itens_list = itens_list.filter(quantidade__lte=qtd_max)
        except (ValueError, TypeError):
            pass
    
    # Ordenar por código do item
    itens_list = itens_list.order_by('codigo_item')
    
    # Paginação
    paginator = Paginator(itens_list, 50)  # 50 itens por página
    page_number = request.GET.get('page', 1)
    itens = paginator.get_page(page_number)
    
    # Estatísticas
    total_count = ItemEstoque.objects.count()
    unidades_count = ItemEstoque.objects.exclude(unidade_medida__isnull=True).exclude(unidade_medida='').values('unidade_medida').distinct().count()
    destinos_count = ItemEstoque.objects.exclude(descricao_dest_uso__isnull=True).exclude(descricao_dest_uso='').values('descricao_dest_uso').distinct().count()
    
    # Obter valores únicos para os dropdowns de filtros
    unidades_medida_unicas = ItemEstoque.objects.exclude(
        unidade_medida__isnull=True
    ).exclude(
        unidade_medida=''
    ).values_list('unidade_medida', flat=True).distinct().order_by('unidade_medida')
    
    destinos_uso_unicos = ItemEstoque.objects.exclude(
        descricao_dest_uso__isnull=True
    ).exclude(
        descricao_dest_uso=''
    ).values_list('descricao_dest_uso', flat=True).distinct().order_by('descricao_dest_uso')
    
    classificacoes_unicas = ItemEstoque.objects.exclude(
        classificacao_tempo_sem_consumo__isnull=True
    ).exclude(
        classificacao_tempo_sem_consumo=''
    ).values_list('classificacao_tempo_sem_consumo', flat=True).distinct().order_by('classificacao_tempo_sem_consumo')
    
    context = {
        'page_title': 'Consultar Estoque',
        'active_page': 'consultar_estoque',
        'itens': itens,
        'total_count': total_count,
        'unidades_count': unidades_count,
        'destinos_count': destinos_count,
        # Valores dos filtros ativos
        'filtro_unidade_medida': filtro_unidade_medida,
        'filtro_destino_uso': filtro_destino_uso,
        'filtro_controla_estoque': filtro_controla_estoque,
        'filtro_classificacao': filtro_classificacao,
        'filtro_estante': filtro_estante,
        'filtro_prateleira': filtro_prateleira,
        'quantidade_min': quantidade_min,
        'quantidade_max': quantidade_max,
        # Valores únicos para dropdowns
        'unidades_medida_unicas': unidades_medida_unicas,
        'destinos_uso_unicos': destinos_uso_unicos,
        'classificacoes_unicas': classificacoes_unicas,
    }
    return render(request, 'consultar/consultar_estoque.html', context)


def importar_locais_e_cas(request):
    """Importar Locais e CAs page view"""
    print(f"DEBUG - Método da requisição: {request.method}")
    if request.method == 'POST':
        print("DEBUG - POST recebido!")
        # Verificar se há arquivo enviado
        if 'file' not in request.FILES:
            messages.error(request, 'Por favor, selecione um arquivo para importar.')
            context = {
                'page_title': 'Importar Locais e CAs',
                'active_page': 'importar_locais_e_cas'
            }
            return render(request, 'importar/locais_e_cas.html', context)
        
        file = request.FILES['file']
        
        # Validar extensão do arquivo
        allowed_extensions = ['.xlsx', '.xls', '.xlsm', '.csv']
        file_extension = '.' + file.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            messages.error(
                request, 
                f'Formato de arquivo não suportado. Use: {", ".join(allowed_extensions)}'
            )
            context = {
                'page_title': 'Importar Locais e CAs',
                'active_page': 'importar_locais_e_cas'
            }
            return render(request, 'importar/locais_e_cas.html', context)
        
        # Verificar se deve apenas adicionar novos registros (ignorar duplicados)
        only_new_records = request.POST.get('only_new_records', 'off') == 'on'
        
        # Verificar se deve atualizar registros existentes
        # Se only_new_records estiver marcado, update_existing será ignorado
        update_existing = False
        if not only_new_records:
            update_existing = request.POST.get('update_existing', 'off') == 'on'
        
        try:
            from app.utils import upload_cas_from_file
            
            # Fazer upload dos dados
            # Se only_new_records estiver marcado, update_existing será False (ignora duplicados)
            created_count, updated_count, errors = upload_cas_from_file(
                file, 
                update_existing=update_existing
            )
            
            # Preparar mensagens
            if errors:
                for error in errors[:10]:  # Mostrar apenas os primeiros 10 erros
                    messages.warning(request, error)
                if len(errors) > 10:
                    messages.warning(
                        request, 
                        f'... e mais {len(errors) - 10} erro(s). Verifique o arquivo.'
                    )
            
            if created_count > 0 or updated_count > 0:
                success_msg = f'Importação concluída com sucesso! '
                if created_count > 0:
                    success_msg += f'{created_count} registro(s) criado(s). '
                if updated_count > 0:
                    success_msg += f'{updated_count} registro(s) atualizado(s).'
                messages.success(request, success_msg)
            elif not errors:
                messages.info(request, 'Nenhum registro foi importado.')
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            messages.error(request, f'Erro ao importar arquivo: {str(e)}')
            print(f"DEBUG - Erro ao importar: {error_detail}")
    
    context = {
        'page_title': 'Importar Locais e CAs',
        'active_page': 'importar_locais_e_cas'
    }
    return render(request, 'importar/locais_e_cas.html', context)


def cadastrar_local_e_cas(request):
    """Cadastrar novo Centro de Atividade (CA) com múltiplos locais"""
    from app.forms import CentroAtividadeForm, LocalCentroAtividadeFormSet
    
    if request.method == 'POST':
        form = CentroAtividadeForm(request.POST)
        formset = LocalCentroAtividadeFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            try:
                centro_atividade = form.save()
                formset.instance = centro_atividade
                formset.save()
                messages.success(request, f'Centro de Atividade {centro_atividade.ca} cadastrado com sucesso!')
                return redirect('consultar_locais_e_cas')
            except Exception as e:
                messages.error(request, f'Erro ao cadastrar Centro de Atividade: {str(e)}')
        else:
            handle_form_errors(form, request)
            if formset.errors:
                for error in formset.non_form_errors():
                    messages.error(request, f'Erro no formulário: {error}')
    else:
        form = CentroAtividadeForm()
        formset = LocalCentroAtividadeFormSet()
    
    context = {
        'page_title': 'Cadastrar Local e CA',
        'active_page': 'cadastrar_local_e_cas',
        'form': form,
        'formset': formset
    }
    return render(request, 'cadastrar/cadastrar_local_e_cas.html', context)


def consultar_locais_e_cas(request):
    """Consultar/listar Centros de Atividade (CA) cadastrados"""
    from app.models import CentroAtividade
    
    # Buscar todos os centros de atividade
    cas_list = CentroAtividade.objects.all()
    
    # Filtro de busca geral
    search_query = request.GET.get('search', '').strip()
    if search_query:
        # Criar lista de condições Q
        search_conditions = Q()
        
        # Para campos numéricos, tentar converter e fazer busca exata
        try:
            search_num = int(float(search_query))
            search_conditions |= Q(ca=search_num)
        except (ValueError, TypeError):
            pass
        
        # Para campos de texto, usar icontains
        search_conditions |= (
            Q(sigla__icontains=search_query) |
            Q(descricao__icontains=search_query) |
            Q(encarregado_responsavel__icontains=search_query) |
            Q(locais__local__icontains=search_query)
        )
        
        cas_list = cas_list.filter(search_conditions).distinct()
    
    # Filtros por coluna individual
    filter_ca = request.GET.get('filter_ca', '').strip()
    if filter_ca:
        try:
            ca_num = int(float(filter_ca))
            cas_list = cas_list.filter(ca=ca_num)
        except (ValueError, TypeError):
            cas_list = cas_list.filter(ca__icontains=filter_ca)
    
    filter_sigla = request.GET.get('filter_sigla', '').strip()
    if filter_sigla:
        cas_list = cas_list.filter(sigla__icontains=filter_sigla)
    
    filter_descricao = request.GET.get('filter_descricao', '').strip()
    if filter_descricao:
        cas_list = cas_list.filter(descricao__icontains=filter_descricao)
    
    filter_indice = request.GET.get('filter_indice', '').strip()
    if filter_indice:
        try:
            indice_num = int(float(filter_indice))
            cas_list = cas_list.filter(indice=indice_num)
        except (ValueError, TypeError):
            cas_list = cas_list.filter(indice__icontains=filter_indice)
    
    filter_encarregado = request.GET.get('filter_encarregado', '').strip()
    if filter_encarregado:
        cas_list = cas_list.filter(encarregado_responsavel__icontains=filter_encarregado)
    
    filter_local = request.GET.get('filter_local', '').strip()
    if filter_local:
        cas_list = cas_list.filter(locais__local__icontains=filter_local).distinct()
    
    # Ordenar por código CA
    cas_list = cas_list.order_by('ca').distinct()
    
    # Paginação
    paginator = Paginator(cas_list, 50)  # 50 itens por página
    page_number = request.GET.get('page', 1)
    cas = paginator.get_page(page_number)
    
    # Estatísticas
    total_count = CentroAtividade.objects.count()
    siglas_count = CentroAtividade.objects.exclude(sigla__isnull=True).exclude(sigla='').values('sigla').distinct().count()
    encarregados_count = CentroAtividade.objects.exclude(encarregado_responsavel__isnull=True).exclude(encarregado_responsavel='').values('encarregado_responsavel').distinct().count()
    
    context = {
        'page_title': 'Consultar Centros de Atividades',
        'active_page': 'consultar_locais_e_cas',
        'cas': cas,
        'total_count': total_count,
        'siglas_count': siglas_count,
        'encarregados_count': encarregados_count,
        # Preservar filtros no contexto
        'filter_ca': filter_ca,
        'filter_sigla': filter_sigla,
        'filter_descricao': filter_descricao,
        'filter_indice': filter_indice,
        'filter_encarregado': filter_encarregado,
        'filter_local': filter_local,
        'search_query': search_query,
    }
    return render(request, 'consultar/consultar_centros_de_atividades.html', context)


def visualizar_centro_de_atividade(request, ca_id):
    """Visualizar detalhes de um Centro de Atividade específico"""
    from app.models import CentroAtividade
    
    try:
        centro_atividade = CentroAtividade.objects.get(id=ca_id)
    except CentroAtividade.DoesNotExist:
        messages.error(request, 'Centro de Atividade não encontrado.')
        return redirect('consultar_locais_e_cas')
    
    context = {
        'page_title': f'Visualizar CA {centro_atividade.ca}',
        'active_page': 'consultar_locais_e_cas',
        'ca': centro_atividade,
    }
    return render(request, 'visualizar/visualizar_centro_de_atividade.html', context)


def visualizar_local(request, local_id):
    """Visualizar detalhes de um Local do Centro de Atividade específico"""
    from app.models import LocalCentroAtividade, Maquina
    
    try:
        local = LocalCentroAtividade.objects.select_related('centro_atividade').get(id=local_id)
    except LocalCentroAtividade.DoesNotExist:
        messages.error(request, 'Local do Centro de Atividade não encontrado.')
        return redirect('consultar_locais_e_cas')
    
    # Buscar todas as máquinas relacionadas a este local com classificação "MÁQUINAS PRINCIPAL"
    maquinas = Maquina.objects.filter(
        local_centro_atividade=local,
        descr_gerenc__iexact='MÁQUINAS PRINCIPAL'
    ).order_by('cd_maquina')
    
    context = {
        'page_title': f'Visualizar Local {local.local}',
        'active_page': 'consultar_locais_e_cas',
        'local': local,
        'maquinas': maquinas,
    }
    return render(request, 'visualizar/visualizar_local.html', context)


def consultar_locais(request):
    """Consultar/listar Locais do Centro de Atividade cadastrados"""
    from app.models import LocalCentroAtividade
    
    # Buscar todos os locais
    locais_list = LocalCentroAtividade.objects.select_related('centro_atividade').all()
    
    # Filtro de busca
    search_query = request.GET.get('search', '').strip()
    if search_query:
        # Buscar em local, observações, CA e sigla do centro de atividade
        search_conditions = (
            Q(local__icontains=search_query) |
            Q(observacoes__icontains=search_query) |
            Q(centro_atividade__ca__icontains=search_query) |
            Q(centro_atividade__sigla__icontains=search_query) |
            Q(centro_atividade__descricao__icontains=search_query)
        )
        locais_list = locais_list.filter(search_conditions)
    
    # Ordenar por local
    locais_list = locais_list.order_by('local')
    
    # Paginação
    paginator = Paginator(locais_list, 50)  # 50 itens por página
    page_number = request.GET.get('page', 1)
    locais = paginator.get_page(page_number)
    
    # Estatísticas
    total_count = LocalCentroAtividade.objects.count()
    centros_count = LocalCentroAtividade.objects.values('centro_atividade').distinct().count()
    
    context = {
        'page_title': 'Consultar Locais',
        'active_page': 'consultar_locais',
        'locais': locais,
        'total_count': total_count,
        'centros_count': centros_count,
    }
    return render(request, 'consultar/consultar_locais.html', context)


def editar_ca_e_locais(request, ca_id):
    """Editar Centro de Atividade (CA) existente com múltiplos locais"""
    from app.forms import CentroAtividadeForm, LocalCentroAtividadeFormSet
    from app.models import CentroAtividade
    
    try:
        centro_atividade = CentroAtividade.objects.get(id=ca_id)
    except CentroAtividade.DoesNotExist:
        messages.error(request, 'Centro de Atividade não encontrado.')
        return redirect('consultar_locais_e_cas')
    
    if request.method == 'POST':
        form = CentroAtividadeForm(request.POST, instance=centro_atividade)
        formset = LocalCentroAtividadeFormSet(request.POST, instance=centro_atividade)
        
        # Debug: verificar dados recebidos
        print(f"\n{'='*60}")
        print(f"DEBUG - POST recebido para editar CA {centro_atividade.ca}")
        print(f"{'='*60}")
        print(f"POST data keys: {list(request.POST.keys())[:20]}...")  # Primeiros 20
        print(f"Formset prefix: {formset.prefix}")
        total_forms = request.POST.get(f'{formset.prefix}-TOTAL_FORMS', 'N/A')
        print(f"Formset total forms: {total_forms}")
        
        # Listar todos os campos do formset
        print(f"\nCampos do formset recebidos:")
        for key in request.POST.keys():
            if key.startswith(f'{formset.prefix}-'):
                print(f"  {key} = {request.POST[key]}")
        
        if form.is_valid() and formset.is_valid():
            try:
                print(f"\nFormulário e formset são válidos!")
                centro_atividade = form.save()
                print(f"Centro de Atividade salvo: {centro_atividade.ca}")
                
                formset.instance = centro_atividade
                print(f"Processando formset com {len(formset)} formulários...")
                
                # Debug: verificar cada formulário do formset
                print(f"\nDetalhamento dos formulários do formset:")
                for i, form_item in enumerate(formset):
                    if form_item.cleaned_data:
                        print(f"  Form {i}: {form_item.cleaned_data}")
                        # Verificar se é um novo formulário (sem id) ou existente
                        if 'id' in form_item.cleaned_data:
                            if form_item.cleaned_data['id']:
                                print(f"    -> Formulário existente (ID: {form_item.cleaned_data['id']})")
                            else:
                                print(f"    -> NOVO formulário (sem ID)")
                        else:
                            print(f"    -> NOVO formulário (campo id ausente)")
                    elif form_item.errors:
                        print(f"  Form {i} tem erros: {form_item.errors}")
                    else:
                        print(f"  Form {i}: vazio (será ignorado pelo Django)")
                
                saved_instances = formset.save()
                print(f"\nInstâncias salvas: {len(saved_instances)}")
                for instance in saved_instances:
                    print(f"  - Local salvo: '{instance.local}' (ID: {instance.id})")
                
                # Verificar instâncias deletadas
                deleted_count = len([f for f in formset.deleted_forms if f.cleaned_data.get('DELETE', False)])
                if deleted_count > 0:
                    print(f"  - Locais deletados: {deleted_count}")
                
                messages.success(request, f'Centro de Atividade {centro_atividade.ca} atualizado com sucesso!')
                print(f"{'='*60}\n")
                return redirect('consultar_locais_e_cas')
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                print(f"\nERRO ao salvar:")
                print(error_trace)
                print(f"{'='*60}\n")
                messages.error(request, f'Erro ao atualizar Centro de Atividade: {str(e)}')
        else:
            print(f"\nFormulário ou formset inválido!")
            print(f"Form is_valid: {form.is_valid()}")
            if not form.is_valid():
                print(f"Form errors: {form.errors}")
            print(f"Formset is_valid: {formset.is_valid()}")
            if not formset.is_valid():
                print(f"Formset errors: {formset.errors}")
                print(f"Formset non_form_errors: {formset.non_form_errors()}")
            print(f"{'='*60}\n")
            
            handle_form_errors(form, request)
            if formset.errors:
                for error in formset.non_form_errors():
                    messages.error(request, f'Erro no formulário: {error}')
                # Mostrar erros de cada formulário do formset
                for i, form_error in enumerate(formset.errors):
                    if form_error:
                        for field, errors in form_error.items():
                            for error in errors:
                                messages.error(request, f'Erro no local {i+1}, campo {field}: {error}')
    else:
        form = CentroAtividadeForm(instance=centro_atividade)
        formset = LocalCentroAtividadeFormSet(instance=centro_atividade)
    
    context = {
        'page_title': f'Editar CA {centro_atividade.ca}',
        'active_page': 'consultar_locais_e_cas',
        'form': form,
        'formset': formset,
        'centro_atividade': centro_atividade,
    }
    return render(request, 'editar/editar_ca_e_locais.html', context)


def cadastrar_maquina(request):
    """Cadastrar nova máquina"""
    from app.forms import MaquinaForm
    
    if request.method == 'POST':
        form = MaquinaForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                maquina = form.save()
                messages.success(request, f'Máquina {maquina.cd_maquina} cadastrada com sucesso!')
                return redirect('consultar_maquinas')
            except Exception as e:
                messages.error(request, f'Erro ao cadastrar máquina: {str(e)}')
        else:
            handle_form_errors(form, request)
    else:
        form = MaquinaForm()
    
    context = {
        'page_title': 'Cadastrar Máquina',
        'active_page': 'cadastrar_maquina',
        'form': form
    }
    return render(request, 'cadastrar/cadastrar_maquina.html', context)


def analise_maquinas(request):
    """Página de análise de máquinas com gráficos e estatísticas"""
    from app.models import Maquina, OrdemServicoCorretiva
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    from collections import defaultdict
    import json
    
    # Estatísticas básicas
    total_count = Maquina.objects.count()
    setores_count = Maquina.objects.exclude(cd_setormanut__isnull=True).exclude(cd_setormanut='').values('cd_setormanut').distinct().count()
    unidades_count = Maquina.objects.exclude(nome_unid__isnull=True).exclude(nome_unid='').values('nome_unid').distinct().count()
    
    # Máquinas por setor (cd_setormanut) - TODOS os setores
    maquinas_por_setor = Maquina.objects.exclude(
        cd_setormanut__isnull=True
    ).exclude(
        cd_setormanut=''
    ).values('cd_setormanut').annotate(
        total=Count('id')
    ).order_by('-total')  # Removido [:10] para mostrar todos
    
    setores_labels = [str(item['cd_setormanut']) for item in maquinas_por_setor]
    setores_data = [item['total'] for item in maquinas_por_setor]
    
    # Máquinas por unidade (top 10)
    maquinas_por_unidade = Maquina.objects.exclude(
        nome_unid__isnull=True
    ).exclude(
        nome_unid=''
    ).values('nome_unid').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    unidades_labels = [item['nome_unid'][:30] for item in maquinas_por_unidade]
    unidades_data = [item['total'] for item in maquinas_por_unidade]
    
    # Máquinas por mês (últimos 12 meses)
    maquinas_por_mes = defaultdict(int)
    maquinas = Maquina.objects.all().order_by('created_at')
    for maquina in maquinas:
        if maquina.created_at:
            mes_ano = maquina.created_at.strftime('%Y-%m')
            maquinas_por_mes[mes_ano] += 1
    
    # Ordenar por data e pegar últimos 12 meses
    meses_ordenados = sorted(maquinas_por_mes.keys())[-12:]
    meses_labels = [datetime.strptime(m, '%Y-%m').strftime('%b/%Y') for m in meses_ordenados]
    meses_data = [maquinas_por_mes[m] for m in meses_ordenados]
    
    # Distribuição por prioridade
    maquinas_por_prioridade = Maquina.objects.exclude(
        cd_priomaqutv__isnull=True
    ).values('cd_priomaqutv').annotate(
        total=Count('id')
    ).order_by('-cd_priomaqutv')[:10]
    
    prioridades_labels = [f"Prioridade {item['cd_priomaqutv']}" for item in maquinas_por_prioridade]
    prioridades_data = [item['total'] for item in maquinas_por_prioridade]
    
    # Distribuição por grupo
    maquinas_por_grupo = Maquina.objects.exclude(
        cd_grupo__isnull=True
    ).values('cd_grupo').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    grupos_labels = [f"Grupo {item['cd_grupo']}" for item in maquinas_por_grupo]
    grupos_data = [item['total'] for item in maquinas_por_grupo]
    
    # Distribuição por gerência
    maquinas_por_gerencia = Maquina.objects.exclude(
        descr_gerenc__isnull=True
    ).exclude(
        descr_gerenc=''
    ).values('descr_gerenc').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    gerencias_labels = [item['descr_gerenc'][:30] for item in maquinas_por_gerencia]
    gerencias_data = [item['total'] for item in maquinas_por_gerencia]
    
    # Máquinas com fotos
    maquinas_com_foto = Maquina.objects.exclude(foto__isnull=True).exclude(foto='').count()
    percentual_foto = (maquinas_com_foto / total_count * 100) if total_count > 0 else 0
    
    # Máquinas com placa
    maquinas_com_placa = Maquina.objects.exclude(placa_identificacao__isnull=True).exclude(placa_identificacao='').count()
    percentual_placa = (maquinas_com_placa / total_count * 100) if total_count > 0 else 0
    
    # Máquinas recentes (últimas 30 dias)
    data_30_dias_atras = datetime.now() - timedelta(days=30)
    maquinas_recentes = Maquina.objects.filter(created_at__gte=data_30_dias_atras).count()
    
    # Máquinas do mês atual
    mes_atual = datetime.now().replace(day=1)
    maquinas_mes_atual = Maquina.objects.filter(created_at__gte=mes_atual).count()
    
    # Top 10 máquinas com mais ordens de serviço
    top_maquinas_os = OrdemServicoCorretiva.objects.exclude(
        cd_maquina__isnull=True
    ).values('cd_maquina').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    # Buscar descrições das máquinas
    top_maquinas_os_list = []
    for item in top_maquinas_os:
        try:
            maquina = Maquina.objects.get(cd_maquina=item['cd_maquina'])
            top_maquinas_os_list.append({
                'cd_maquina': item['cd_maquina'],
                'descr_maquina': maquina.descr_maquina or 'Sem descrição',
                'total': item['total']
            })
        except Maquina.DoesNotExist:
            top_maquinas_os_list.append({
                'cd_maquina': item['cd_maquina'],
                'descr_maquina': 'Máquina não encontrada',
                'total': item['total']
            })
    
    maquinas_os_labels = [f"{item['cd_maquina']} - {item['descr_maquina'][:40]}" for item in top_maquinas_os_list]
    maquinas_os_data = [item['total'] for item in top_maquinas_os_list]
    
    # Máquinas com patrimônio
    maquinas_com_patrimonio = Maquina.objects.exclude(nro_patrimonio__isnull=True).exclude(nro_patrimonio='').count()
    percentual_patrimonio = (maquinas_com_patrimonio / total_count * 100) if total_count > 0 else 0
    
    # Máquinas "MÁQUINAS PRINCIPAL" agrupadas por cd_setormanut
    maquinas_principais = Maquina.objects.filter(
        descr_gerenc__iexact='MÁQUINAS PRINCIPAL'
    ).exclude(
        cd_setormanut__isnull=True
    ).exclude(
        cd_setormanut=''
    ).order_by('cd_setormanut', 'cd_maquina')
    
    # Agrupar máquinas por setor
    maquinas_por_setor_principal = {}
    for maquina in maquinas_principais:
        setor = str(maquina.cd_setormanut)
        if setor not in maquinas_por_setor_principal:
            maquinas_por_setor_principal[setor] = {
                'cd_setormanut': setor,
                'descr_setormanut': maquina.descr_setormanut or 'Sem descrição',
                'maquinas': []
            }
        maquinas_por_setor_principal[setor]['maquinas'].append({
            'id': maquina.id,
            'cd_maquina': maquina.cd_maquina,
            'descr_maquina': maquina.descr_maquina or 'Sem descrição',
            'nome_unid': maquina.nome_unid or '-',
            'nro_patrimonio': maquina.nro_patrimonio or '-'
        })
    
    # Converter para lista ordenada por cd_setormanut
    maquinas_principais_por_setor = sorted(
        maquinas_por_setor_principal.values(),
        key=lambda x: x['cd_setormanut']
    )
    
    # Buscar Centros de Atividade filtrados por local (INDÚSTRIA ou FRIGORÍFICO)
    from app.models import CentroAtividade
    centros_industria = list(CentroAtividade.objects.filter(
        local__iexact='INDÚSTRIA'
    ).order_by('ca'))
    
    centros_frigorifico = list(CentroAtividade.objects.filter(
        local__iexact='FRIGORÍFICO'
    ).order_by('ca'))
    
    context = {
        'page_title': 'Análise de Máquinas',
        'active_page': 'analise_maquinas',
        'total_count': total_count,
        'setores_count': setores_count,
        'unidades_count': unidades_count,
        'maquinas_recentes': maquinas_recentes,
        'maquinas_mes_atual': maquinas_mes_atual,
        'maquinas_com_foto': maquinas_com_foto,
        'percentual_foto': round(percentual_foto, 1),
        'maquinas_com_placa': maquinas_com_placa,
        'percentual_placa': round(percentual_placa, 1),
        'maquinas_com_patrimonio': maquinas_com_patrimonio,
        'percentual_patrimonio': round(percentual_patrimonio, 1),
        # Dados para gráficos (JSON)
        'setores_labels': json.dumps(setores_labels),
        'setores_data': json.dumps(setores_data),
        'unidades_labels': json.dumps(unidades_labels),
        'unidades_data': json.dumps(unidades_data),
        'meses_labels': json.dumps(meses_labels),
        'meses_data': json.dumps(meses_data),
        'prioridades_labels': json.dumps(prioridades_labels),
        'prioridades_data': json.dumps(prioridades_data),
        'grupos_labels': json.dumps(grupos_labels),
        'grupos_data': json.dumps(grupos_data),
        'gerencias_labels': json.dumps(gerencias_labels),
        'gerencias_data': json.dumps(gerencias_data),
        'maquinas_os_labels': json.dumps(maquinas_os_labels),
        'maquinas_os_data': json.dumps(maquinas_os_data),
        # Dados para tabelas
        'top_maquinas_os': top_maquinas_os_list,
        'maquinas_por_setor': maquinas_por_setor,
        'maquinas_por_unidade': maquinas_por_unidade,
        'maquinas_principais_por_setor': maquinas_principais_por_setor,
        'centros_industria': centros_industria,
        'centros_frigorifico': centros_frigorifico,
    }
    return render(request, 'analise/analise_maquinas.html', context)


def consultar_maquinas(request):
    """Consultar/listar máquinas cadastradas"""
    from app.models import Maquina
    
    # Buscar todas as máquinas
    maquinas_list = Maquina.objects.all()
    
    # Filtro de busca geral
    search_query = request.GET.get('search', '').strip()
    if search_query:
        # Criar lista de condições Q
        search_conditions = Q()
        
        # Para campos numéricos, tentar converter e fazer busca exata
        try:
            search_num = int(float(search_query))
            search_conditions |= Q(cd_maquina=search_num)
        except (ValueError, TypeError):
            pass
        
        # Para campos de texto, usar icontains
        search_conditions |= (
            Q(descr_maquina__icontains=search_query) |
            Q(cd_setormanut__icontains=search_query) |
            Q(descr_setormanut__icontains=search_query) |
            Q(nome_unid__icontains=search_query) |
            Q(nro_patrimonio__icontains=search_query)
        )
        
        maquinas_list = maquinas_list.filter(search_conditions)
    
    # Filtros por coluna individual
    filter_codigo = request.GET.get('filter_codigo', '').strip()
    if filter_codigo:
        try:
            codigo_num = int(float(filter_codigo))
            maquinas_list = maquinas_list.filter(cd_maquina=codigo_num)
        except (ValueError, TypeError):
            maquinas_list = maquinas_list.filter(cd_maquina__icontains=filter_codigo)
    
    filter_descricao = request.GET.get('filter_descricao', '').strip()
    if filter_descricao:
        maquinas_list = maquinas_list.filter(descr_maquina__icontains=filter_descricao)
    
    filter_setor = request.GET.get('filter_setor', '').strip()
    if filter_setor:
        # Se for um valor exato (da lista de opções), usar busca exata
        # Caso contrário, usar busca parcial
        maquinas_list = maquinas_list.filter(descr_setormanut=filter_setor)
    
    filter_unidade = request.GET.get('filter_unidade', '').strip()
    if filter_unidade:
        maquinas_list = maquinas_list.filter(nome_unid__icontains=filter_unidade)
    
    filter_patrimonio = request.GET.get('filter_patrimonio', '').strip()
    if filter_patrimonio:
        maquinas_list = maquinas_list.filter(nro_patrimonio__icontains=filter_patrimonio)
    
    filter_prioridade = request.GET.get('filter_prioridade', '').strip()
    if filter_prioridade:
        try:
            prioridade_num = int(float(filter_prioridade))
            maquinas_list = maquinas_list.filter(cd_priomaqutv=prioridade_num)
        except (ValueError, TypeError):
            maquinas_list = maquinas_list.filter(cd_priomaqutv__icontains=filter_prioridade)
    
    filter_gerenc = request.GET.get('filter_gerenc', '').strip()
    if filter_gerenc:
        maquinas_list = maquinas_list.filter(descr_gerenc=filter_gerenc)
    
    # Ordenar por código da máquina
    maquinas_list = maquinas_list.order_by('cd_maquina')
    
    # Paginação
    paginator = Paginator(maquinas_list, 100)  # 100 itens por página
    page_number = request.GET.get('page', 1)
    maquinas = paginator.get_page(page_number)
    
    # Estatísticas
    total_count = Maquina.objects.count()
    setores_count = Maquina.objects.exclude(descr_setormanut__isnull=True).exclude(descr_setormanut='').values('descr_setormanut').distinct().count()
    unidades_count = Maquina.objects.exclude(nome_unid__isnull=True).exclude(nome_unid='').values('nome_unid').distinct().count()
    
    # Contar máquinas com descr_gerenc = "MÁQUINAS PRINCIPAL" ou "MÁQUINA PRINCIPAL"
    maquinas_principais_count = Maquina.objects.filter(
        descr_gerenc__iexact='MÁQUINAS PRINCIPAL'
    ).count()
    
    # Obter valores distintos de descr_gerenc para o select
    gerenc_choices = Maquina.objects.exclude(
        descr_gerenc__isnull=True
    ).exclude(
        descr_gerenc=''
    ).values_list('descr_gerenc', flat=True).distinct().order_by('descr_gerenc')
    
    # Obter valores distintos de descr_setormanut para o select
    setor_choices = Maquina.objects.exclude(
        descr_setormanut__isnull=True
    ).exclude(
        descr_setormanut=''
    ).values_list('descr_setormanut', flat=True).distinct().order_by('descr_setormanut')
    
    context = {
        'page_title': 'Consultar Máquinas',
        'active_page': 'consultar_maquinas',
        'maquinas': maquinas,
        'total_count': total_count,
        'setores_count': setores_count,
        'unidades_count': unidades_count,
        'maquinas_principais_count': maquinas_principais_count,
        'gerenc_choices': gerenc_choices,
        'setor_choices': setor_choices,
        # Preservar filtros no contexto
        'filter_codigo': filter_codigo,
        'filter_descricao': filter_descricao,
        'filter_setor': filter_setor,
        'filter_unidade': filter_unidade,
        'filter_patrimonio': filter_patrimonio,
        'filter_prioridade': filter_prioridade,
        'filter_gerenc': filter_gerenc,
        'search_query': search_query,
    }
    return render(request, 'consultar/consultar_maquinas.html', context)


def consultar_manutencoes_preventivas(request):
    """Consultar/listar planos de manutenção preventiva"""
    from app.models import PlanoPreventiva
    
    # Buscar todos os planos preventiva
    planos_list = PlanoPreventiva.objects.all().select_related('maquina', 'roteiro_preventiva')
    
    # Filtro de busca geral
    search_query = request.GET.get('search', '').strip()
    if search_query:
        # Criar lista de condições Q
        search_conditions = Q()
        
        # Para campos numéricos, tentar converter e fazer busca exata
        try:
            search_num = int(float(search_query))
            search_conditions |= Q(cd_maquina=search_num) | Q(numero_plano=search_num) | Q(sequencia_manutencao=search_num) | Q(sequencia_tarefa=search_num)
        except (ValueError, TypeError):
            pass
        
        # Para campos de texto, usar icontains
        search_conditions |= (
            Q(descr_maquina__icontains=search_query) |
            Q(descr_tarefa__icontains=search_query) |
            Q(nome_funcionario__icontains=search_query) |
            Q(cd_funcionario__icontains=search_query) |
            Q(cd_setor__icontains=search_query) |
            Q(descr_setor__icontains=search_query) |
            Q(nome_unid__icontains=search_query) |
            Q(descr_plano__icontains=search_query)
        )
        
        planos_list = planos_list.filter(search_conditions)
    
    # Filtros por coluna individual
    filter_maquina = request.GET.get('filter_maquina', '').strip()
    if filter_maquina:
        try:
            maquina_num = int(float(filter_maquina))
            planos_list = planos_list.filter(cd_maquina=maquina_num)
        except (ValueError, TypeError):
            planos_list = planos_list.filter(
                Q(cd_maquina__icontains=filter_maquina) |
                Q(descr_maquina__icontains=filter_maquina)
            )
    
    filter_plano = request.GET.get('filter_plano', '').strip()
    if filter_plano:
        try:
            plano_num = int(float(filter_plano))
            planos_list = planos_list.filter(numero_plano=plano_num)
        except (ValueError, TypeError):
            planos_list = planos_list.filter(
                Q(numero_plano__icontains=filter_plano) |
                Q(descr_plano__icontains=filter_plano)
            )
    
    filter_seq_manutencao = request.GET.get('filter_seq_manutencao', '').strip()
    if filter_seq_manutencao:
        try:
            seq_num = int(float(filter_seq_manutencao))
            planos_list = planos_list.filter(sequencia_manutencao=seq_num)
        except (ValueError, TypeError):
            planos_list = planos_list.filter(sequencia_manutencao__icontains=filter_seq_manutencao)
    
    filter_data = request.GET.get('filter_data', '').strip()
    if filter_data:
        planos_list = planos_list.filter(dt_execucao__icontains=filter_data)
    
    filter_periodo = request.GET.get('filter_periodo', '').strip()
    if filter_periodo:
        try:
            periodo_num = int(float(filter_periodo))
            planos_list = planos_list.filter(quantidade_periodo=periodo_num)
        except (ValueError, TypeError):
            planos_list = planos_list.filter(quantidade_periodo__icontains=filter_periodo)
    
    filter_seq_tarefa = request.GET.get('filter_seq_tarefa', '').strip()
    if filter_seq_tarefa:
        try:
            seq_tarefa_num = int(float(filter_seq_tarefa))
            planos_list = planos_list.filter(sequencia_tarefa=seq_tarefa_num)
        except (ValueError, TypeError):
            planos_list = planos_list.filter(sequencia_tarefa__icontains=filter_seq_tarefa)
    
    filter_tarefa = request.GET.get('filter_tarefa', '').strip()
    if filter_tarefa:
        planos_list = planos_list.filter(descr_tarefa__icontains=filter_tarefa)
    
    filter_descr_seqplamanu = request.GET.get('filter_descr_seqplamanu', '').strip()
    if filter_descr_seqplamanu:
        planos_list = planos_list.filter(descr_seqplamanu__icontains=filter_descr_seqplamanu)
    
    filter_funcionario = request.GET.get('filter_funcionario', '').strip()
    if filter_funcionario:
        planos_list = planos_list.filter(
            Q(nome_funcionario__icontains=filter_funcionario) |
            Q(cd_funcionario__icontains=filter_funcionario)
        )
    
    filter_setor = request.GET.get('filter_setor', '').strip()
    if filter_setor:
        planos_list = planos_list.filter(
            Q(cd_setor__icontains=filter_setor) |
            Q(descr_setor__icontains=filter_setor)
        )
    
    filter_unidade = request.GET.get('filter_unidade', '').strip()
    if filter_unidade:
        try:
            unidade_num = int(float(filter_unidade))
            planos_list = planos_list.filter(cd_unid=unidade_num)
        except (ValueError, TypeError):
            planos_list = planos_list.filter(
                Q(nome_unid__icontains=filter_unidade)
            )
    
    # Ordenar por máquina, plano, sequência manutenção e sequência tarefa
    planos_list = planos_list.order_by('cd_maquina', 'numero_plano', 'sequencia_manutencao', 'sequencia_tarefa')
    
    # Paginação
    paginator = Paginator(planos_list, 100)  # 100 itens por página
    page_number = request.GET.get('page', 1)
    planos = paginator.get_page(page_number)
    
    # Estatísticas
    total_count = PlanoPreventiva.objects.count()
    maquinas_count = PlanoPreventiva.objects.exclude(cd_maquina__isnull=True).values('cd_maquina').distinct().count()
    setores_count = PlanoPreventiva.objects.exclude(cd_setor__isnull=True).exclude(cd_setor='').values('cd_setor').distinct().count()
    
    context = {
        'page_title': 'Consultar Manutenções Preventivas',
        'active_page': 'consultar_manutencoes_preventivas',
        'planos': planos,
        'total_count': total_count,
        'maquinas_count': maquinas_count,
        'setores_count': setores_count,
        # Preservar filtros no contexto
        'filter_maquina': filter_maquina,
        'filter_plano': filter_plano,
        'filter_seq_manutencao': filter_seq_manutencao,
        'filter_data': filter_data,
        'filter_periodo': filter_periodo,
        'filter_seq_tarefa': filter_seq_tarefa,
        'filter_tarefa': filter_tarefa,
        'filter_descr_seqplamanu': filter_descr_seqplamanu,
        'filter_funcionario': filter_funcionario,
        'filter_setor': filter_setor,
        'filter_unidade': filter_unidade,
        'search_query': search_query,
    }
    return render(request, 'consultar/consultar_manutencoes_preventivas.html', context)


def consultar_roteiro_preventiva(request):
    """Consultar/listar roteiros de manutenção preventiva"""
    from app.models import RoteiroPreventiva
    
    # Buscar todos os roteiros preventiva
    roteiros_list = RoteiroPreventiva.objects.all().select_related('maquina')
    
    # Filtro de busca geral
    search_query = request.GET.get('search', '').strip()
    if search_query:
        # Criar lista de condições Q
        search_conditions = Q()
        
        # Para campos numéricos, tentar converter e fazer busca exata
        try:
            search_num = int(float(search_query))
            search_conditions |= Q(cd_maquina=search_num) | Q(cd_planmanut=search_num) | Q(seq_seqplamanu=search_num) | Q(cd_tarefamanu=search_num) | Q(cd_ordemserv=search_num)
        except (ValueError, TypeError):
            pass
        
        # Para campos de texto, usar icontains
        search_conditions |= (
            Q(descr_maquina__icontains=search_query) |
            Q(descr_tarefamanu__icontains=search_query) |
            Q(nome_funciomanu__icontains=search_query) |
            Q(cd_funciomanu__icontains=search_query) |
            Q(cd_setormanut__icontains=search_query) |
            Q(descr_setormanut__icontains=search_query) |
            Q(nome_unid__icontains=search_query) |
            Q(descr_planmanut__icontains=search_query) |
            Q(descr_item__icontains=search_query)
        )
        
        roteiros_list = roteiros_list.filter(search_conditions)
    
    # Filtros por coluna individual
    filter_maquina = request.GET.get('filter_maquina', '').strip()
    if filter_maquina:
        try:
            maquina_num = int(float(filter_maquina))
            roteiros_list = roteiros_list.filter(cd_maquina=maquina_num)
        except (ValueError, TypeError):
            roteiros_list = roteiros_list.filter(
                Q(cd_maquina__icontains=filter_maquina) |
                Q(descr_maquina__icontains=filter_maquina)
            )
    
    filter_planmanut = request.GET.get('filter_planmanut', '').strip()
    if filter_planmanut:
        try:
            planmanut_num = int(float(filter_planmanut))
            roteiros_list = roteiros_list.filter(cd_planmanut=planmanut_num)
        except (ValueError, TypeError):
            roteiros_list = roteiros_list.filter(
                Q(cd_planmanut__icontains=filter_planmanut) |
                Q(descr_planmanut__icontains=filter_planmanut)
            )
    
    filter_seq_plamanu = request.GET.get('filter_seq_plamanu', '').strip()
    if filter_seq_plamanu:
        try:
            seq_num = int(float(filter_seq_plamanu))
            roteiros_list = roteiros_list.filter(seq_seqplamanu=seq_num)
        except (ValueError, TypeError):
            roteiros_list = roteiros_list.filter(seq_seqplamanu__icontains=filter_seq_plamanu)
    
    filter_tarefamanu = request.GET.get('filter_tarefamanu', '').strip()
    if filter_tarefamanu:
        try:
            tarefa_num = int(float(filter_tarefamanu))
            roteiros_list = roteiros_list.filter(cd_tarefamanu=tarefa_num)
        except (ValueError, TypeError):
            roteiros_list = roteiros_list.filter(
                Q(cd_tarefamanu__icontains=filter_tarefamanu) |
                Q(descr_tarefamanu__icontains=filter_tarefamanu)
            )
    
    filter_ordemserv = request.GET.get('filter_ordemserv', '').strip()
    if filter_ordemserv:
        try:
            ordemserv_num = int(float(filter_ordemserv))
            roteiros_list = roteiros_list.filter(cd_ordemserv=ordemserv_num)
        except (ValueError, TypeError):
            roteiros_list = roteiros_list.filter(cd_ordemserv__icontains=filter_ordemserv)
    
    filter_data_exec = request.GET.get('filter_data_exec', '').strip()
    if filter_data_exec:
        roteiros_list = roteiros_list.filter(dt_primexec__icontains=filter_data_exec)
    
    filter_periodo = request.GET.get('filter_periodo', '').strip()
    if filter_periodo:
        try:
            periodo_num = int(float(filter_periodo))
            roteiros_list = roteiros_list.filter(qtde_periodo=periodo_num)
        except (ValueError, TypeError):
            roteiros_list = roteiros_list.filter(qtde_periodo__icontains=filter_periodo)
    
    filter_funcionario = request.GET.get('filter_funcionario', '').strip()
    if filter_funcionario:
        roteiros_list = roteiros_list.filter(
            Q(nome_funciomanu__icontains=filter_funcionario) |
            Q(cd_funciomanu__icontains=filter_funcionario)
        )
    
    filter_setor = request.GET.get('filter_setor', '').strip()
    if filter_setor:
        roteiros_list = roteiros_list.filter(
            Q(cd_setormanut__icontains=filter_setor) |
            Q(descr_setormanut__icontains=filter_setor)
        )
    
    filter_unidade = request.GET.get('filter_unidade', '').strip()
    if filter_unidade:
        try:
            unidade_num = int(float(filter_unidade))
            roteiros_list = roteiros_list.filter(cd_unid=unidade_num)
        except (ValueError, TypeError):
            roteiros_list = roteiros_list.filter(
                Q(nome_unid__icontains=filter_unidade)
            )
    
    # Ordenar por máquina, plano, sequência e tarefa
    roteiros_list = roteiros_list.order_by('cd_maquina', 'cd_planmanut', 'seq_seqplamanu', 'cd_tarefamanu')
    
    # Paginação
    paginator = Paginator(roteiros_list, 100)  # 100 itens por página
    page_number = request.GET.get('page', 1)
    roteiros = paginator.get_page(page_number)
    
    # Estatísticas
    total_count = RoteiroPreventiva.objects.count()
    maquinas_count = RoteiroPreventiva.objects.exclude(cd_maquina__isnull=True).values('cd_maquina').distinct().count()
    setores_count = RoteiroPreventiva.objects.exclude(cd_setormanut__isnull=True).exclude(cd_setormanut='').values('cd_setormanut').distinct().count()
    planos_count = RoteiroPreventiva.objects.exclude(cd_planmanut__isnull=True).values('cd_planmanut').distinct().count()
    
    context = {
        'page_title': 'Consultar Roteiros Preventiva',
        'active_page': 'consultar_roteiro_preventiva',
        'roteiros': roteiros,
        'total_count': total_count,
        'maquinas_count': maquinas_count,
        'setores_count': setores_count,
        'planos_count': planos_count,
        # Preservar filtros no contexto
        'filter_maquina': filter_maquina,
        'filter_planmanut': filter_planmanut,
        'filter_seq_plamanu': filter_seq_plamanu,
        'filter_tarefamanu': filter_tarefamanu,
        'filter_ordemserv': filter_ordemserv,
        'filter_data_exec': filter_data_exec,
        'filter_periodo': filter_periodo,
        'filter_funcionario': filter_funcionario,
        'filter_setor': filter_setor,
        'filter_unidade': filter_unidade,
        'search_query': search_query,
    }
    return render(request, 'consultar/consultar_roteiro_preventiva.html', context)


def visualizar_roteiro_preventiva(request, roteiro_id):
    """Visualizar detalhes de um roteiro de manutenção preventiva específico"""
    from app.models import RoteiroPreventiva
    
    try:
        roteiro = RoteiroPreventiva.objects.select_related('maquina').get(id=roteiro_id)
    except RoteiroPreventiva.DoesNotExist:
        messages.error(request, 'Roteiro de manutenção preventiva não encontrado.')
        return redirect('consultar_roteiro_preventiva')
    
    context = {
        'page_title': f'Visualizar Roteiro Preventiva - Máquina {roteiro.cd_maquina}',
        'active_page': 'consultar_roteiro_preventiva',
        'roteiro': roteiro,
    }
    return render(request, 'visualizar/visualizar_roteiro_preventiva.html', context)


def visualizar_analise_plano_roteiro(request, plano_id, roteiro_id):
    """Visualizar análise detalhada da relação entre um PlanoPreventiva e um RoteiroPreventiva"""
    from app.models import PlanoPreventiva, RoteiroPreventiva
    
    try:
        plano = PlanoPreventiva.objects.select_related('maquina', 'roteiro_preventiva').get(id=plano_id)
    except PlanoPreventiva.DoesNotExist:
        messages.error(request, 'Plano de manutenção preventiva não encontrado.')
        return redirect('analise_roteiro_plano_preventiva')
    
    try:
        roteiro = RoteiroPreventiva.objects.select_related('maquina').get(id=roteiro_id)
    except RoteiroPreventiva.DoesNotExist:
        messages.error(request, 'Roteiro de manutenção preventiva não encontrado.')
        return redirect('analise_roteiro_plano_preventiva')
    
    # Calcular match score e campos que correspondem
    match_score, campos_match = _match_plano_roteiro(plano, roteiro)
    
    # Verificar se já está vinculado
    ja_vinculado = plano.roteiro_preventiva_id == roteiro.id
    
    # Preparar dados comparativos
    comparacao = {
        'cd_maquina': {
            'plano': plano.cd_maquina,
            'roteiro': roteiro.cd_maquina,
            'match': plano.cd_maquina == roteiro.cd_maquina if plano.cd_maquina and roteiro.cd_maquina else False
        },
        'cd_funcionario': {
            'plano': plano.cd_funcionario,
            'roteiro': roteiro.cd_funciomanu,
            'match': str(plano.cd_funcionario or '').strip().upper() == str(roteiro.cd_funciomanu or '').strip().upper() if plano.cd_funcionario and roteiro.cd_funciomanu else False
        },
        'nome_funcionario': {
            'plano': plano.nome_funcionario,
            'roteiro': roteiro.nome_funciomanu,
            'match': str(plano.nome_funcionario or '').strip().upper() == str(roteiro.nome_funciomanu or '').strip().upper() if plano.nome_funcionario and roteiro.nome_funciomanu else False
        },
        'cd_atividade': {
            'plano': plano.cd_atividade,
            'roteiro': roteiro.cd_tpcentativ,
            'match': plano.cd_atividade == roteiro.cd_tpcentativ if plano.cd_atividade and roteiro.cd_tpcentativ else False
        },
        'numero_plano': {
            'plano': plano.numero_plano,
            'roteiro': roteiro.cd_planmanut,
            'match': plano.numero_plano == roteiro.cd_planmanut if plano.numero_plano and roteiro.cd_planmanut else False
        },
        'sequencia_manutencao': {
            'plano': plano.sequencia_manutencao,
            'roteiro': roteiro.seq_seqplamanu,
            'match': plano.sequencia_manutencao == roteiro.seq_seqplamanu if plano.sequencia_manutencao and roteiro.seq_seqplamanu else False
        },
        'sequencia_tarefa': {
            'plano': plano.sequencia_tarefa,
            'roteiro': roteiro.cd_tarefamanu,
            'match': plano.sequencia_tarefa == roteiro.cd_tarefamanu if plano.sequencia_tarefa and roteiro.cd_tarefamanu else False
        },
    }
    
    context = {
        'page_title': f'Análise: Plano {plano.numero_plano} ↔ Roteiro {roteiro.cd_planmanut}',
        'active_page': 'analise_roteiro_plano_preventiva',
        'plano': plano,
        'roteiro': roteiro,
        'match_score': match_score,
        'campos_match': campos_match,
        'ja_vinculado': ja_vinculado,
        'comparacao': comparacao,
    }
    return render(request, 'visualizar/visualizar_analise_plano_roteiro.html', context)


def visualizar_manutencao_preventiva(request, plano_id):
    """Visualizar detalhes de um plano de manutenção preventiva específico"""
    from app.models import PlanoPreventiva, PlanoPreventivaDocumento
    
    try:
        plano = PlanoPreventiva.objects.select_related('maquina', 'roteiro_preventiva').get(id=plano_id)
    except PlanoPreventiva.DoesNotExist:
        messages.error(request, 'Plano de manutenção preventiva não encontrado.')
        return redirect('consultar_manutencoes_preventivas')
    
    # Buscar documentos relacionados
    documentos = PlanoPreventivaDocumento.objects.filter(plano_preventiva=plano).order_by('-created_at')
    
    context = {
        'page_title': f'Visualizar Manutenção Preventiva - Plano {plano.numero_plano}',
        'active_page': 'consultar_manutencoes_preventivas',
        'plano': plano,
        'documentos': documentos,
    }
    return render(request, 'visualizar/visualizar_manutencao_preventiva.html', context)


def adicionar_documento_plano_preventiva(request, plano_id):
    """Adicionar documento a um plano preventiva"""
    from app.models import PlanoPreventiva, PlanoPreventivaDocumento
    from app.forms import PlanoPreventivaDocumentoForm
    import os
    
    try:
        plano = PlanoPreventiva.objects.get(id=plano_id)
    except PlanoPreventiva.DoesNotExist:
        messages.error(request, 'Plano preventiva não encontrado.')
        return redirect('consultar_manutencoes_preventivas')
    
    if request.method == 'POST':
        print(f"DEBUG - Método POST recebido")
        print(f"DEBUG - request.FILES: {list(request.FILES.keys())}")
        print(f"DEBUG - request.POST: {dict(request.POST)}")
        
        # Verificar se arquivo foi enviado
        if 'arquivo' not in request.FILES:
            print("DEBUG - Arquivo não encontrado em request.FILES")
            messages.error(request, 'Por favor, selecione um arquivo para upload.')
            return redirect('visualizar_manutencao_preventiva', plano_id=plano_id)
        
        arquivo = request.FILES['arquivo']
        comentario = request.POST.get('comentario', '').strip()
        
        print(f"DEBUG - Arquivo recebido: {arquivo.name}, Tamanho: {arquivo.size}, Content-Type: {arquivo.content_type}")
        print(f"DEBUG - Comentário: {comentario}")
        print(f"DEBUG - Plano ID: {plano.id}, Plano Preventiva: {plano}")
        
        # Criar documento diretamente
        try:
            documento = PlanoPreventivaDocumento(
                plano_preventiva=plano,
                arquivo=arquivo,
                comentario=comentario if comentario else None
            )
            documento.full_clean()  # Validar antes de salvar
            documento.save()
            print(f"DEBUG - Documento criado com sucesso! ID: {documento.id}, Arquivo: {documento.arquivo.name}")
            messages.success(request, 'Documento adicionado com sucesso!')
        except Exception as e:
            print(f"DEBUG - Erro ao criar documento: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Erro ao adicionar documento: {str(e)}')
    else:
        print(f"DEBUG - Método não é POST: {request.method}")
        messages.error(request, 'Método não permitido.')
    
    return redirect('visualizar_manutencao_preventiva', plano_id=plano_id)


def remover_documento_plano_preventiva(request, plano_id, documento_id):
    """Remover documento de um plano preventiva"""
    from app.models import PlanoPreventiva, PlanoPreventivaDocumento
    import os
    
    try:
        plano = PlanoPreventiva.objects.get(id=plano_id)
    except PlanoPreventiva.DoesNotExist:
        messages.error(request, 'Plano preventiva não encontrado.')
        return redirect('consultar_manutencoes_preventivas')
    
    try:
        documento = PlanoPreventivaDocumento.objects.get(id=documento_id, plano_preventiva=plano)
        # Deletar arquivo físico se existir
        if documento.arquivo:
            if os.path.isfile(documento.arquivo.path):
                os.remove(documento.arquivo.path)
        documento.delete()
        messages.success(request, 'Documento removido com sucesso!')
    except PlanoPreventivaDocumento.DoesNotExist:
        messages.error(request, 'Documento não encontrado.')
    
    return redirect('visualizar_manutencao_preventiva', plano_id=plano_id)


def visualizar_maquina(request, maquina_id):
    """Visualizar detalhes de uma máquina específica"""
    from app.models import Maquina, ItemEstoque, MaquinaPeca, MaquinaPrimariaSecundaria, PlanoPreventiva
    
    try:
        maquina = Maquina.objects.get(id=maquina_id)
    except Maquina.DoesNotExist:
        messages.error(request, 'Máquina não encontrada.')
        return redirect('consultar_maquinas')
    
    # Buscar peças relacionadas a esta máquina
    pecas_relacionadas = MaquinaPeca.objects.filter(maquina=maquina).select_related('item_estoque').order_by('-created_at')
    
    # Buscar todos os itens de estoque para seleção (excluindo os já relacionados)
    itens_estoque_ids = pecas_relacionadas.values_list('item_estoque_id', flat=True)
    itens_disponiveis = ItemEstoque.objects.exclude(id__in=itens_estoque_ids).order_by('codigo_item')[:100]  # Limitar a 100 para performance
    
    # Buscar relacionamentos onde esta máquina é primária
    relacionamentos_como_primaria = MaquinaPrimariaSecundaria.objects.filter(
        maquina_primaria=maquina
    ).select_related('maquina_secundaria').order_by('maquina_secundaria__cd_maquina')
    
    # Buscar relacionamentos onde esta máquina é secundária
    relacionamentos_como_secundaria = MaquinaPrimariaSecundaria.objects.filter(
        maquina_secundaria=maquina
    ).select_related('maquina_primaria').order_by('maquina_primaria__cd_maquina')
    
    # Buscar planos preventiva relacionados a esta máquina
    # Primeiro pelo relacionamento direto, depois pelo código da máquina
    planos_preventiva = PlanoPreventiva.objects.filter(
        Q(maquina=maquina) | Q(cd_maquina=maquina.cd_maquina)
    ).order_by('numero_plano', 'sequencia_manutencao', 'sequencia_tarefa')
    
    context = {
        'page_title': f'Visualizar Máquina {maquina.cd_maquina}',
        'active_page': 'consultar_maquinas',
        'maquina': maquina,
        'pecas_relacionadas': pecas_relacionadas,
        'itens_disponiveis': itens_disponiveis,
        'relacionamentos_como_primaria': relacionamentos_como_primaria,
        'relacionamentos_como_secundaria': relacionamentos_como_secundaria,
        'planos_preventiva': planos_preventiva,
    }
    return render(request, 'visualizar/visualizar_maquina.html', context)


def editar_maquina(request, maquina_id):
    """Editar uma máquina existente"""
    from app.forms import MaquinaForm
    from app.models import Maquina
    
    try:
        maquina = Maquina.objects.get(id=maquina_id)
    except Maquina.DoesNotExist:
        messages.error(request, 'Máquina não encontrada.')
        return redirect('consultar_maquinas')
    
    if request.method == 'POST':
        print(f"DEBUG - POST recebido para editar máquina {maquina_id}")
        print(f"DEBUG - request.FILES: {request.FILES}")
        print(f"DEBUG - 'foto' in request.FILES: {'foto' in request.FILES}")
        if 'foto' in request.FILES:
            print(f"DEBUG - Arquivo recebido: {request.FILES['foto'].name}, Tamanho: {request.FILES['foto'].size}")
        print(f"DEBUG - request.POST: {request.POST}")
        
        form = MaquinaForm(request.POST, request.FILES, instance=maquina)
        print(f"DEBUG - Form criado. is_valid(): {form.is_valid()}")
        
        if form.is_valid():
            try:
                print(f"DEBUG - Antes de salvar. Foto atual: {maquina.foto}")
                maquina = form.save()
                print(f"DEBUG - Máquina salva com sucesso. Foto: {maquina.foto}")
                print(f"DEBUG - Foto URL: {maquina.foto.url if maquina.foto else 'N/A'}")
                messages.success(request, f'Máquina {maquina.cd_maquina} atualizada com sucesso!')
                return redirect('visualizar_maquina', maquina_id=maquina.id)
            except Exception as e:
                print(f"DEBUG - Erro ao salvar: {str(e)}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'Erro ao atualizar máquina: {str(e)}')
        else:
            print(f"DEBUG - Form inválido. Erros: {form.errors}")
            for field, errors in form.errors.items():
                print(f"DEBUG - Campo {field}: {errors}")
            handle_form_errors(form, request)
    else:
        form = MaquinaForm(instance=maquina)
    
    context = {
        'page_title': f'Editar Máquina {maquina.cd_maquina}',
        'active_page': 'consultar_maquinas',
        'form': form,
        'maquina': maquina,
    }
    return render(request, 'editar/editar_maquina.html', context)


def filtrar_locais_por_setormanut(request):
    """View AJAX para filtrar LocalCentroAtividade baseado no cd_setormanut"""
    from app.models import CentroAtividade, LocalCentroAtividade
    
    cd_setormanut = request.GET.get('cd_setormanut', '')
    
    if not cd_setormanut:
        return JsonResponse({'locais': []})
    
    try:
        # Tentar converter cd_setormanut para inteiro para comparar com ca
        if cd_setormanut.isdigit():
            ca_value = int(cd_setormanut)
            centros = CentroAtividade.objects.filter(ca=ca_value)
            if centros.exists():
                locais = LocalCentroAtividade.objects.filter(
                    centro_atividade__in=centros
                ).order_by('local')
                
                locais_data = [
                    {
                        'id': local.id,
                        'local': local.local,
                        'centro_atividade': str(local.centro_atividade),
                        'observacoes': local.observacoes or ''
                    }
                    for local in locais
                ]
                return JsonResponse({'locais': locais_data})
            else:
                return JsonResponse({'locais': []})
        else:
            # Se não é numérico, retornar vazio ou todos (dependendo da lógica de negócio)
            return JsonResponse({'locais': []})
    except (ValueError, AttributeError) as e:
        return JsonResponse({'error': str(e), 'locais': []})


def cadastrar_corretiva_outros(request):
    """Cadastrar nova ordem corretiva/outros"""
    from app.forms import OrdemServicoCorretivaForm
    
    if request.method == 'POST':
        form = OrdemServicoCorretivaForm(request.POST)
        if form.is_valid():
            try:
                ordem = form.save()
                messages.success(request, f'Ordem de serviço {ordem.cd_ordemserv} cadastrada com sucesso!')
                return redirect('consultar_corretivas_outros')
            except Exception as e:
                messages.error(request, f'Erro ao cadastrar ordem: {str(e)}')
        else:
            handle_form_errors(form, request)
    else:
        form = OrdemServicoCorretivaForm()
    
    context = {
        'page_title': 'Cadastrar Ordem Corretiva/Outros',
        'active_page': 'cadastrar_corretiva_outros',
        'form': form
    }
    return render(request, 'cadastrar/cadastrar_corretiva_outros.html', context)


def consultar_corretivas_outros(request):
    """Consultar/listar ordens corretivas cadastradas com filtros avançados"""
    from app.models import OrdemServicoCorretiva
    from datetime import datetime
    
    # Buscar todas as ordens
    ordens_list = OrdemServicoCorretiva.objects.all()
    
    # Filtro de busca geral (texto)
    search_query = request.GET.get('search', '').strip()
    if search_query:
        # Criar lista de condições Q
        search_conditions = Q()
        
        # Para campos numéricos, tentar converter e fazer busca exata
        try:
            search_num = int(float(search_query))
            search_conditions |= Q(cd_ordemserv=search_num)
            search_conditions |= Q(cd_maquina=search_num)
        except (ValueError, TypeError):
            pass
        
        # Para campos de texto, usar icontains
        search_conditions |= (
            Q(descr_maquina__icontains=search_query) |
            Q(cd_setormanut__icontains=search_query) |
            Q(descr_setormanut__icontains=search_query) |
            Q(nm_func_solic_os__icontains=search_query) |
            Q(nm_func_exec__icontains=search_query) |
            Q(descr_queixa__icontains=search_query) |
            Q(exec_tarefas__icontains=search_query)
        )
        
        ordens_list = ordens_list.filter(search_conditions)
    
    # Filtros específicos
    # Filtro por Setor de Manutenção
    filtro_setor = request.GET.get('filtro_setor', '')
    if filtro_setor:
        ordens_list = ordens_list.filter(descr_setormanut__icontains=filtro_setor)
    
    # Filtro por Unidade
    filtro_unidade = request.GET.get('filtro_unidade', '')
    if filtro_unidade:
        ordens_list = ordens_list.filter(nome_unid__icontains=filtro_unidade)
    
    # Filtro por Tipo de Ordem de Serviço
    filtro_tipo_os = request.GET.get('filtro_tipo_os', '')
    if filtro_tipo_os:
        ordens_list = ordens_list.filter(descr_tpordservtv__icontains=filtro_tipo_os)
    
    # Filtro por Situação da Ordem
    filtro_situacao = request.GET.get('filtro_situacao', '')
    if filtro_situacao:
        ordens_list = ordens_list.filter(descr_sitordsetv__icontains=filtro_situacao)
    
    # Filtro por Funcionário Solicitante
    filtro_solicitante = request.GET.get('filtro_solicitante', '')
    if filtro_solicitante:
        ordens_list = ordens_list.filter(nm_func_solic_os__icontains=filtro_solicitante)
    
    # Filtro por Funcionário Executor
    filtro_executor = request.GET.get('filtro_executor', '')
    if filtro_executor:
        ordens_list = ordens_list.filter(
            Q(nm_func_exec__icontains=filtro_executor) |
            Q(nm_func_exec_os__icontains=filtro_executor)
        )
    
    # Filtro por Código da Máquina
    filtro_maquina = request.GET.get('filtro_maquina', '')
    if filtro_maquina:
        ordens_list = ordens_list.filter(cd_maquina__icontains=filtro_maquina)
    
    # Filtro por Data de Entrada (período)
    data_entrada_inicio = request.GET.get('data_entrada_inicio', '')
    data_entrada_fim = request.GET.get('data_entrada_fim', '')
    if data_entrada_inicio:
        try:
            data_inicio = datetime.strptime(data_entrada_inicio, '%Y-%m-%d')
            ordens_list = ordens_list.filter(created_at__gte=data_inicio)
        except ValueError:
            pass
    if data_entrada_fim:
        try:
            data_fim = datetime.strptime(data_entrada_fim, '%Y-%m-%d')
            # Adicionar 1 dia para incluir o dia final
            from datetime import timedelta
            data_fim = data_fim + timedelta(days=1)
            ordens_list = ordens_list.filter(created_at__lte=data_fim)
        except ValueError:
            pass
    
    # Filtro por Status da Ordem (Abertas/Fechadas)
    filtro_ordens_abertas = request.GET.get('filtro_ordens_abertas', '')
    filtro_ordens_fechadas = request.GET.get('filtro_ordens_fechadas', '')
    
    # Converter para boolean (se existe e não é vazio, é True)
    filtro_ordens_abertas = filtro_ordens_abertas == '1'
    filtro_ordens_fechadas = filtro_ordens_fechadas == '1'
    
    # Aplicar filtros baseado nos checkboxes marcados
    if filtro_ordens_abertas and filtro_ordens_fechadas:
        # Ambos marcados: mostrar todas (não aplicar filtro)
        pass
    elif filtro_ordens_abertas and not filtro_ordens_fechadas:
        # Apenas "Ordens Abertas" marcado: dt_encordmanu está vazio ou nulo
        ordens_list = ordens_list.filter(
            Q(dt_encordmanu__isnull=True) | Q(dt_encordmanu='')
        )
    elif filtro_ordens_fechadas and not filtro_ordens_abertas:
        # Apenas "Ordens Fechadas" marcado: dt_encordmanu tem valor (não é nulo nem vazio)
        ordens_list = ordens_list.exclude(
            Q(dt_encordmanu__isnull=True) | Q(dt_encordmanu='')
        )
    # Se nenhum está marcado, mostra todas (não aplicar filtro)
    
    # Ordenar por código da ordem de serviço (mais recente primeiro)
    ordens_list = ordens_list.order_by('-cd_ordemserv')
    
    # Paginação
    paginator = Paginator(ordens_list, 50)  # 50 itens por página
    page_number = request.GET.get('page', 1)
    ordens = paginator.get_page(page_number)
    
    # Estatísticas
    total_count = OrdemServicoCorretiva.objects.count()
    setores_count = OrdemServicoCorretiva.objects.exclude(cd_setormanut__isnull=True).exclude(cd_setormanut='').values('cd_setormanut').distinct().count()
    unidades_count = OrdemServicoCorretiva.objects.exclude(nome_unid__isnull=True).exclude(nome_unid='').values('nome_unid').distinct().count()
    
    # Obter valores únicos para os dropdowns de filtros
    setores_unicos = OrdemServicoCorretiva.objects.exclude(
        descr_setormanut__isnull=True
    ).exclude(
        descr_setormanut=''
    ).values_list('descr_setormanut', flat=True).distinct().order_by('descr_setormanut')
    
    unidades_unicas = OrdemServicoCorretiva.objects.exclude(
        nome_unid__isnull=True
    ).exclude(
        nome_unid=''
    ).values_list('nome_unid', flat=True).distinct().order_by('nome_unid')
    
    tipos_os_unicos = OrdemServicoCorretiva.objects.exclude(
        descr_tpordservtv__isnull=True
    ).exclude(
        descr_tpordservtv=''
    ).values_list('descr_tpordservtv', flat=True).distinct().order_by('descr_tpordservtv')
    
    situacoes_unicas = OrdemServicoCorretiva.objects.exclude(
        descr_sitordsetv__isnull=True
    ).exclude(
        descr_sitordsetv=''
    ).values_list('descr_sitordsetv', flat=True).distinct().order_by('descr_sitordsetv')
    
    context = {
        'page_title': 'Consultar Ordens Corretivas/Outros',
        'active_page': 'consultar_corretivas_outros',
        'ordens': ordens,
        'total_count': total_count,
        'setores_count': setores_count,
        'unidades_count': unidades_count,
        # Valores para dropdowns
        'setores_unicos': setores_unicos,
        'unidades_unicas': unidades_unicas,
        'tipos_os_unicos': tipos_os_unicos,
        'situacoes_unicas': situacoes_unicas,
        # Valores dos filtros ativos
        'filtro_setor': filtro_setor,
        'filtro_unidade': filtro_unidade,
        'filtro_tipo_os': filtro_tipo_os,
        'filtro_situacao': filtro_situacao,
        'filtro_solicitante': filtro_solicitante,
        'filtro_executor': filtro_executor,
        'filtro_maquina': filtro_maquina,
        'data_entrada_inicio': data_entrada_inicio,
        'data_entrada_fim': data_entrada_fim,
        'filtro_ordens_abertas': '1' if filtro_ordens_abertas else '',
        'filtro_ordens_fechadas': '1' if filtro_ordens_fechadas else '',
    }
    return render(request, 'consultar/consultar_corretivas_outros.html', context)


def visualizar_corretiva_outros(request, ordem_id):
    """Visualizar detalhes de uma ordem corretiva específica"""
    from app.models import OrdemServicoCorretiva, Maquina
    
    try:
        ordem = OrdemServicoCorretiva.objects.get(id=ordem_id)
    except OrdemServicoCorretiva.DoesNotExist:
        messages.error(request, 'Ordem de serviço não encontrada.')
        return redirect('consultar_corretivas_outros')
    
    # Buscar a máquina correspondente se cd_maquina existir
    maquina = None
    if ordem.cd_maquina:
        try:
            maquina = Maquina.objects.get(cd_maquina=ordem.cd_maquina)
        except Maquina.DoesNotExist:
            maquina = None
    
    # Buscar fichas relacionadas (pode haver múltiplas fichas)
    fichas = ordem.fichas.all().order_by('-created_at')
    
    context = {
        'page_title': f'Visualizar OS {ordem.cd_ordemserv}',
        'active_page': 'consultar_corretivas_outros',
        'ordem': ordem,
        'maquina': maquina,
        'fichas': fichas,
    }
    return render(request, 'visualizar/visualizar_corretiva_outros.html', context)


def analise_corretiva_outros(request):
    """Página inicial da seção Manutenção Corretiva com análises e gráficos"""
    from app.models import OrdemServicoCorretiva, Maquina
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    from collections import defaultdict
    import json
    
    # Estatísticas básicas
    total_count = OrdemServicoCorretiva.objects.count()
    setores_count = OrdemServicoCorretiva.objects.exclude(cd_setormanut__isnull=True).exclude(cd_setormanut='').values('cd_setormanut').distinct().count()
    unidades_count = OrdemServicoCorretiva.objects.exclude(nome_unid__isnull=True).exclude(nome_unid='').values('nome_unid').distinct().count()
    maquinas_count = Maquina.objects.count()
    
    # Ordens por setor (top 10)
    ordens_por_setor = OrdemServicoCorretiva.objects.exclude(
        descr_setormanut__isnull=True
    ).exclude(
        descr_setormanut=''
    ).values('descr_setormanut').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    setores_labels = [item['descr_setormanut'][:30] for item in ordens_por_setor]
    setores_data = [item['total'] for item in ordens_por_setor]
    
    # Ordens por unidade (top 10)
    ordens_por_unidade = OrdemServicoCorretiva.objects.exclude(
        nome_unid__isnull=True
    ).exclude(
        nome_unid=''
    ).values('nome_unid').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    unidades_labels = [item['nome_unid'][:30] for item in ordens_por_unidade]
    unidades_data = [item['total'] for item in ordens_por_unidade]
    
    # Ordens por mês (últimos 12 meses)
    ordens_por_mes = defaultdict(int)
    ordens = OrdemServicoCorretiva.objects.all().order_by('created_at')
    for ordem in ordens:
        if ordem.created_at:
            mes_ano = ordem.created_at.strftime('%Y-%m')
            ordens_por_mes[mes_ano] += 1
    
    # Ordenar por data e pegar últimos 12 meses
    meses_ordenados = sorted(ordens_por_mes.keys())[-12:]
    meses_labels = [datetime.strptime(m, '%Y-%m').strftime('%b/%Y') for m in meses_ordenados]
    meses_data = [ordens_por_mes[m] for m in meses_ordenados]
    
    # Top 10 máquinas com mais ordens
    top_maquinas = OrdemServicoCorretiva.objects.exclude(
        descr_maquina__isnull=True
    ).exclude(
        descr_maquina=''
    ).values('cd_maquina', 'descr_maquina').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    maquinas_labels = [f"{item['cd_maquina']} - {item['descr_maquina'][:40]}" for item in top_maquinas]
    maquinas_data = [item['total'] for item in top_maquinas]
    
    # Top 10 executores
    top_executores = OrdemServicoCorretiva.objects.exclude(
        nm_func_exec_os__isnull=True
    ).exclude(
        nm_func_exec_os=''
    ).values('nm_func_exec_os').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    executores_labels = [item['nm_func_exec_os'][:30] for item in top_executores]
    executores_data = [item['total'] for item in top_executores]
    
    # Distribuição por tipo de ordem de serviço
    ordens_por_tipo = OrdemServicoCorretiva.objects.exclude(
        descr_tpordservtv__isnull=True
    ).exclude(
        descr_tpordservtv=''
    ).values('descr_tpordservtv').annotate(
        total=Count('id')
    ).order_by('-total')[:8]
    
    tipos_labels = [item['descr_tpordservtv'][:30] for item in ordens_por_tipo]
    tipos_data = [item['total'] for item in ordens_por_tipo]
    
    # Ordens recentes (últimas 30 dias)
    data_30_dias_atras = datetime.now() - timedelta(days=30)
    ordens_recentes = OrdemServicoCorretiva.objects.filter(
        created_at__gte=data_30_dias_atras
    ).count()
    
    # Ordens do mês atual
    mes_atual = datetime.now().replace(day=1)
    ordens_mes_atual = OrdemServicoCorretiva.objects.filter(
        created_at__gte=mes_atual
    ).count()
    
    # Ordens com queixa preenchida
    ordens_com_queixa = OrdemServicoCorretiva.objects.exclude(
        descr_queixa__isnull=True
    ).exclude(
        descr_queixa=''
    ).count()
    
    # Percentual de ordens com queixa
    percentual_queixa = (ordens_com_queixa / total_count * 100) if total_count > 0 else 0
    
    context = {
        'page_title': 'Manutenção Corretiva - Análise',
        'active_page': 'manutencao_corretiva',
        'total_count': total_count,
        'setores_count': setores_count,
        'unidades_count': unidades_count,
        'maquinas_count': maquinas_count,
        'ordens_recentes': ordens_recentes,
        'ordens_mes_atual': ordens_mes_atual,
        'ordens_com_queixa': ordens_com_queixa,
        'percentual_queixa': round(percentual_queixa, 1),
        # Dados para gráficos (JSON)
        'setores_labels': json.dumps(setores_labels),
        'setores_data': json.dumps(setores_data),
        'unidades_labels': json.dumps(unidades_labels),
        'unidades_data': json.dumps(unidades_data),
        'meses_labels': json.dumps(meses_labels),
        'meses_data': json.dumps(meses_data),
        'maquinas_labels': json.dumps(maquinas_labels),
        'maquinas_data': json.dumps(maquinas_data),
        'executores_labels': json.dumps(executores_labels),
        'executores_data': json.dumps(executores_data),
        'tipos_labels': json.dumps(tipos_labels),
        'tipos_data': json.dumps(tipos_data),
        # Dados para tabelas
        'top_maquinas': top_maquinas,
        'top_executores': top_executores,
    }
    return render(request, 'analise/analise_corretiva_outros.html', context)


def consultar_manutencao_terceiros(request):
    """Consultar/listar manutenções de terceiros cadastradas com filtros avançados"""
    from app.models import ManutencaoTerceiro
    from datetime import datetime
    
    # Buscar todas as manutenções de terceiros
    manutencoes_list = ManutencaoTerceiro.objects.all()
    
    # Filtro de busca geral (texto)
    search_query = request.GET.get('search', '').strip()
    if search_query:
        # Criar lista de condições Q
        search_conditions = Q()
        
        # Para campos de texto, usar icontains
        search_conditions |= (
            Q(titulo__icontains=search_query) |
            Q(os__icontains=search_query) |
            Q(empresa__icontains=search_query) |
            Q(pedidodecompra__icontains=search_query) |
            Q(requisicaodecompra__icontains=search_query) |
            Q(descricao__icontains=search_query) |
            Q(maquina__descr_maquina__icontains=search_query) |
            Q(manutentor__Nome__icontains=search_query)
        )
        
        manutencoes_list = manutencoes_list.filter(search_conditions)
    
    # Filtros específicos
    # Filtro por Empresa
    filtro_empresa = request.GET.get('filtro_empresa', '')
    if filtro_empresa:
        manutencoes_list = manutencoes_list.filter(empresa__icontains=filtro_empresa)
    
    # Filtro por Tipo
    filtro_tipo = request.GET.get('filtro_tipo', '')
    if filtro_tipo:
        manutencoes_list = manutencoes_list.filter(tipo=filtro_tipo)
    
    # Filtro por Máquina
    filtro_maquina = request.GET.get('filtro_maquina', '')
    if filtro_maquina:
        try:
            maquina_id = int(filtro_maquina)
            manutencoes_list = manutencoes_list.filter(maquina_id=maquina_id)
        except ValueError:
            manutencoes_list = manutencoes_list.filter(maquina__descr_maquina__icontains=filtro_maquina)
    
    # Filtro por Manutentor
    filtro_manutentor = request.GET.get('filtro_manutentor', '')
    if filtro_manutentor:
        try:
            manutentor_id = filtro_manutentor
            manutencoes_list = manutencoes_list.filter(manutentor__Cadastro=manutentor_id)
        except ValueError:
            manutencoes_list = manutencoes_list.filter(manutentor__Nome__icontains=filtro_manutentor)
    
    # Filtro por Data (período)
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    if data_inicio:
        try:
            data_ini = datetime.strptime(data_inicio, '%Y-%m-%d')
            manutencoes_list = manutencoes_list.filter(data__gte=data_ini)
        except ValueError:
            pass
    if data_fim:
        try:
            data_f = datetime.strptime(data_fim, '%Y-%m-%d')
            from datetime import timedelta
            data_f = data_f + timedelta(days=1)
            manutencoes_list = manutencoes_list.filter(data__lte=data_f)
        except ValueError:
            pass
    
    # Ordenar por data (mais recente primeiro)
    manutencoes_list = manutencoes_list.order_by('-data', '-created_at')
    
    # Paginação
    paginator = Paginator(manutencoes_list, 50)  # 50 itens por página
    page_number = request.GET.get('page', 1)
    manutencoes = paginator.get_page(page_number)
    
    # Estatísticas
    total_count = ManutencaoTerceiro.objects.count()
    empresas_count = ManutencaoTerceiro.objects.exclude(empresa__isnull=True).exclude(empresa='').values('empresa').distinct().count()
    tipos_count = ManutencaoTerceiro.objects.exclude(tipo__isnull=True).exclude(tipo='').values('tipo').distinct().count()
    
    # Obter valores únicos para os dropdowns de filtros
    empresas_unicas = ManutencaoTerceiro.objects.exclude(
        empresa__isnull=True
    ).exclude(
        empresa=''
    ).values_list('empresa', flat=True).distinct().order_by('empresa')
    
    tipos_unicos = ManutencaoTerceiro.objects.exclude(
        tipo__isnull=True
    ).exclude(
        tipo=''
    ).values_list('tipo', flat=True).distinct().order_by('tipo')
    
    maquinas_unicas = ManutencaoTerceiro.objects.exclude(
        maquina__isnull=True
    ).select_related('maquina').values_list('maquina__id', 'maquina__descr_maquina').distinct().order_by('maquina__descr_maquina')
    
    manutentores_unicos = ManutencaoTerceiro.objects.exclude(
        manutentor__isnull=True
    ).select_related('manutentor').values_list('manutentor__Cadastro', 'manutentor__Nome').distinct().order_by('manutentor__Nome')
    
    context = {
        'page_title': 'Consultar Manutenções Terceiros',
        'active_page': 'consultar_manutencao_terceiros',
        'manutencoes': manutencoes,
        'total_count': total_count,
        'empresas_count': empresas_count,
        'tipos_count': tipos_count,
        # Valores para dropdowns
        'empresas_unicas': empresas_unicas,
        'tipos_unicos': tipos_unicos,
        'maquinas_unicas': maquinas_unicas,
        'manutentores_unicos': manutentores_unicos,
        # Valores dos filtros ativos
        'filtro_empresa': filtro_empresa,
        'filtro_tipo': filtro_tipo,
        'filtro_maquina': filtro_maquina,
        'filtro_manutentor': filtro_manutentor,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    }
    return render(request, 'consultar/consultar_manutencao_terceiros.html', context)


def cadastrar_manutencao_terceiro(request):
    """Cadastrar nova manutenção de terceiro"""
    from app.forms import ManutencaoTerceiroForm
    
    if request.method == 'POST':
        form = ManutencaoTerceiroForm(request.POST)
        if form.is_valid():
            try:
                manutencao = form.save()
                messages.success(request, f'Manutenção de terceiro "{manutencao.titulo}" cadastrada com sucesso!')
                return redirect('home')
            except Exception as e:
                import traceback
                print(f"DEBUG - Erro ao salvar manutenção terceiro: {str(e)}")
                print(f"DEBUG - Traceback: {traceback.format_exc()}")
                messages.error(request, f'Erro ao cadastrar manutenção de terceiro: {str(e)}')
        else:
            # Exibir erros de validação específicos
            missing_required = []
            for field, errors in form.errors.items():
                field_label = form.fields[field].label
                for error in errors:
                    if 'required' in str(error).lower() or 'obrigatório' in str(error).lower():
                        missing_required.append(field_label)
                        messages.warning(request, f'<strong>{field_label}</strong>: Este campo é obrigatório e deve ser preenchido.')
                    else:
                        messages.error(request, f'<strong>{field_label}</strong>: {error}')
            
            if missing_required:
                messages.warning(request, f'<strong>Atenção:</strong> {len(missing_required)} campo(s) obrigatório(s) não preenchido(s). Por favor, preencha todos os campos marcados com <span class="text-danger">*</span>.')
            else:
                messages.error(request, 'Por favor, corrija os erros no formulário antes de continuar.')
    else:
        form = ManutencaoTerceiroForm()
    
    context = {
        'page_title': 'Cadastrar Manutenção Terceiro',
        'active_page': 'cadastrar_manutencao_terceiro',
        'form': form
    }
    return render(request, 'cadastrar/cadastrar_manutencao_terceiro.html', context)


def cadastrar_manutentor(request):
    """Cadastrar novo manutentor"""
    from app.forms import ManutentorForm
    from app.models import ManutentorMaquina, Maquina
    
    if request.method == 'POST':
        form = ManutentorForm(request.POST)
        if form.is_valid():
            try:
                manutentor = form.save()
                
                # Processar máquinas selecionadas
                maquinas_ids = request.POST.getlist('maquinas_selecionadas')
                maquinas_adicionadas = 0
                for maquina_id in maquinas_ids:
                    try:
                        maquina = Maquina.objects.get(id=maquina_id)
                        # Verificar se já existe relação
                        if not ManutentorMaquina.objects.filter(manutentor=manutentor, maquina=maquina).exists():
                            ManutentorMaquina.objects.create(
                                manutentor=manutentor,
                                maquina=maquina
                            )
                            maquinas_adicionadas += 1
                    except Maquina.DoesNotExist:
                        pass
                    except Exception as e:
                        print(f"Erro ao relacionar máquina {maquina_id}: {str(e)}")
                
                if maquinas_adicionadas > 0:
                    messages.success(request, f'Manutentor {manutentor.Cadastro} cadastrado com sucesso! {maquinas_adicionadas} máquina(s) relacionada(s).')
                else:
                    messages.success(request, f'Manutentor {manutentor.Cadastro} cadastrado com sucesso!')
                
                return redirect('consultar_manutentores')
            except Exception as e:
                import traceback
                print(f"DEBUG - Erro ao salvar manutentor: {str(e)}")
                print(f"DEBUG - Traceback: {traceback.format_exc()}")
                messages.error(request, f'Erro ao cadastrar manutentor: {str(e)}')
        else:
            # Exibir erros de validação específicos
            missing_required = []
            for field, errors in form.errors.items():
                field_label = form.fields[field].label
                for error in errors:
                    if 'required' in str(error).lower() or 'obrigatório' in str(error).lower():
                        missing_required.append(field_label)
                        messages.warning(request, f'<strong>{field_label}</strong>: Este campo é obrigatório e deve ser preenchido.')
                    else:
                        messages.error(request, f'<strong>{field_label}</strong>: {error}')
            
            if missing_required:
                messages.warning(request, f'<strong>Atenção:</strong> {len(missing_required)} campo(s) obrigatório(s) não preenchido(s). Por favor, preencha todos os campos marcados com <span class="text-danger">*</span>.')
            else:
                messages.error(request, 'Por favor, corrija os erros no formulário antes de continuar.')
    else:
        form = ManutentorForm()
    
    # Buscar todas as máquinas disponíveis
    maquinas_disponiveis = Maquina.objects.all().order_by('cd_maquina')
    
    context = {
        'page_title': 'Cadastrar Manutentor',
        'active_page': 'cadastrar_manutentor',
        'form': form,
        'maquinas_disponiveis': maquinas_disponiveis
    }
    return render(request, 'cadastrar/cadastrar_manutentor.html', context)


def visualizar_manutentor(request, cadastro):
    """Visualizar detalhes de um manutentor específico"""
    from app.models import Manutentor, ManutentorMaquina, Maquina
    
    try:
        manutentor = Manutentor.objects.get(Cadastro=cadastro)
    except Manutentor.DoesNotExist:
        messages.error(request, 'Manutentor não encontrado.')
        return redirect('consultar_manutentores')
    
    # Buscar máquinas relacionadas
    maquinas_relacionadas = ManutentorMaquina.objects.filter(manutentor=manutentor).select_related('maquina')
    
    # Buscar máquinas já relacionadas para excluir da lista de disponíveis
    maquinas_ids_relacionadas = maquinas_relacionadas.values_list('maquina_id', flat=True)
    maquinas_disponiveis = Maquina.objects.exclude(id__in=maquinas_ids_relacionadas).order_by('cd_maquina')
    
    context = {
        'page_title': f'Visualizar Manutentor {manutentor.Cadastro}',
        'active_page': 'consultar_manutentores',
        'manutentor': manutentor,
        'maquinas_relacionadas': maquinas_relacionadas,
        'maquinas_disponiveis': maquinas_disponiveis,
    }
    return render(request, 'visualizar/visualizar_manutentor.html', context)


def editar_manutentor(request, cadastro):
    """Editar um manutentor existente"""
    from app.forms import ManutentorForm
    from app.models import Manutentor
    
    try:
        manutentor = Manutentor.objects.get(Cadastro=cadastro)
    except Manutentor.DoesNotExist:
        messages.error(request, 'Manutentor não encontrado.')
        return redirect('consultar_manutentores')
    
    if request.method == 'POST':
        # Garantir que o Cadastro não seja alterado (é a primary key)
        post_data = request.POST.copy()
        post_data['Cadastro'] = manutentor.Cadastro
        
        form = ManutentorForm(post_data, instance=manutentor)
        
        if form.is_valid():
            try:
                manutentor = form.save()
                messages.success(request, f'Manutentor {manutentor.Cadastro} atualizado com sucesso!')
                return redirect('visualizar_manutentor', cadastro=manutentor.Cadastro)
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                print(f"Erro ao salvar manutentor: {error_detail}")
                messages.error(request, f'Erro ao atualizar manutentor: {str(e)}')
        else:
            handle_form_errors(form, request)
    else:
        form = ManutentorForm(instance=manutentor)
        # Tornar o campo Cadastro readonly na edição (é a primary key)
        form.fields['Cadastro'].widget.attrs['readonly'] = True
        form.fields['Cadastro'].widget.attrs['class'] = 'form-control bg-light'
    
    context = {
        'page_title': f'Editar Manutentor {manutentor.Cadastro}',
        'active_page': 'consultar_manutentores',
        'form': form,
        'manutentor': manutentor,
    }
    return render(request, 'visualizar/editar_manutentor.html', context)


def consultar_manutentores(request):
    """Consultar/listar manutentores cadastrados com filtros avançados"""
    from app.models import Manutentor, TIPO_MANUTENTOR, TURNO, LOCAL_TRABALHO
    from datetime import datetime
    
    # Buscar todos os manutentores
    manutentores_list = Manutentor.objects.all()
    
    # Filtro de busca geral (texto)
    search_query = request.GET.get('search', '').strip()
    if search_query:
        manutentores_list = manutentores_list.filter(
            Q(Cadastro__icontains=search_query) |
            Q(Nome__icontains=search_query) |
            Q(Cargo__icontains=search_query) |
            Q(Posto__icontains=search_query) |
            Q(tipo__icontains=search_query) |
            Q(turno__icontains=search_query) |
            Q(local_trab__icontains=search_query)
        )
    
    # Filtros específicos
    # Filtro por Tipo
    filtro_tipo = request.GET.get('filtro_tipo', '')
    if filtro_tipo:
        manutentores_list = manutentores_list.filter(tipo=filtro_tipo)
    
    # Filtro por Turno
    filtro_turno = request.GET.get('filtro_turno', '')
    if filtro_turno:
        manutentores_list = manutentores_list.filter(turno=filtro_turno)
    
    # Filtro por Local de Trabalho
    filtro_local_trab = request.GET.get('filtro_local_trab', '')
    if filtro_local_trab:
        manutentores_list = manutentores_list.filter(local_trab=filtro_local_trab)
    
    # Filtro por Cargo
    filtro_cargo = request.GET.get('filtro_cargo', '')
    if filtro_cargo:
        manutentores_list = manutentores_list.filter(Cargo__icontains=filtro_cargo)
    
    # Filtro por Posto
    filtro_posto = request.GET.get('filtro_posto', '')
    if filtro_posto:
        manutentores_list = manutentores_list.filter(Posto__icontains=filtro_posto)
    
    # Filtro por Data de Admissão (período)
    data_admissao_inicio = request.GET.get('data_admissao_inicio', '')
    data_admissao_fim = request.GET.get('data_admissao_fim', '')
    if data_admissao_inicio:
        try:
            data_inicio = datetime.strptime(data_admissao_inicio, '%Y-%m-%d').date()
            manutentores_list = manutentores_list.filter(Admissao__gte=data_inicio)
        except ValueError:
            pass
    if data_admissao_fim:
        try:
            data_fim = datetime.strptime(data_admissao_fim, '%Y-%m-%d').date()
            # Adicionar 1 dia para incluir o dia final
            from datetime import timedelta
            data_fim = data_fim + timedelta(days=1)
            manutentores_list = manutentores_list.filter(Admissao__lte=data_fim)
        except ValueError:
            pass
    
    # Ordenar por nome e cadastro
    manutentores_list = manutentores_list.order_by('Nome', 'Cadastro')
    
    # Paginação
    paginator = Paginator(manutentores_list, 50)  # 50 itens por página
    page_number = request.GET.get('page', 1)
    manutentores = paginator.get_page(page_number)
    
    # Estatísticas
    total_count = Manutentor.objects.count()
    tipos_count = Manutentor.objects.exclude(tipo__isnull=True).exclude(tipo='').values('tipo').distinct().count()
    turnos_count = Manutentor.objects.exclude(turno__isnull=True).exclude(turno='').values('turno').distinct().count()
    locais_count = Manutentor.objects.exclude(local_trab__isnull=True).exclude(local_trab='').values('local_trab').distinct().count()
    
    # Obter valores únicos para os dropdowns de filtros
    cargos_unicos = Manutentor.objects.exclude(
        Cargo__isnull=True
    ).exclude(
        Cargo=''
    ).values_list('Cargo', flat=True).distinct().order_by('Cargo')
    
    postos_unicos = Manutentor.objects.exclude(
        Posto__isnull=True
    ).exclude(
        Posto=''
    ).values_list('Posto', flat=True).distinct().order_by('Posto')
    
    context = {
        'page_title': 'Consultar Manutentores',
        'active_page': 'consultar_manutentores',
        'manutentores': manutentores,
        'total_count': total_count,
        'tipos_count': tipos_count,
        'turnos_count': turnos_count,
        'locais_count': locais_count,
        # Valores para dropdowns
        'tipos_manutentor': TIPO_MANUTENTOR,
        'turnos': TURNO,
        'locais_trabalho': LOCAL_TRABALHO,
        'cargos_unicos': cargos_unicos,
        'postos_unicos': postos_unicos,
        # Valores dos filtros ativos
        'filtro_tipo': filtro_tipo,
        'filtro_turno': filtro_turno,
        'filtro_local_trab': filtro_local_trab,
        'filtro_cargo': filtro_cargo,
        'filtro_posto': filtro_posto,
        'data_admissao_inicio': data_admissao_inicio,
        'data_admissao_fim': data_admissao_fim,
    }
    return render(request, 'consultar/consultar_manutentores.html', context)


def gerenciar_projeto(request):
    """Página de gerenciamento administrativo do projeto"""
    from app.models import (
        Maquina, OrdemServicoCorretiva, OrdemServicoCorretivaFicha,
        CentroAtividade, LocalCentroAtividade, Manutentor, ManutentorMaquina,
        ItemEstoque, ManutencaoCsv, ManutencaoTerceiro, MaquinaPeca,
        MaquinaPrimariaSecundaria, PlanoPreventiva, PlanoPreventivaDocumento
    )
    
    # Definir todos os modelos com suas informações
    modelos_info = [
        {
            'nome': 'Máquinas',
            'modelo': Maquina,
            'key': 'maquinas',
            'icone': 'fas fa-industry',
            'cor': 'primary',
            'descricao': 'Registros de máquinas cadastradas no sistema'
        },
        {
            'nome': 'Ordens Corretivas',
            'modelo': OrdemServicoCorretiva,
            'key': 'ordens',
            'icone': 'fas fa-wrench',
            'cor': 'info',
            'descricao': 'Ordens de serviço corretivas e outros fechadas'
        },
        {
            'nome': 'Fichas de Ordens Corretivas',
            'modelo': OrdemServicoCorretivaFicha,
            'key': 'ordens_ficha',
            'icone': 'fas fa-file-alt',
            'cor': 'info',
            'descricao': 'Fichas técnicas de ordens de serviço corretivas'
        },
        {
            'nome': 'Centros de Atividade',
            'modelo': CentroAtividade,
            'key': 'centros',
            'icone': 'fas fa-building',
            'cor': 'success',
            'descricao': 'Centros de atividade (CA) cadastrados'
        },
        {
            'nome': 'Locais e Centros de Atividade',
            'modelo': LocalCentroAtividade,
            'key': 'locais_centros',
            'icone': 'fas fa-map-marker-alt',
            'cor': 'success',
            'descricao': 'Relação entre locais e centros de atividade'
        },
        {
            'nome': 'Manutentores',
            'modelo': Manutentor,
            'key': 'manutentores',
            'icone': 'fas fa-user-tie',
            'cor': 'warning',
            'descricao': 'Manutentores cadastrados no sistema'
        },
        {
            'nome': 'Máquinas dos Manutentores',
            'modelo': ManutentorMaquina,
            'key': 'manutentor_maquina',
            'icone': 'fas fa-link',
            'cor': 'warning',
            'descricao': 'Relação entre manutentores e máquinas'
        },
        {
            'nome': 'Itens de Estoque',
            'modelo': ItemEstoque,
            'key': 'estoque',
            'icone': 'fas fa-boxes',
            'cor': 'secondary',
            'descricao': 'Itens de estoque cadastrados'
        },
        {
            'nome': 'Manutenções CSV',
            'modelo': ManutencaoCsv,
            'key': 'manutencao_csv',
            'icone': 'fas fa-file-csv',
            'cor': 'dark',
            'descricao': 'Manutenções importadas via CSV'
        },
        {
            'nome': 'Manutenções Terceiros',
            'modelo': ManutencaoTerceiro,
            'key': 'manutencao_terceiros',
            'icone': 'fas fa-tools',
            'cor': 'danger',
            'descricao': 'Manutenções de terceiros cadastradas'
        },
        {
            'nome': 'Peças das Máquinas',
            'modelo': MaquinaPeca,
            'key': 'maquina_peca',
            'icone': 'fas fa-cog',
            'cor': 'primary',
            'descricao': 'Relação entre máquinas e peças'
        },
        {
            'nome': 'Máquinas Primárias/Secundárias',
            'modelo': MaquinaPrimariaSecundaria,
            'key': 'maquina_primaria_secundaria',
            'icone': 'fas fa-sitemap',
            'cor': 'primary',
            'descricao': 'Relação entre máquinas primárias e secundárias'
        },
        {
            'nome': 'Planos Preventiva',
            'modelo': PlanoPreventiva,
            'key': 'plano_preventiva',
            'icone': 'fas fa-calendar-check',
            'cor': 'success',
            'descricao': 'Planos de manutenção preventiva'
        },
        {
            'nome': 'Documentos Planos Preventiva',
            'modelo': PlanoPreventivaDocumento,
            'key': 'plano_preventiva_documento',
            'icone': 'fas fa-file-upload',
            'cor': 'success',
            'descricao': 'Documentos relacionados aos planos preventiva'
        },
    ]
    
    # Contar registros em cada tabela
    tabelas_info = []
    total_geral = 0
    
    for info in modelos_info:
        count = info['modelo'].objects.count()
        total_geral += count
        tabelas_info.append({
            **info,
            'count': count
        })
    
    # Manter compatibilidade com o template atual (primeiros 4 para cards de estatísticas)
    maquinas_count = tabelas_info[0]['count'] if len(tabelas_info) > 0 else 0
    ordens_count = tabelas_info[1]['count'] if len(tabelas_info) > 1 else 0
    centros_count = tabelas_info[2]['count'] if len(tabelas_info) > 2 else 0
    manutentores_count = tabelas_info[3]['count'] if len(tabelas_info) > 3 else 0
    
    context = {
        'page_title': 'Gerenciar Projeto',
        'active_page': 'gerenciar_projeto',
        'maquinas_count': maquinas_count,
        'ordens_count': ordens_count,
        'centros_count': centros_count,
        'manutentores_count': manutentores_count,
        'tabelas_info': tabelas_info,
        'total_geral': total_geral,
    }
    return render(request, 'administrador/gerenciar_projeto.html', context)


def limpar_tabela(request):
    """Limpar registros de uma tabela específica ou todas as tabelas"""
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('gerenciar_projeto')
    
    from app.models import (
        Maquina, OrdemServicoCorretiva, OrdemServicoCorretivaFicha,
        CentroAtividade, LocalCentroAtividade, Manutentor, ManutentorMaquina,
        ItemEstoque, ManutencaoCsv, ManutencaoTerceiro, MaquinaPeca,
        MaquinaPrimariaSecundaria, PlanoPreventiva, PlanoPreventivaDocumento
    )
    
    # Mapeamento de tabelas para modelos
    tabelas_map = {
        'maquinas': {'modelo': Maquina, 'nome': 'Máquinas'},
        'ordens': {'modelo': OrdemServicoCorretiva, 'nome': 'Ordens Corretivas'},
        'ordens_ficha': {'modelo': OrdemServicoCorretivaFicha, 'nome': 'Fichas de Ordens Corretivas'},
        'centros': {'modelo': CentroAtividade, 'nome': 'Centros de Atividade'},
        'locais_centros': {'modelo': LocalCentroAtividade, 'nome': 'Locais e Centros de Atividade'},
        'manutentores': {'modelo': Manutentor, 'nome': 'Manutentores'},
        'manutentor_maquina': {'modelo': ManutentorMaquina, 'nome': 'Máquinas dos Manutentores'},
        'estoque': {'modelo': ItemEstoque, 'nome': 'Itens de Estoque'},
        'manutencao_csv': {'modelo': ManutencaoCsv, 'nome': 'Manutenções CSV'},
        'manutencao_terceiros': {'modelo': ManutencaoTerceiro, 'nome': 'Manutenções Terceiros'},
        'maquina_peca': {'modelo': MaquinaPeca, 'nome': 'Peças das Máquinas'},
        'maquina_primaria_secundaria': {'modelo': MaquinaPrimariaSecundaria, 'nome': 'Máquinas Primárias/Secundárias'},
        'plano_preventiva': {'modelo': PlanoPreventiva, 'nome': 'Planos Preventiva'},
        'plano_preventiva_documento': {'modelo': PlanoPreventivaDocumento, 'nome': 'Documentos Planos Preventiva'},
    }
    
    tabela = request.POST.get('tabela', '')
    
    try:
        if tabela == 'todos':
            # Limpar todas as tabelas
            total_removido = 0
            detalhes = []
            
            for key, info in tabelas_map.items():
                count = info['modelo'].objects.count()
                if count > 0:
                    info['modelo'].objects.all().delete()
                    total_removido += count
                    detalhes.append(f"{info['nome']} ({count})")
            
            if total_removido > 0:
                detalhes_str = '<br>'.join([f"- {d}" for d in detalhes])
                messages.success(request, f'Todas as tabelas foram limpas. Total de {total_removido} registro(s) removidos.<br><br>{detalhes_str}')
            else:
                messages.info(request, 'Não há registros para limpar.')
        
        elif tabela in tabelas_map:
            # Limpar tabela específica
            info = tabelas_map[tabela]
            count = info['modelo'].objects.count()
            info['modelo'].objects.all().delete()
            messages.success(request, f'{count} registro(s) de {info["nome"]} foram removidos com sucesso.')
        
        else:
            messages.error(request, 'Tabela não reconhecida.')
    
    except Exception as e:
        messages.error(request, f'Erro ao limpar tabela: {str(e)}')
    
    return redirect('gerenciar_projeto')


def adicionar_peca_maquina(request, maquina_id):
    """Adicionar uma peça de estoque a uma máquina"""
    print(f"=== ADICIONAR PECA MAQUINA === Method: {request.method}, Maquina ID: {maquina_id}")
    print(f"POST data: {request.POST}")
    print(f"GET data: {request.GET}")
    
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        # Redirecionar para a página de peças se vier de lá, senão para visualizar
        redirect_to = request.GET.get('redirect_to', 'visualizar_maquina')
        if redirect_to == 'maquinas_pecas':
            return redirect('maquinas_pecas', maquina_id=maquina_id)
        return redirect('visualizar_maquina', maquina_id=maquina_id)
    
    from app.models import Maquina, ItemEstoque, MaquinaPeca
    
    try:
        maquina = Maquina.objects.get(id=maquina_id)
    except Maquina.DoesNotExist:
        messages.error(request, 'Máquina não encontrada.')
        return redirect('consultar_maquinas')
    
    item_estoque_id = request.POST.get('item_estoque_id')
    quantidade = request.POST.get('quantidade', '1')
    observacoes = request.POST.get('observacoes', '')
    
    if not item_estoque_id:
        messages.error(request, 'Por favor, selecione um item de estoque.')
        # Redirecionar para a página de peças se vier de lá, senão para visualizar
        redirect_to = request.GET.get('redirect_to', 'visualizar_maquina')
        if redirect_to == 'maquinas_pecas':
            return redirect('maquinas_pecas', maquina_id=maquina_id)
        return redirect('visualizar_maquina', maquina_id=maquina_id)
    
    try:
        item_estoque = ItemEstoque.objects.get(id=item_estoque_id)
        
        # Verificar se já existe relação
        if MaquinaPeca.objects.filter(maquina=maquina, item_estoque=item_estoque).exists():
            messages.warning(request, f'Esta peça já está relacionada à máquina {maquina.cd_maquina}.')
        else:
            # Converter quantidade para Decimal
            from decimal import Decimal
            try:
                quantidade_decimal = Decimal(str(quantidade))
            except (ValueError, TypeError):
                quantidade_decimal = Decimal('1.0')
            
            # Criar relação
            try:
                MaquinaPeca.objects.create(
                    maquina=maquina,
                    item_estoque=item_estoque,
                    quantidade=quantidade_decimal,
                    observacoes=observacoes if observacoes else None
                )
                messages.success(request, f'Peça "{item_estoque.descricao_item or item_estoque.codigo_item}" adicionada com sucesso à máquina {maquina.cd_maquina}.')
            except Exception as create_error:
                from django.db import IntegrityError
                if isinstance(create_error, IntegrityError):
                    messages.warning(request, f'Esta peça já está relacionada à máquina {maquina.cd_maquina}.')
                else:
                    raise create_error
    
    except ItemEstoque.DoesNotExist:
        messages.error(request, 'Item de estoque não encontrado.')
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        messages.error(request, f'Erro ao adicionar peça: {str(e)}')
        print(f"Erro ao adicionar peça: {error_detail}")  # Debug
    
    # Redirecionar para a página de peças se vier de lá, senão para visualizar
    redirect_to = request.GET.get('redirect_to', 'visualizar_maquina')
    if redirect_to == 'maquinas_pecas':
        return redirect('maquinas_pecas', maquina_id=maquina_id)
    return redirect('visualizar_maquina', maquina_id=maquina_id)


def adicionar_maquina_manutentor(request, cadastro):
    """Adicionar uma máquina a um manutentor"""
    from app.models import Manutentor, ManutentorMaquina, Maquina
    from django.db import IntegrityError
    
    print(f"=== ADICIONAR MAQUINA MANUTENTOR === Method: {request.method}, Cadastro: {cadastro}")
    print(f"POST data: {request.POST}")
    print(f"GET data: {request.GET}")
    
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('visualizar_manutentor', cadastro=cadastro)
    
    try:
        manutentor = Manutentor.objects.get(Cadastro=cadastro)
    except Manutentor.DoesNotExist:
        messages.error(request, 'Manutentor não encontrado.')
        return redirect('consultar_manutentores')
    
    maquina_id = request.POST.get('maquina_id')
    observacoes = request.POST.get('observacoes', '')
    
    if not maquina_id:
        messages.error(request, 'Por favor, selecione uma máquina.')
        return redirect('visualizar_manutentor', cadastro=cadastro)
    
    try:
        maquina = Maquina.objects.get(id=maquina_id)
        
        # Verificar se já existe relação
        if ManutentorMaquina.objects.filter(manutentor=manutentor, maquina=maquina).exists():
            messages.warning(request, f'Esta máquina já está relacionada ao manutentor {manutentor.Cadastro}.')
        else:
            # Criar relação
            try:
                ManutentorMaquina.objects.create(
                    manutentor=manutentor,
                    maquina=maquina,
                    observacoes=observacoes if observacoes else None
                )
                messages.success(request, f'Máquina "{maquina.cd_maquina}" adicionada com sucesso ao manutentor {manutentor.Cadastro}.')
            except Exception as create_error:
                if isinstance(create_error, IntegrityError):
                    messages.warning(request, f'Esta máquina já está relacionada ao manutentor {manutentor.Cadastro}.')
                else:
                    raise create_error
    
    except Maquina.DoesNotExist:
        messages.error(request, 'Máquina não encontrada.')
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        messages.error(request, f'Erro ao adicionar máquina: {str(e)}')
        print(f"Erro ao adicionar máquina: {error_detail}")  # Debug
    
    return redirect('visualizar_manutentor', cadastro=cadastro)


def remover_maquina_manutentor(request, cadastro, manutentor_maquina_id):
    """Remover uma máquina de um manutentor"""
    from app.models import Manutentor, ManutentorMaquina
    
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('visualizar_manutentor', cadastro=cadastro)
    
    try:
        manutentor = Manutentor.objects.get(Cadastro=cadastro)
    except Manutentor.DoesNotExist:
        messages.error(request, 'Manutentor não encontrado.')
        return redirect('consultar_manutentores')
    
    try:
        manutentor_maquina = ManutentorMaquina.objects.get(id=manutentor_maquina_id, manutentor=manutentor)
        maquina_codigo = manutentor_maquina.maquina.cd_maquina
        manutentor_maquina.delete()
        messages.success(request, f'Máquina "{maquina_codigo}" removida com sucesso do manutentor {manutentor.Cadastro}.')
    except ManutentorMaquina.DoesNotExist:
        messages.error(request, 'Relação não encontrada.')
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        messages.error(request, f'Erro ao remover máquina: {str(e)}')
        print(f"Erro ao remover máquina: {error_detail}")  # Debug
    
    return redirect('visualizar_manutentor', cadastro=cadastro)


def remover_peca_maquina(request, maquina_id, peca_id):
    """Remover uma peça de estoque de uma máquina"""
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        # Redirecionar para a página de peças se vier de lá, senão para visualizar
        redirect_to = request.GET.get('redirect_to', 'visualizar_maquina')
        if redirect_to == 'maquinas_pecas':
            return redirect('maquinas_pecas', maquina_id=maquina_id)
        return redirect('visualizar_maquina', maquina_id=maquina_id)
    
    from app.models import MaquinaPeca
    
    try:
        peca = MaquinaPeca.objects.get(id=peca_id, maquina_id=maquina_id)
        item_descricao = peca.item_estoque.descricao_item or peca.item_estoque.codigo_item
        peca.delete()
        messages.success(request, f'Peça "{item_descricao}" removida com sucesso da máquina.')
    except MaquinaPeca.DoesNotExist:
        messages.error(request, 'Relação de peça não encontrada.')
    except Exception as e:
        messages.error(request, f'Erro ao remover peça: {str(e)}')
    
    # Redirecionar para a página de peças se vier de lá, senão para visualizar
    redirect_to = request.GET.get('redirect_to', 'visualizar_maquina')
    if redirect_to == 'maquinas_pecas':
        return redirect('maquinas_pecas', maquina_id=maquina_id)
    return redirect('visualizar_maquina', maquina_id=maquina_id)


def deletar_maquina(request, maquina_id):
    """Deletar uma máquina e seus relacionamentos"""
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('consultar_maquinas')
    
    from app.models import Maquina, ManutentorMaquina, MaquinaPeca, MaquinaPrimariaSecundaria
    
    try:
        maquina = Maquina.objects.get(id=maquina_id)
        cd_maquina = maquina.cd_maquina
        descr_maquina = maquina.descr_maquina or 'Sem descrição'
        
        # Contar relacionamentos que serão deletados
        relacionamentos_manutentor = ManutentorMaquina.objects.filter(maquina=maquina).count()
        relacionamentos_pecas = MaquinaPeca.objects.filter(maquina=maquina).count()
        relacionamentos_primaria = MaquinaPrimariaSecundaria.objects.filter(maquina_primaria=maquina).count()
        relacionamentos_secundaria = MaquinaPrimariaSecundaria.objects.filter(maquina_secundaria=maquina).count()
        
        # Deletar a máquina (os relacionamentos serão deletados automaticamente devido ao CASCADE)
        maquina.delete()
        
        # Mensagem de sucesso com detalhes
        detalhes = []
        if relacionamentos_manutentor > 0:
            detalhes.append(f'{relacionamentos_manutentor} relacionamento(s) com manutentor(es)')
        if relacionamentos_pecas > 0:
            detalhes.append(f'{relacionamentos_pecas} relacionamento(s) com peça(s)')
        if relacionamentos_primaria > 0:
            detalhes.append(f'{relacionamentos_primaria} relacionamento(s) como máquina primária')
        if relacionamentos_secundaria > 0:
            detalhes.append(f'{relacionamentos_secundaria} relacionamento(s) como máquina secundária')
        
        mensagem = f'Máquina "{cd_maquina} - {descr_maquina}" deletada com sucesso.'
        if detalhes:
            mensagem += f' Também foram removidos: {", ".join(detalhes)}.'
        
        messages.success(request, mensagem)
        
    except Maquina.DoesNotExist:
        messages.error(request, 'Máquina não encontrada.')
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        messages.error(request, f'Erro ao deletar máquina: {str(e)}')
        print(f"Erro ao deletar máquina: {error_detail}")
    
    # Redirecionar de volta para a página de consulta, preservando filtros
    redirect_url = 'consultar_maquinas'
    if request.GET.get('search'):
        redirect_url += f"?search={request.GET.get('search')}"
    if request.GET.get('page'):
        redirect_url += f"{'&' if '?' in redirect_url else '?'}page={request.GET.get('page')}"
    
    return redirect(redirect_url)


def atualizar_codigo_aurora(request, maquina_id):
    """Atualizar foto do código Aurora de uma máquina"""
    from app.models import Maquina
    
    print(f"=== ATUALIZAR CODIGO AURORA === Method: {request.method}, Maquina ID: {maquina_id}")
    print(f"POST data: {request.POST}")
    print(f"FILES data: {request.FILES}")
    
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('maquinas_pecas', maquina_id=maquina_id)
    
    try:
        maquina = Maquina.objects.get(id=maquina_id)
    except Maquina.DoesNotExist:
        messages.error(request, 'Máquina não encontrada.')
        return redirect('consultar_maquinas')
    
    try:
        if 'codigo_aurora' in request.FILES:
            arquivo = request.FILES['codigo_aurora']
            print(f"Arquivo recebido: {arquivo.name}, Tamanho: {arquivo.size}, Tipo: {arquivo.content_type}")
            maquina.codigo_aurora = arquivo
            maquina.save()
            print(f"Foto salva com sucesso: {maquina.codigo_aurora.url if maquina.codigo_aurora else 'N/A'}")
            messages.success(request, 'Foto do código Aurora atualizada com sucesso!')
        else:
            print("Nenhum arquivo encontrado em request.FILES")
            messages.error(request, 'Nenhum arquivo foi enviado.')
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Erro ao atualizar código Aurora: {error_detail}")
        messages.error(request, f'Erro ao atualizar foto: {str(e)}')
    
    return redirect('maquinas_pecas', maquina_id=maquina_id)


def atualizar_codigo_fabricante(request, maquina_id):
    """Atualizar foto do código do fabricante de uma máquina"""
    from app.models import Maquina
    
    print(f"=== ATUALIZAR CODIGO FABRICANTE === Method: {request.method}, Maquina ID: {maquina_id}")
    print(f"POST data: {request.POST}")
    print(f"FILES data: {request.FILES}")
    
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('maquinas_pecas', maquina_id=maquina_id)
    
    try:
        maquina = Maquina.objects.get(id=maquina_id)
    except Maquina.DoesNotExist:
        messages.error(request, 'Máquina não encontrada.')
        return redirect('consultar_maquinas')
    
    try:
        if 'codigo_fabricante' in request.FILES:
            arquivo = request.FILES['codigo_fabricante']
            print(f"Arquivo recebido: {arquivo.name}, Tamanho: {arquivo.size}, Tipo: {arquivo.content_type}")
            maquina.codigo_fabricante = arquivo
            maquina.save()
            print(f"Foto salva com sucesso: {maquina.codigo_fabricante.url if maquina.codigo_fabricante else 'N/A'}")
            messages.success(request, 'Foto do código do fabricante atualizada com sucesso!')
        else:
            print("Nenhum arquivo encontrado em request.FILES")
            messages.error(request, 'Nenhum arquivo foi enviado.')
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Erro ao atualizar código Fabricante: {error_detail}")
        messages.error(request, f'Erro ao atualizar foto: {str(e)}')
    
    return redirect('maquinas_pecas', maquina_id=maquina_id)


def maquinas_pecas(request, maquina_id):
    """Página para gerenciar peças de reposição de uma máquina"""
    from app.models import Maquina, ItemEstoque, MaquinaPeca
    
    try:
        maquina = Maquina.objects.get(id=maquina_id)
    except Maquina.DoesNotExist:
        messages.error(request, 'Máquina não encontrada.')
        return redirect('consultar_maquinas')
    
    # Buscar peças relacionadas a esta máquina
    pecas_relacionadas = MaquinaPeca.objects.filter(maquina=maquina).select_related('item_estoque').order_by('-created_at')
    
    # Buscar todos os itens de estoque para seleção (excluindo os já relacionados)
    itens_estoque_ids = pecas_relacionadas.values_list('item_estoque_id', flat=True)
    itens_disponiveis = ItemEstoque.objects.exclude(id__in=itens_estoque_ids).order_by('codigo_item')[:100]  # Limitar a 100 para performance
    
    context = {
        'page_title': f'Peças de Reposição - Máquina {maquina.cd_maquina}',
        'active_page': 'consultar_maquinas',
        'maquina': maquina,
        'pecas_relacionadas': pecas_relacionadas,
        'itens_disponiveis': itens_disponiveis,
    }
    return render(request, 'visualizar/visualizar_maquina_pecas.html', context)


def visualizar_item_estoque(request, item_id):
    """Visualizar detalhes de um item de estoque específico"""
    from app.models import ItemEstoque, MaquinaPeca
    
    try:
        item = ItemEstoque.objects.get(id=item_id)
    except ItemEstoque.DoesNotExist:
        messages.error(request, 'Item de estoque não encontrado.')
        return redirect('consultar_estoque')
    
    # Buscar máquinas relacionadas a este item
    maquinas_relacionadas = MaquinaPeca.objects.filter(item_estoque=item).select_related('maquina').order_by('-created_at')
    
    context = {
        'page_title': f'Visualizar Item de Estoque {item.codigo_item}',
        'active_page': 'consultar_estoque',
        'item': item,
        'maquinas_relacionadas': maquinas_relacionadas,
    }
    return render(request, 'visualizar/visualizar_item_peca.html', context)


def atualizar_foto_item(request, item_id):
    """Atualizar foto do item de estoque"""
    from app.models import ItemEstoque
    
    print(f"=== ATUALIZAR FOTO ITEM === Method: {request.method}, Item ID: {item_id}")
    print(f"POST data: {request.POST}")
    print(f"FILES data: {request.FILES}")
    
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('visualizar_item_estoque', item_id=item_id)
    
    try:
        item = ItemEstoque.objects.get(id=item_id)
    except ItemEstoque.DoesNotExist:
        messages.error(request, 'Item de estoque não encontrado.')
        return redirect('consultar_estoque')
    
    try:
        if 'foto_item' in request.FILES:
            arquivo = request.FILES['foto_item']
            print(f"Arquivo recebido: {arquivo.name}, Tamanho: {arquivo.size}, Tipo: {arquivo.content_type}")
            item.foto_item = arquivo
            item.save()
            print(f"Foto salva com sucesso: {item.foto_item.url if item.foto_item else 'N/A'}")
            messages.success(request, 'Foto do item atualizada com sucesso!')
        else:
            print("Nenhum arquivo encontrado em request.FILES")
            messages.error(request, 'Nenhum arquivo foi enviado.')
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Erro ao atualizar foto do item: {error_detail}")
        messages.error(request, f'Erro ao atualizar foto: {str(e)}')
    
    return redirect('visualizar_item_estoque', item_id=item_id)


def atualizar_documentacao_tecnica(request, item_id):
    """Atualizar documentação técnica do item de estoque"""
    from app.models import ItemEstoque
    
    print(f"=== ATUALIZAR DOCUMENTACAO TECNICA === Method: {request.method}, Item ID: {item_id}")
    print(f"POST data: {request.POST}")
    print(f"FILES data: {request.FILES}")
    
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('visualizar_item_estoque', item_id=item_id)
    
    try:
        item = ItemEstoque.objects.get(id=item_id)
    except ItemEstoque.DoesNotExist:
        messages.error(request, 'Item de estoque não encontrado.')
        return redirect('consultar_estoque')
    
    try:
        if 'documentacao_tecnica' in request.FILES:
            arquivo = request.FILES['documentacao_tecnica']
            print(f"Arquivo recebido: {arquivo.name}, Tamanho: {arquivo.size}, Tipo: {arquivo.content_type}")
            item.documentacao_tecnica = arquivo
            item.save()
            print(f"Documentação salva com sucesso: {item.documentacao_tecnica.url if item.documentacao_tecnica else 'N/A'}")
            messages.success(request, 'Documentação técnica atualizada com sucesso!')
        else:
            print("Nenhum arquivo encontrado em request.FILES")
            messages.error(request, 'Nenhum arquivo foi enviado.')
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Erro ao atualizar documentação técnica: {error_detail}")
        messages.error(request, f'Erro ao atualizar documentação: {str(e)}')
    
    return redirect('visualizar_item_estoque', item_id=item_id)


def atualizar_foto_detalhada(request, item_id):
    """Atualizar foto detalhada do item de estoque"""
    from app.models import ItemEstoque
    
    print(f"=== ATUALIZAR FOTO DETALHADA === Method: {request.method}, Item ID: {item_id}")
    print(f"POST data: {request.POST}")
    print(f"FILES data: {request.FILES}")
    
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('visualizar_item_estoque', item_id=item_id)
    
    try:
        item = ItemEstoque.objects.get(id=item_id)
    except ItemEstoque.DoesNotExist:
        messages.error(request, 'Item de estoque não encontrado.')
        return redirect('consultar_estoque')
    
    try:
        if 'foto_detalhada' in request.FILES:
            arquivo = request.FILES['foto_detalhada']
            print(f"Arquivo recebido: {arquivo.name}, Tamanho: {arquivo.size}, Tipo: {arquivo.content_type}")
            item.foto_detalhada = arquivo
            item.save()
            print(f"Foto detalhada salva com sucesso: {item.foto_detalhada.url if item.foto_detalhada else 'N/A'}")
            messages.success(request, 'Foto detalhada atualizada com sucesso!')
        else:
            print("Nenhum arquivo encontrado em request.FILES")
            messages.error(request, 'Nenhum arquivo foi enviado.')
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Erro ao atualizar foto detalhada: {error_detail}")
        messages.error(request, f'Erro ao atualizar foto: {str(e)}')
    
    return redirect('visualizar_item_estoque', item_id=item_id)