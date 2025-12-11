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
    """Home page view - Data filtered by current week from Semana52"""
    from app.models import OrdemServicoCorretiva, RequisicaoAlmoxarifado, Semana52, Maquina, Manutentor
    from datetime import datetime, timedelta, date
    from django.db.models import Sum, Count, Q
    from decimal import Decimal
    
    hoje = date.today()
    
    # Encontrar a semana atual baseada na data de hoje
    semana_atual = None
    try:
        # Buscar semana onde hoje está entre inicio e fim
        semana_atual = Semana52.objects.filter(
            inicio__lte=hoje,
            fim__gte=hoje
        ).first()
        
        # Se não encontrou, buscar a semana mais próxima
        if not semana_atual:
            # Tentar encontrar semana onde inicio é mais próximo de hoje (mas não futuro)
            semana_atual = Semana52.objects.filter(
                inicio__lte=hoje
            ).order_by('-inicio').first()
        
        # Se ainda não encontrou, buscar qualquer semana futura próxima
        if not semana_atual:
            semana_atual = Semana52.objects.filter(
                inicio__gte=hoje
            ).order_by('inicio').first()
    except Exception as e:
        print(f"Erro ao buscar semana atual: {e}")
        semana_atual = None
    
    # Definir intervalo de datas para filtros
    data_inicio_semana = None
    data_fim_semana = None
    mes_ano_grafico = None
    
    if semana_atual and semana_atual.inicio and semana_atual.fim:
        data_inicio_semana = semana_atual.inicio
        data_fim_semana = semana_atual.fim
        # Usar o mês da semana atual para o gráfico
        mes_ano_grafico = f"{data_inicio_semana.year}-{str(data_inicio_semana.month).zfill(2)}"
    else:
        # Fallback: usar mês atual se não houver semana definida
        mes_ano_grafico = f"{hoje.year}-{str(hoje.month).zfill(2)}"
        # Usar início e fim do mês atual como fallback
        from calendar import monthrange
        ultimo_dia = monthrange(hoje.year, hoje.month)[1]
        data_inicio_semana = date(hoje.year, hoje.month, 1)
        data_fim_semana = date(hoje.year, hoje.month, ultimo_dia)
    
    # ========== KPIs BASEADOS NA SEMANA ATUAL ==========
    
    # 1. Manutenções Corretivas na semana atual
    manutencoes_corretivas = 0
    if data_inicio_semana and data_fim_semana:
        try:
            ordens_semana = OrdemServicoCorretiva.objects.exclude(
                dt_entrada__isnull=True
            ).exclude(dt_entrada='')
            
            # Filtrar por data (precisa parsear dt_entrada que é string)
            for ordem in ordens_semana:
                try:
                    dt_str = ordem.dt_entrada.strip()
                    if ' ' in dt_str:
                        date_part = dt_str.split(' ')[0]
                    else:
                        date_part = dt_str
                    
                    if '/' in date_part:
                        parts = date_part.split('/')
                        if len(parts) == 3:
                            day, month, year = parts
                            ordem_date = date(int(year), int(month), int(day))
                            if data_inicio_semana <= ordem_date <= data_fim_semana:
                                manutencoes_corretivas += 1
                except:
                    continue
        except Exception as e:
            print(f"Erro ao contar manutenções corretivas: {e}")
    
    # 2. Manutenções Preventivas (usar MeuPlanoPreventiva se disponível)
    try:
        from app.models import MeuPlanoPreventiva
        if data_inicio_semana and data_fim_semana:
            # Contar planos preventivos com ações na semana atual
            manutencoes_preventivas = MeuPlanoPreventiva.objects.filter(
                data_planejada__gte=data_inicio_semana,
                data_planejada__lte=data_fim_semana
            ).count()
        else:
            manutencoes_preventivas = MeuPlanoPreventiva.objects.count()
    except:
        manutencoes_preventivas = 0
    
    # 3. Requisições de Almoxarifado na semana atual
    if data_inicio_semana and data_fim_semana:
        requisicoes_semana = RequisicaoAlmoxarifado.objects.filter(
            data_requisicao__gte=data_inicio_semana,
            data_requisicao__lte=data_fim_semana
        )
        total_requisicoes_semana = requisicoes_semana.count()
        valor_total_semana = requisicoes_semana.aggregate(
            total=Sum('vlr_movto_estoq')
        )['total'] or Decimal('0')
    else:
        total_requisicoes_semana = RequisicaoAlmoxarifado.objects.count()
        valor_total_semana = Decimal('0')
    
    # 4. Máquinas e Manutentores (total geral, não filtrado por semana)
    total_maquinas = Maquina.objects.count()
    total_manutentores = Manutentor.objects.count()
    
    # 5. Calendário - eventos na semana atual
    eventos = []
    if data_inicio_semana and data_fim_semana:
        # Buscar ordens de serviço na semana atual
        ordens = OrdemServicoCorretiva.objects.exclude(
            dt_entrada__isnull=True
        ).exclude(dt_entrada='')
        
        for ordem in ordens:
            try:
                dt_str = ordem.dt_entrada.strip()
                if ' ' in dt_str:
                    date_part = dt_str.split(' ')[0]
                else:
                    date_part = dt_str
                
                if '/' in date_part:
                    parts = date_part.split('/')
                    if len(parts) == 3:
                        day, month, year = parts
                        ordem_date = date(int(year), int(month), int(day))
                        
                        # Incluir apenas eventos dentro da semana atual
                        if data_inicio_semana <= ordem_date <= data_fim_semana:
                            start_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                            eventos.append({
                                'title': f'OS {ordem.cd_ordemserv} - {ordem.descr_maquina[:30] if ordem.descr_maquina else "Sem descrição"}',
                                'start': start_date,
                                'color': '#3788d8',  # Azul
                                'url': f'/manutencao-corretiva/consultar/?search={ordem.cd_ordemserv}'
                            })
            except:
                continue
        
        # Adicionar eventos de manutenção preventiva na semana atual
        try:
            from app.models import MeuPlanoPreventiva
            preventivas_semana = MeuPlanoPreventiva.objects.filter(
                data_planejada__gte=data_inicio_semana,
                data_planejada__lte=data_fim_semana
            )
            for preventiva in preventivas_semana:
                eventos.append({
                    'title': f'Preventiva - {preventiva.cd_maquina.cd_maquina if preventiva.cd_maquina else "N/A"}',
                    'start': preventiva.data_planejada.strftime('%Y-%m-%d'),
                    'color': '#28a745',  # Verde
                    'url': f'/planejamento/meu-plano/?search={preventiva.cd_maquina.cd_maquina if preventiva.cd_maquina else ""}'
                })
        except:
            pass
        
        # Adicionar eventos de Manutenção Terceiro na semana atual
        try:
            from app.models import ManutencaoTerceiro
            manutencoes_terceiro_semana = ManutencaoTerceiro.objects.filter(
                data__date__gte=data_inicio_semana,
                data__date__lte=data_fim_semana
            )
            for manutencao in manutencoes_terceiro_semana:
                if manutencao.data:
                    eventos.append({
                        'title': f'Manutenção Terceiro - {manutencao.titulo[:30]}',
                        'start': manutencao.data.strftime('%Y-%m-%d'),
                        'color': '#ff9800',  # Laranja
                        'url': '/manutencao-terceiro/consultar/'
                    })
        except Exception as e:
            print(f"Erro ao adicionar eventos de Manutenção Terceiro: {e}")
        
        # Adicionar eventos de Visitas na semana atual
        try:
            from app.models import Visitas
            visitas_semana = Visitas.objects.filter(
                data__date__gte=data_inicio_semana,
                data__date__lte=data_fim_semana
            )
            for visita in visitas_semana:
                if visita.data:
                    eventos.append({
                        'title': f'Visita - {visita.titulo[:30]}',
                        'start': visita.data.strftime('%Y-%m-%d'),
                        'color': '#9c27b0',  # Roxo
                        'url': '/visitas/consultar/'
                    })
        except Exception as e:
            print(f"Erro ao adicionar eventos de Visitas: {e}")
    
    # ========== GRÁFICO: ORDENS FECHADAS NA SEMANA ATUAL ==========
    ordens_fechadas_labels = []
    ordens_fechadas_data = []
    
    def parse_date_from_string(date_str):
        """
        Tenta fazer parse de uma data em vários formatos diferentes.
        Retorna um objeto date ou None se não conseguir fazer parse.
        """
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        if not date_str:
            return None
        
        # Remover hora se existir (formato: "dd/mm/yyyy hh:mm" ou "dd/mm/yyyy hh:mm:ss")
        if ' ' in date_str:
            date_part = date_str.split(' ')[0]
        else:
            date_part = date_str
        
        # Tentar diferentes formatos de data
        date_formats = [
            '%d/%m/%Y',      # 26/09/2025
            '%d-%m-%Y',      # 26-09-2025
            '%d.%m.%Y',      # 26.09.2025
            '%Y-%m-%d',      # 2025-09-26
            '%Y/%m/%d',      # 2025/09/26
            '%d/%m/%y',      # 26/09/25
            '%d-%m-%y',      # 26-09-25
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_part, fmt).date()
            except (ValueError, TypeError):
                continue
        
        # Se nenhum formato funcionou, tentar parse manual para formato brasileiro comum
        if '/' in date_part:
            parts = date_part.split('/')
            if len(parts) == 3:
                try:
                    day, month, year = parts
                    # Se ano tem 2 dígitos, assumir 2000+
                    if len(year) == 2:
                        year = '20' + year
                    return date(int(year), int(month), int(day))
                except (ValueError, TypeError):
                    pass
        
        return None
    
    if data_inicio_semana and data_fim_semana:
        # Criar dicionário para contar ordens por dia
        from collections import defaultdict
        ordens_por_dia = defaultdict(int)
        
        # Buscar todas as ordens com dt_encordmanu preenchida
        ordens_fechadas = OrdemServicoCorretiva.objects.exclude(
            dt_encordmanu__isnull=True
        ).exclude(dt_encordmanu='')
        
        # Processar cada ordem e contar por dia
        for ordem in ordens_fechadas:
            try:
                # Usar função de parse melhorada
                ordem_date = parse_date_from_string(ordem.dt_encordmanu)
                
                if ordem_date:
                    # Debug: verificar se esta ordem específica está sendo processada
                    if ordem.cd_ordemserv == 7 or '07/12/2025' in str(ordem.dt_encordmanu):
                        print(f"DEBUG - Ordem {ordem.cd_ordemserv}:")
                        print(f"  dt_encordmanu original: {ordem.dt_encordmanu}")
                        print(f"  Data parseada: {ordem_date}")
                        print(f"  Semana atual: {data_inicio_semana} a {data_fim_semana}")
                        print(f"  Está na semana? {data_inicio_semana <= ordem_date <= data_fim_semana}")
                    
                    # Verificar se está na semana atual
                    if data_inicio_semana <= ordem_date <= data_fim_semana:
                        # Formatar data como chave (YYYY-MM-DD)
                        data_key = ordem_date.strftime('%Y-%m-%d')
                        ordens_por_dia[data_key] += 1
                    elif ordem.cd_ordemserv == 7 or '07/12/2025' in str(ordem.dt_encordmanu):
                        print(f"  Ordem {ordem.cd_ordemserv} NÃO está na semana atual!")
                        print(f"  Comparação: {data_inicio_semana} <= {ordem_date} <= {data_fim_semana}")
                else:
                    # Debug: se não conseguiu fazer parse
                    if ordem.cd_ordemserv == 7 or '07/12/2025' in str(ordem.dt_encordmanu):
                        print(f"DEBUG - Ordem {ordem.cd_ordemserv}: Não conseguiu fazer parse de '{ordem.dt_encordmanu}'")
            except Exception as e:
                # Log erro para debug, mas continuar processando outras ordens
                if ordem.cd_ordemserv == 7 or '07/12/2025' in str(ordem.dt_encordmanu):
                    print(f"Erro ao processar dt_encordmanu da ordem {ordem.cd_ordemserv}: {e}")
                    import traceback
                    traceback.print_exc()
                continue
        
        # Criar lista de todos os dias da semana
        from datetime import timedelta
        current_date = data_inicio_semana
        while current_date <= data_fim_semana:
            data_key = current_date.strftime('%Y-%m-%d')
            data_label = current_date.strftime('%d/%m')
            ordens_fechadas_labels.append(data_label)
            ordens_fechadas_data.append(ordens_por_dia.get(data_key, 0))
            current_date += timedelta(days=1)
    
    # Converter para JSON para o template
    import json
    # Garantir que sempre temos arrays válidos (mesmo que vazios)
    if not ordens_fechadas_labels:
        ordens_fechadas_labels = []
    if not ordens_fechadas_data:
        ordens_fechadas_data = []
    
    # Debug: imprimir dados calculados
    print(f"DEBUG - Gráfico Ordens Fechadas (usando dt_encordmanu):")
    print(f"  Data de hoje: {hoje}")
    print(f"  Semana: {semana_atual.semana if semana_atual else 'N/A'}")
    print(f"  Data início semana: {data_inicio_semana}, Data fim semana: {data_fim_semana}")
    print(f"  Total de ordens processadas: {ordens_fechadas.count()}")
    print(f"  Labels: {ordens_fechadas_labels}")
    print(f"  Data: {ordens_fechadas_data}")
    print(f"  Total de ordens fechadas na semana: {sum(ordens_fechadas_data)}")
    
    # Debug adicional: verificar se há ordens com dt_encordmanu = 07/12/2025
    # Tentar encontrar ordem com ID 7 ou com data 07/12/2025
    ordem_teste = OrdemServicoCorretiva.objects.filter(cd_ordemserv=7).first()
    if not ordem_teste:
        # Tentar encontrar qualquer ordem com essa data
        ordens_com_data = OrdemServicoCorretiva.objects.exclude(dt_encordmanu__isnull=True).exclude(dt_encordmanu='')
        for ordem in ordens_com_data:
            if '07/12/2025' in str(ordem.dt_encordmanu):
                ordem_teste = ordem
                break
    
    if ordem_teste:
        print(f"DEBUG - Ordem encontrada (ID: {ordem_teste.cd_ordemserv}):")
        print(f"  dt_encordmanu: {ordem_teste.dt_encordmanu}")
        ordem_date_teste = parse_date_from_string(ordem_teste.dt_encordmanu)
        print(f"  Data parseada: {ordem_date_teste}")
        if ordem_date_teste:
            print(f"  Está na semana atual ({data_inicio_semana} a {data_fim_semana})? {data_inicio_semana <= ordem_date_teste <= data_fim_semana if data_inicio_semana and data_fim_semana else 'N/A'}")
            # Verificar qual semana contém essa data
            semana_com_data = Semana52.objects.filter(
                inicio__lte=ordem_date_teste,
                fim__gte=ordem_date_teste
            ).first()
            if semana_com_data:
                print(f"  Esta data pertence à semana: {semana_com_data.semana} ({semana_com_data.inicio} a {semana_com_data.fim})")
            else:
                print(f"  Nenhuma semana encontrada que contenha esta data!")
    
    ordens_fechadas_labels_json = json.dumps(ordens_fechadas_labels)
    ordens_fechadas_data_json = json.dumps(ordens_fechadas_data)
    
    context = {
        'page_title': 'Home',
        'active_page': 'home',
        'eventos': eventos,
        'semana_atual': semana_atual,
        'data_inicio_semana': data_inicio_semana,
        'data_fim_semana': data_fim_semana,
        'mes_ano_grafico': mes_ano_grafico,
        # KPIs
        'manutencoes_corretivas': manutencoes_corretivas,
        'manutencoes_preventivas': manutencoes_preventivas,
        'total_requisicoes_semana': total_requisicoes_semana,
        'valor_total_semana': abs(valor_total_semana),  # Usar valor absoluto
        'total_maquinas': total_maquinas,
        'total_manutentores': total_manutentores,
        # Dados do gráfico de ordens fechadas
        'ordens_fechadas_labels': ordens_fechadas_labels_json,
        'ordens_fechadas_data': ordens_fechadas_data_json,
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


def analise_requisicoes(request):
    """Análise de requisições de almoxarifado"""
    from app.models import RequisicaoAlmoxarifado
    from decimal import Decimal
    from datetime import datetime, timedelta
    from django.db.models import Sum, Count, Q, Avg
    from collections import defaultdict
    import json
    from calendar import monthrange
    
    # Obter anos e meses disponíveis no banco de dados
    anos_disponiveis = RequisicaoAlmoxarifado.objects.values_list('data_requisicao__year', flat=True).distinct().order_by('-data_requisicao__year')
    meses_disponiveis = {}
    for ano in anos_disponiveis:
        meses = RequisicaoAlmoxarifado.objects.filter(data_requisicao__year=ano).values_list('data_requisicao__month', flat=True).distinct().order_by('data_requisicao__month')
        meses_disponiveis[ano] = list(meses)
    
    # Processar filtros
    data_inicio_str = request.GET.get('data_inicio', '').strip()
    data_fim_str = request.GET.get('data_fim', '').strip()
    ano_selecionado = request.GET.get('ano', '').strip()
    mes_selecionado = request.GET.get('mes', '').strip()
    
    # Debug: verificar se os filtros estão sendo recebidos
    # print(f"DEBUG - Filtros recebidos: data_inicio={data_inicio_str}, data_fim={data_fim_str}, ano={ano_selecionado}, mes={mes_selecionado}")
    
    # Construir queryset base com filtros
    queryset_base = RequisicaoAlmoxarifado.objects.all()
    
    # Prioridade: Se há filtro de intervalo de datas, usar apenas ele
    # Caso contrário, usar filtro de ano/mês
    tem_filtro_data_range = bool(data_inicio_str or data_fim_str)
    tem_filtro_ano_mes = bool(ano_selecionado)
    
    if tem_filtro_data_range:
        # Aplicar filtro de intervalo de datas
        if data_inicio_str:
            try:
                data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
                queryset_base = queryset_base.filter(data_requisicao__gte=data_inicio)
            except ValueError as e:
                # print(f"DEBUG - Erro ao parse data_inicio: {e}")
                pass
        
        if data_fim_str:
            try:
                data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
                queryset_base = queryset_base.filter(data_requisicao__lte=data_fim)
            except ValueError as e:
                # print(f"DEBUG - Erro ao parse data_fim: {e}")
                pass
    elif tem_filtro_ano_mes:
        # Aplicar filtro de ano/mês
        try:
            ano = int(ano_selecionado)
            queryset_base = queryset_base.filter(data_requisicao__year=ano)
            
            if mes_selecionado:
                try:
                    mes = int(mes_selecionado)
                    queryset_base = queryset_base.filter(data_requisicao__month=mes)
                except ValueError as e:
                    # print(f"DEBUG - Erro ao parse mes: {e}")
                    pass
        except ValueError as e:
            # print(f"DEBUG - Erro ao parse ano: {e}")
            pass
    
    # Debug: verificar quantos registros após filtro
    # total_antes = RequisicaoAlmoxarifado.objects.count()
    # total_depois = queryset_base.count()
    # print(f"DEBUG - Total antes: {total_antes}, Total depois: {total_depois}")
    
    # Estatísticas gerais (usando queryset filtrado)
    hoje = datetime.now().date()
    total_requisicoes = queryset_base.count()
    
    # Últimos 30 dias (apenas se não houver filtros de data)
    if not tem_filtro_data_range and not tem_filtro_ano_mes:
        data_30_dias_atras = hoje - timedelta(days=30)
        requisicoes_recentes = queryset_base.filter(
            data_requisicao__gte=data_30_dias_atras
        ).count()
    else:
        # Se há filtros, mostrar total filtrado
        requisicoes_recentes = total_requisicoes
    
    # Mês atual (apenas se não houver filtros de data)
    if not tem_filtro_data_range and not tem_filtro_ano_mes:
        primeiro_dia_mes = hoje.replace(day=1)
        requisicoes_mes_atual = queryset_base.filter(
            data_requisicao__gte=primeiro_dia_mes
        ).count()
    else:
        # Se há filtros, mostrar total filtrado
        requisicoes_mes_atual = total_requisicoes
    
    # Itens únicos
    itens_unicos = queryset_base.values('cd_item').distinct().count()
    
    # Centros de atividade únicos
    centros_unicos = queryset_base.exclude(
        cd_centro_ativ__isnull=True
    ).values('cd_centro_ativ').distinct().count()
    
    # Calcular valor total (vlr_movto_estoq já é o valor total da linha, não precisa multiplicar por quantidade)
    valor_total = Decimal('0.00')
    quantidade_total = Decimal('0.00')
    for req in queryset_base:
        if req.vlr_movto_estoq:
            # vlr_movto_estoq já representa o valor total da transação (pode ser negativo para saídas)
            valor_total += abs(req.vlr_movto_estoq)
        if req.qtde_movto_estoq:
            quantidade_total += abs(req.qtde_movto_estoq)
    
    # Valor médio por requisição
    valor_medio = valor_total / total_requisicoes if total_requisicoes > 0 else Decimal('0.00')
    
    # Evolução temporal (últimos 12 meses ou período filtrado)
    meses_labels = []
    meses_data = []
    meses_valor = []
    
    # Determinar período para evolução temporal
    if data_inicio_str and data_fim_str:
        try:
            periodo_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            periodo_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError:
            periodo_inicio = (hoje - timedelta(days=365)).replace(day=1)
            periodo_fim = hoje
    elif ano_selecionado:
        try:
            ano = int(ano_selecionado)
            periodo_inicio = datetime(ano, 1, 1).date()
            if mes_selecionado:
                try:
                    mes = int(mes_selecionado)
                    periodo_inicio = datetime(ano, mes, 1).date()
                    ultimo_dia = monthrange(ano, mes)[1]
                    periodo_fim = datetime(ano, mes, ultimo_dia).date()
                    if periodo_fim > hoje:
                        periodo_fim = hoje
                except ValueError:
                    periodo_fim = datetime(ano, 12, 31).date()
                    if periodo_fim > hoje:
                        periodo_fim = hoje
            else:
                periodo_fim = datetime(ano, 12, 31).date()
                if periodo_fim > hoje:
                    periodo_fim = hoje
        except ValueError:
            periodo_inicio = (hoje - timedelta(days=365)).replace(day=1)
            periodo_fim = hoje
    else:
        periodo_inicio = (hoje - timedelta(days=365)).replace(day=1)
        periodo_fim = hoje
    
    # Gerar meses do período
    data_atual = periodo_inicio.replace(day=1)
    while data_atual <= periodo_fim:
        # Calcular último dia do mês
        ultimo_dia_mes = monthrange(data_atual.year, data_atual.month)[1]
        fim_mes_calc = datetime(data_atual.year, data_atual.month, ultimo_dia_mes).date()
        fim_mes = fim_mes_calc if fim_mes_calc <= periodo_fim else periodo_fim
        
        count = queryset_base.filter(
            data_requisicao__gte=data_atual,
            data_requisicao__lte=fim_mes
        ).count()
        
        valor_mes = Decimal('0.00')
        for req in queryset_base.filter(
            data_requisicao__gte=data_atual,
            data_requisicao__lte=fim_mes
        ):
            if req.vlr_movto_estoq:
                valor_mes += abs(req.vlr_movto_estoq)
        
        meses_labels.append(data_atual.strftime('%b/%Y'))
        meses_data.append(count)
        meses_valor.append(float(valor_mes))
        
        # Próximo mês
        if data_atual.month == 12:
            data_atual = data_atual.replace(year=data_atual.year + 1, month=1, day=1)
        else:
            data_atual = data_atual.replace(month=data_atual.month + 1, day=1)
    
    # Top 10 itens mais requisitados (por quantidade)
    top_itens_qtd = queryset_base.exclude(
        qtde_movto_estoq__isnull=True
    ).values('cd_item', 'descr_item').annotate(
        total_qtd=Sum('qtde_movto_estoq')
    ).order_by('-total_qtd')[:10]
    
    top_itens_labels = []
    top_itens_data = []
    for item in top_itens_qtd:
        descr = item['descr_item'] or f"Item {item['cd_item']}"
        if len(descr) > 40:
            descr = descr[:37] + "..."
        top_itens_labels.append(f"{item['cd_item']} - {descr}")
        top_itens_data.append(abs(float(item['total_qtd'])))
    
    # Top 10 itens por valor
    top_itens_valor = []
    itens_valor_dict = defaultdict(lambda: Decimal('0.00'))
    
    for req in queryset_base.exclude(vlr_movto_estoq__isnull=True):
        if req.vlr_movto_estoq:
            # vlr_movto_estoq já representa o valor total da transação
            itens_valor_dict[req.cd_item] += abs(req.vlr_movto_estoq)
    
    # Ordenar e pegar top 10
    sorted_itens = sorted(itens_valor_dict.items(), key=lambda x: x[1], reverse=True)[:10]
    
    top_itens_valor_labels = []
    top_itens_valor_data = []
    for cd_item, valor in sorted_itens:
        req = queryset_base.filter(cd_item=cd_item).first()
        descr = req.descr_item if req and req.descr_item else f"Item {cd_item}"
        if len(descr) > 40:
            descr = descr[:37] + "..."
        top_itens_valor_labels.append(f"{cd_item} - {descr}")
        top_itens_valor_data.append(float(valor))
    
    # Distribuição por centro de atividade (top 10)
    centros_dict = defaultdict(lambda: {'count': 0, 'valor': Decimal('0.00')})
    
    for req in queryset_base.exclude(cd_centro_ativ__isnull=True):
        centros_dict[req.cd_centro_ativ]['count'] += 1
        if req.vlr_movto_estoq:
            # vlr_movto_estoq já representa o valor total da transação
            centros_dict[req.cd_centro_ativ]['valor'] += abs(req.vlr_movto_estoq)
    
    sorted_centros = sorted(centros_dict.items(), key=lambda x: x[1]['valor'], reverse=True)[:10]
    
    centros_labels = []
    centros_data_count = []
    centros_data_valor = []
    for centro_id, dados in sorted_centros:
        centros_labels.append(str(centro_id))
        centros_data_count.append(dados['count'])
        centros_data_valor.append(float(dados['valor']))
    
    # Distribuição por operação (top 10)
    operacoes_dict = defaultdict(lambda: {'count': 0, 'valor': Decimal('0.00')})
    
    for req in queryset_base.exclude(descr_operacao__isnull=True).exclude(descr_operacao=''):
        operacoes_dict[req.descr_operacao]['count'] += 1
        if req.vlr_movto_estoq:
            # vlr_movto_estoq já representa o valor total da transação
            operacoes_dict[req.descr_operacao]['valor'] += abs(req.vlr_movto_estoq)
    
    sorted_operacoes = sorted(operacoes_dict.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
    
    operacoes_labels = []
    operacoes_data = []
    for operacao, dados in sorted_operacoes:
        if len(operacao) > 30:
            operacao = operacao[:27] + "..."
        operacoes_labels.append(operacao)
        operacoes_data.append(dados['count'])
    
    # Requisições recentes (últimas 20)
    requisicoes_recentes_list = queryset_base.order_by('-data_requisicao', '-created_at')[:20]
    
    # Dados diários para o mês selecionado (para o gráfico de evolução diária)
    if ano_selecionado and mes_selecionado:
        try:
            ano = int(ano_selecionado)
            mes = int(mes_selecionado)
            primeiro_dia_mes_atual = datetime(ano, mes, 1).date()
            ultimo_dia_mes_atual = datetime(ano, mes, monthrange(ano, mes)[1]).date()
            if ultimo_dia_mes_atual > hoje:
                ultimo_dia_mes_atual = hoje
        except ValueError:
            primeiro_dia_mes_atual = hoje.replace(day=1)
            if hoje.month == 12:
                ultimo_dia_mes_atual = hoje.replace(year=hoje.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                ultimo_dia_mes_atual = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)
            if ultimo_dia_mes_atual > hoje:
                ultimo_dia_mes_atual = hoje
    else:
        primeiro_dia_mes_atual = hoje.replace(day=1)
        if hoje.month == 12:
            ultimo_dia_mes_atual = hoje.replace(year=hoje.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            ultimo_dia_mes_atual = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)
        if ultimo_dia_mes_atual > hoje:
            ultimo_dia_mes_atual = hoje
    
    dias_labels = []
    dias_data = []
    dias_valor = []
    
    for dia in range(1, ultimo_dia_mes_atual.day + 1):
        data_dia = primeiro_dia_mes_atual.replace(day=dia)
        count = queryset_base.filter(data_requisicao=data_dia).count()
        
        valor_dia = Decimal('0.00')
        for req in queryset_base.filter(data_requisicao=data_dia):
            if req.vlr_movto_estoq:
                # vlr_movto_estoq já representa o valor total da transação
                valor_dia += abs(req.vlr_movto_estoq)
        
        dias_labels.append(data_dia.strftime('%d/%m'))
        dias_data.append(count)
        dias_valor.append(float(valor_dia))
    
    # Determinar mês selecionado para o gráfico diário
    if ano_selecionado and mes_selecionado:
        mes_selecionado_grafico = f"{ano_selecionado}-{mes_selecionado.zfill(2)}"
    else:
        mes_selecionado_grafico = hoje.strftime('%Y-%m')
    
    # Nomes dos meses em português
    meses_nomes = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    
    # Meses do ano selecionado (se houver)
    meses_ano_selecionado = []
    if ano_selecionado:
        try:
            ano_int = int(ano_selecionado)
            meses_ano_selecionado = meses_disponiveis.get(ano_int, [])
        except ValueError:
            pass
    
    context = {
        'page_title': 'Análise de Requisições',
        'active_page': 'analise_requisicoes',
        'total_requisicoes': total_requisicoes,
        'requisicoes_recentes': requisicoes_recentes,
        'requisicoes_mes_atual': requisicoes_mes_atual,
        'itens_unicos': itens_unicos,
        'centros_unicos': centros_unicos,
        'valor_total': valor_total,
        'quantidade_total': quantidade_total,
        'valor_medio': valor_medio,
        'meses_labels': json.dumps(meses_labels),
        'meses_data': json.dumps(meses_data),
        'meses_valor': json.dumps(meses_valor),
        'dias_labels': json.dumps(dias_labels),
        'dias_data': json.dumps(dias_data),
        'dias_valor': json.dumps(dias_valor),
        'mes_selecionado': mes_selecionado_grafico,
        'top_itens_labels': json.dumps(top_itens_labels),
        'top_itens_data': json.dumps(top_itens_data),
        'top_itens_valor_labels': json.dumps(top_itens_valor_labels),
        'top_itens_valor_data': json.dumps(top_itens_valor_data),
        'centros_labels': json.dumps(centros_labels),
        'centros_data_count': json.dumps(centros_data_count),
        'centros_data_valor': json.dumps(centros_data_valor),
        'operacoes_labels': json.dumps(operacoes_labels),
        'operacoes_data': json.dumps(operacoes_data),
        'requisicoes_recentes_list': requisicoes_recentes_list,
        # Filtros
        'anos_disponiveis': list(anos_disponiveis),
        'meses_disponiveis': meses_disponiveis,
        'meses_nomes': meses_nomes,
        'meses_ano_selecionado': meses_ano_selecionado,
        'data_inicio': data_inicio_str,
        'data_fim': data_fim_str,
        'ano_selecionado': ano_selecionado,
        'mes_selecionado_filtro': mes_selecionado,
    }
    return render(request, 'orcamento/analise_requisicoes.html', context)


def api_meses_por_ano(request):
    """API endpoint para obter meses disponíveis para um ano específico"""
    from django.http import JsonResponse
    from app.models import RequisicaoAlmoxarifado
    
    if request.method != 'GET':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    ano = request.GET.get('ano')
    if not ano:
        return JsonResponse({'error': 'Parâmetro ano é obrigatório'}, status=400)
    
    try:
        ano_int = int(ano)
        meses = RequisicaoAlmoxarifado.objects.filter(
            data_requisicao__year=ano_int
        ).values_list('data_requisicao__month', flat=True).distinct().order_by('data_requisicao__month')
        
        meses_nomes = {
            1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
            5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
            9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }
        
        meses_list = []
        for mes_num in meses:
            meses_list.append({
                'value': mes_num,
                'label': meses_nomes[mes_num]
            })
        
        return JsonResponse({'meses': meses_list})
    except (ValueError, TypeError) as e:
        return JsonResponse({'error': f'Ano inválido: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Erro ao processar dados: {str(e)}'}, status=500)


def api_dados_diarios_requisicoes(request):
    """API endpoint para obter dados diários de requisições, manutenções terceiro e visitas para um mês específico"""
    from django.http import JsonResponse
    from calendar import monthrange
    from app.models import RequisicaoAlmoxarifado, ManutencaoTerceiro, Visitas
    from decimal import Decimal
    from datetime import datetime
    
    if request.method != 'GET':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    mes_ano = request.GET.get('mes_ano')  # Formato: YYYY-MM
    if not mes_ano:
        return JsonResponse({'error': 'Parâmetro mes_ano é obrigatório'}, status=400)
    
    try:
        year, month = map(int, mes_ano.split('-'))
        primeiro_dia = datetime(year, month, 1).date()
        
        # Calcular último dia do mês
        ultimo_dia_num = monthrange(year, month)[1]
        ultimo_dia = datetime(year, month, ultimo_dia_num).date()
        
        # Hoje para limitar se for o mês atual
        hoje = datetime.now().date()
        if primeiro_dia.year == hoje.year and primeiro_dia.month == hoje.month:
            ultimo_dia = hoje
        
        dias_labels = []
        dias_data = []  # Requisições
        dias_valor = []  # Valor das requisições
        dias_manutencao_terceiro = []  # Manutenções Terceiro
        dias_visitas = []  # Visitas
        
        for dia in range(1, ultimo_dia.day + 1):
            data_dia = primeiro_dia.replace(day=dia)
            
            # Requisições de Almoxarifado
            count = RequisicaoAlmoxarifado.objects.filter(data_requisicao=data_dia).count()
            valor_dia = Decimal('0.00')
            for req in RequisicaoAlmoxarifado.objects.filter(data_requisicao=data_dia):
                if req.vlr_movto_estoq:
                    valor_dia += abs(req.vlr_movto_estoq)
            
            # Manutenções Terceiro (filtrar por data, que é DateTimeField)
            manutencao_count = ManutencaoTerceiro.objects.filter(
                data__date=data_dia
            ).count()
            
            # Visitas (filtrar por data, que é DateTimeField)
            visitas_count = Visitas.objects.filter(
                data__date=data_dia
            ).count()
            
            dias_labels.append(data_dia.strftime('%d/%m'))
            dias_data.append(count)
            dias_valor.append(float(valor_dia))
            dias_manutencao_terceiro.append(manutencao_count)
            dias_visitas.append(visitas_count)
        
        return JsonResponse({
            'labels': dias_labels,
            'data': dias_data,
            'valor': dias_valor,
            'manutencao_terceiro': dias_manutencao_terceiro,
            'visitas': dias_visitas
        })
        
    except (ValueError, TypeError) as e:
        return JsonResponse({'error': f'Formato de data inválido: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Erro ao processar dados: {str(e)}'}, status=500)


def template_debug(request):
    """Debug view to show which template file is being used"""
    from django.template import loader
    import os
    
    try:
        template = loader.get_template('base.html')
        template_path = template.origin.name if hasattr(template.origin, 'name') else str(template.origin)
        template_exists = os.path.exists(template_path)
        file_size = os.path.getsize(template_path) if template_exists else 0
        file_modified = os.path.getmtime(template_path) if template_exists else None
        
        from datetime import datetime
        modified_str = datetime.fromtimestamp(file_modified).strftime('%Y-%m-%d %H:%M:%S') if file_modified else 'N/A'
        
        # Read first few lines of the file
        first_lines = []
        if template_exists:
            with open(template_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i < 10:
                        first_lines.append(line.strip())
                    else:
                        break
        
        context = {
            'template_path': template_path,
            'template_exists': template_exists,
            'file_size': file_size,
            'file_modified': modified_str,
            'first_lines': first_lines,
            'debug_mode': settings.DEBUG,
        }
        return render(request, 'debug_template.html', context)
    except Exception as e:
        return render(request, 'debug_template.html', {'error': str(e)})


def testes(request):
    """Página de testes - Hierarquia de Máquinas Primárias e Secundárias"""
    from app.models import Maquina, MaquinaPrimariaSecundaria
    import json
    
    # Buscar todas as máquinas primárias (descr_gerenc = "MÁQUINAS PRINCIPAL")
    maquinas_primarias = Maquina.objects.filter(
        descr_gerenc__iexact='MÁQUINAS PRINCIPAL'
    ).order_by('cd_maquina')
    
    # Buscar todos os relacionamentos
    relacionamentos = MaquinaPrimariaSecundaria.objects.select_related(
        'maquina_primaria', 'maquina_secundaria'
    ).order_by('maquina_primaria__cd_maquina', 'maquina_secundaria__cd_maquina')
    
    # Construir lista de nós no formato básico do OrgChartJS
    # Formato: { id: X, pid: Y, name: "..." }
    nodes = []
    
    # Adicionar máquinas primárias como nós raiz (sem pid)
    for maq_prim in maquinas_primarias:
        nodes.append({
            'id': maq_prim.id,
            'name': f"{maq_prim.cd_maquina} - {maq_prim.descr_maquina or 'Sem descrição'}"
        })
    
    # Adicionar máquinas secundárias como nós filhos (com pid)
    for rel in relacionamentos:
        maq_sec = rel.maquina_secundaria
        nodes.append({
            'id': maq_sec.id,
            'pid': rel.maquina_primaria.id,
            'name': f"{maq_sec.cd_maquina} - {maq_sec.descr_maquina or 'Sem descrição'}"
        })
    
    # Debug: imprimir informações
    print(f"Total de máquinas primárias: {maquinas_primarias.count()}")
    print(f"Total de relacionamentos: {relacionamentos.count()}")
    print(f"Total de nós criados: {len(nodes)}")
    
    # Serializar JSON
    try:
        dados_json_str = json.dumps(nodes, ensure_ascii=False, default=str)
    except Exception as e:
        print(f"Erro ao serializar JSON: {e}")
        dados_json_str = json.dumps([{
            'id': 0,
            'name': 'Erro ao processar dados'
        }], ensure_ascii=False)
    
    context = {
        'page_title': 'Testes - Hierarquia de Máquinas',
        'active_page': 'testes',
        'dados_json': dados_json_str,
        'total_primarias': maquinas_primarias.count(),
        'total_relacionamentos': relacionamentos.count()
    }
    return render(request, 'testes/testes.html', context)


def analise_plano_preventiva(request):
    """Análise de Plano Preventiva"""
    context = {
        'page_title': 'Análise de Plano Preventiva',
        'active_page': 'analise_plano_preventiva'
    }
    return render(request, 'analise/analise_plano_preventiva.html', context)


def analise_roteiro_plano_preventiva(request):
    """Análise de Roteiro e Plano de Preventiva - Encontrar relações baseadas em campos específicos"""
    from app.models import PlanoPreventiva, RoteiroPreventiva, MeuPlanoPreventiva, Maquina
    from django.core.paginator import Paginator
    from django.db import transaction
    from django.contrib import messages
    
    # Verificar se é uma ação de confirmação e salvamento
    if request.method == 'POST':
        # Debug: imprimir dados recebidos
        print(f"=== DEBUG CONFIRMAR RELAÇÃO ===")
        print(f"POST data: {request.POST}")
        print(f"POST keys: {list(request.POST.keys())}")
        print(f"confirmar_relacao in POST: {'confirmar_relacao' in request.POST}")
        
        if 'confirmar_todos' in request.POST:
            print(f"=== DEBUG CONFIRMAR TODOS ===")
            print(f"POST data: {request.POST}")
            print(f"POST keys: {list(request.POST.keys())}")
            # Bulk confirmation - confirm all pending relationships
            relacionamentos_confirmados = 0
            relacionamentos_erro = 0
            
            # Get all planos and roteiros
            planos = PlanoPreventiva.objects.all()
            roteiros = RoteiroPreventiva.objects.all()
            
            # Helper function to check if fields match (same as campos_correspondem)
            def campos_correspondem(plano, roteiro):
                if not plano.cd_maquina or not roteiro.cd_maquina:
                    return False
                if plano.cd_maquina != roteiro.cd_maquina:
                    return False
                
                descr_plano = (plano.descr_maquina or '').strip().upper()
                descr_roteiro = (roteiro.descr_maquina or '').strip().upper()
                if descr_plano and descr_roteiro:
                    if descr_plano != descr_roteiro:
                        return False
                elif descr_plano or descr_roteiro:
                    return False
                
                if not plano.sequencia_tarefa or not roteiro.cd_tarefamanu:
                    return False
                if plano.sequencia_tarefa != roteiro.cd_tarefamanu:
                    return False
                
                descr_tarefa_plano = (plano.descr_tarefa or '').strip().upper()
                descr_tarefa_roteiro = (roteiro.descr_tarefamanu or '').strip().upper()
                if descr_tarefa_plano and descr_tarefa_roteiro:
                    if descr_tarefa_plano != descr_tarefa_roteiro:
                        return False
                elif descr_tarefa_plano or descr_tarefa_roteiro:
                    return False
                
                if not plano.sequencia_manutencao or not roteiro.seq_seqplamanu:
                    return False
                if plano.sequencia_manutencao != roteiro.seq_seqplamanu:
                    return False
                
                return True
            
            # Process all relationships
            with transaction.atomic():
                for plano in planos:
                    for roteiro in roteiros:
                        if campos_correspondem(plano, roteiro):
                            # Check if already saved
                            ja_existe = MeuPlanoPreventiva.objects.filter(
                                cd_maquina=plano.cd_maquina,
                                numero_plano=plano.numero_plano,
                                sequencia_manutencao=plano.sequencia_manutencao,
                                sequencia_tarefa=plano.sequencia_tarefa
                            ).exists()
                            
                            if not ja_existe:
                                try:
                                    meu_plano, created = MeuPlanoPreventiva.objects.get_or_create(
                                        cd_maquina=plano.cd_maquina,
                                        numero_plano=plano.numero_plano,
                                        sequencia_manutencao=plano.sequencia_manutencao,
                                        sequencia_tarefa=plano.sequencia_tarefa,
                                        defaults={
                                            'cd_unid': plano.cd_unid,
                                            'nome_unid': plano.nome_unid,
                                            'cd_setor': plano.cd_setor,
                                            'descr_setor': plano.descr_setor,
                                            'cd_atividade': plano.cd_atividade,
                                            'descr_maquina': plano.descr_maquina,
                                            'nro_patrimonio': plano.nro_patrimonio,
                                            'descr_plano': plano.descr_plano,
                                            'dt_execucao': plano.dt_execucao,
                                            'quantidade_periodo': plano.quantidade_periodo,
                                            'descr_tarefa': plano.descr_tarefa,
                                            'cd_funcionario': plano.cd_funcionario,
                                            'nome_funcionario': plano.nome_funcionario,
                                            'descr_seqplamanu': roteiro.descr_seqplamanu,
                                            'desc_detalhada_do_roteiro_preventiva': roteiro.descr_seqplamanu,
                                            'roteiro_preventiva': roteiro,
                                            'maquina': plano.maquina,
                                        }
                                    )
                                    
                                    if not created:
                                        meu_plano.desc_detalhada_do_roteiro_preventiva = roteiro.descr_seqplamanu
                                        meu_plano.descr_seqplamanu = roteiro.descr_seqplamanu
                                        meu_plano.roteiro_preventiva = roteiro
                                        meu_plano.cd_unid = plano.cd_unid
                                        meu_plano.nome_unid = plano.nome_unid
                                        meu_plano.cd_setor = plano.cd_setor
                                        meu_plano.descr_setor = plano.descr_setor
                                        meu_plano.cd_atividade = plano.cd_atividade
                                        meu_plano.descr_maquina = plano.descr_maquina
                                        meu_plano.nro_patrimonio = plano.nro_patrimonio
                                        meu_plano.descr_plano = plano.descr_plano
                                        meu_plano.dt_execucao = plano.dt_execucao
                                        meu_plano.quantidade_periodo = plano.quantidade_periodo
                                        meu_plano.descr_tarefa = plano.descr_tarefa
                                        meu_plano.cd_funcionario = plano.cd_funcionario
                                        meu_plano.nome_funcionario = plano.nome_funcionario
                                        meu_plano.maquina = plano.maquina
                                        meu_plano.save()
                                    
                                    relacionamentos_confirmados += 1
                                except Exception as e:
                                    relacionamentos_erro += 1
                                    print(f"Erro ao confirmar relação Plano {plano.id} - Roteiro {roteiro.id}: {str(e)}")
            
            if relacionamentos_confirmados > 0:
                messages.success(request, f'{relacionamentos_confirmados} relação(ões) confirmada(s) e salva(s) com sucesso!')
            if relacionamentos_erro > 0:
                messages.warning(request, f'{relacionamentos_erro} relação(ões) apresentaram erro ao salvar.')
            if relacionamentos_confirmados == 0 and relacionamentos_erro == 0:
                messages.info(request, 'Nenhuma relação pendente para confirmar.')
            
            return redirect('analise_roteiro_plano_preventiva')
        
        elif 'confirmar_relacao' in request.POST:
            plano_id = request.POST.get('plano_id')
            roteiro_id = request.POST.get('roteiro_id')
            
            print(f"plano_id: {plano_id}")
            print(f"roteiro_id: {roteiro_id}")
            
            if not plano_id or not roteiro_id:
                messages.error(request, 'Plano ID ou Roteiro ID não fornecido.')
                return redirect('analise_roteiro_plano_preventiva')
            
            try:
                plano = PlanoPreventiva.objects.get(id=plano_id)
                roteiro = RoteiroPreventiva.objects.get(id=roteiro_id)
                
                # Usar transaction.atomic para garantir integridade dos dados
                with transaction.atomic():
                    # Verificar se já existe um MeuPlanoPreventiva para esta combinação específica
                    # Usar uma combinação mais específica para evitar duplicatas
                    meu_plano, created = MeuPlanoPreventiva.objects.get_or_create(
                        cd_maquina=plano.cd_maquina,
                        numero_plano=plano.numero_plano,
                        sequencia_manutencao=plano.sequencia_manutencao,
                        sequencia_tarefa=plano.sequencia_tarefa,
                        defaults={
                            'cd_unid': plano.cd_unid,
                            'nome_unid': plano.nome_unid,
                            'cd_setor': plano.cd_setor,
                            'descr_setor': plano.descr_setor,
                            'cd_atividade': plano.cd_atividade,
                            'descr_maquina': plano.descr_maquina,
                            'nro_patrimonio': plano.nro_patrimonio,
                            'descr_plano': plano.descr_plano,
                            'dt_execucao': plano.dt_execucao,
                            'quantidade_periodo': plano.quantidade_periodo,
                            'descr_tarefa': plano.descr_tarefa,
                            'cd_funcionario': plano.cd_funcionario,
                            'nome_funcionario': plano.nome_funcionario,
                            'descr_seqplamanu': roteiro.descr_seqplamanu,
                            'desc_detalhada_do_roteiro_preventiva': roteiro.descr_seqplamanu,
                            'roteiro_preventiva': roteiro,
                            'maquina': plano.maquina,
                        }
                    )
                    
                    # Se já existia, atualizar com os dados do roteiro
                    if not created:
                        meu_plano.desc_detalhada_do_roteiro_preventiva = roteiro.descr_seqplamanu
                        meu_plano.descr_seqplamanu = roteiro.descr_seqplamanu
                        meu_plano.roteiro_preventiva = roteiro
                        # Atualizar outros campos que possam ter mudado
                        meu_plano.cd_unid = plano.cd_unid
                        meu_plano.nome_unid = plano.nome_unid
                        meu_plano.cd_setor = plano.cd_setor
                        meu_plano.descr_setor = plano.descr_setor
                        meu_plano.cd_atividade = plano.cd_atividade
                        meu_plano.descr_maquina = plano.descr_maquina
                        meu_plano.nro_patrimonio = plano.nro_patrimonio
                        meu_plano.descr_plano = plano.descr_plano
                        meu_plano.dt_execucao = plano.dt_execucao
                        meu_plano.quantidade_periodo = plano.quantidade_periodo
                        meu_plano.descr_tarefa = plano.descr_tarefa
                        meu_plano.cd_funcionario = plano.cd_funcionario
                        meu_plano.nome_funcionario = plano.nome_funcionario
                        meu_plano.maquina = plano.maquina
                        meu_plano.save()
                
                messages.success(request, f'Relação confirmada e salva com sucesso! Plano {plano.id} vinculado ao Roteiro {roteiro.id} em MeuPlanoPreventiva.')
                # Redirecionar para evitar reenvio do formulário
                return redirect('analise_roteiro_plano_preventiva')
            except PlanoPreventiva.DoesNotExist:
                messages.error(request, 'Plano não encontrado.')
                return redirect('analise_roteiro_plano_preventiva')
            except RoteiroPreventiva.DoesNotExist:
                messages.error(request, 'Roteiro não encontrado.')
                return redirect('analise_roteiro_plano_preventiva')
            except Exception as e:
                messages.error(request, f'Erro ao salvar relação: {str(e)}')
                import traceback
                print(f"Erro ao salvar relação: {traceback.format_exc()}")
                return redirect('analise_roteiro_plano_preventiva')
    
    # Buscar todos os registros
    planos = PlanoPreventiva.objects.all()
    roteiros = RoteiroPreventiva.objects.all()
    
    # Estatísticas gerais
    total_planos = planos.count()
    total_roteiros = roteiros.count()
    
    # Encontrar relacionamentos baseados em correspondência exata dos campos
    relacionamentos = []
    planos_sem_relacao = []
    roteiros_sem_relacao = []
    
    # Processar planos e encontrar relacionamentos
    planos_processados = set()
    roteiros_processados = set()
    
    def campos_correspondem(plano, roteiro):
        """Verifica se os campos principais correspondem exatamente"""
        # Comparar cd_maquina (ambos devem ter valor e serem iguais)
        if not plano.cd_maquina or not roteiro.cd_maquina:
            return False
        if plano.cd_maquina != roteiro.cd_maquina:
            return False
        
        # Comparar descr_maquina (ignorar case e espaços, mas ambos devem ter valor)
        descr_plano = (plano.descr_maquina or '').strip().upper()
        descr_roteiro = (roteiro.descr_maquina or '').strip().upper()
        if descr_plano and descr_roteiro:
            if descr_plano != descr_roteiro:
                return False
        elif descr_plano or descr_roteiro:
            # Se apenas um tem valor, não corresponde
            return False
        
        # Comparar sequencia_tarefa (Plano) com cd_tarefamanu (Roteiro)
        if not plano.sequencia_tarefa or not roteiro.cd_tarefamanu:
            return False
        if plano.sequencia_tarefa != roteiro.cd_tarefamanu:
            return False
        
        # Comparar descr_tarefa (Plano) com descr_tarefamanu (Roteiro) - ignorar case e espaços
        descr_tarefa_plano = (plano.descr_tarefa or '').strip().upper()
        descr_tarefa_roteiro = (roteiro.descr_tarefamanu or '').strip().upper()
        if descr_tarefa_plano and descr_tarefa_roteiro:
            if descr_tarefa_plano != descr_tarefa_roteiro:
                return False
        elif descr_tarefa_plano or descr_tarefa_roteiro:
            # Se apenas um tem valor, não corresponde
            return False
        
        # Comparar sequencia_manutencao (Plano) com seq_seqplamanu (Roteiro)
        if not plano.sequencia_manutencao or not roteiro.seq_seqplamanu:
            return False
        if plano.sequencia_manutencao != roteiro.seq_seqplamanu:
            return False
        
        return True
    
    # Função para calcular score parcial de match
    def calcular_score_parcial(plano, roteiro):
        """Calcula um score de correspondência parcial (0-100)"""
        score = 0
        total = 0
        
        # cd_maquina (peso 20)
        if plano.cd_maquina and roteiro.cd_maquina:
            total += 20
            if plano.cd_maquina == roteiro.cd_maquina:
                score += 20
        
        # descr_maquina (peso 20)
        descr_plano = (plano.descr_maquina or '').strip().upper()
        descr_roteiro = (roteiro.descr_maquina or '').strip().upper()
        if descr_plano and descr_roteiro:
            total += 20
            if descr_plano == descr_roteiro:
                score += 20
        
        # sequencia_tarefa vs cd_tarefamanu (peso 20)
        if plano.sequencia_tarefa and roteiro.cd_tarefamanu:
            total += 20
            if plano.sequencia_tarefa == roteiro.cd_tarefamanu:
                score += 20
        
        # descr_tarefa vs descr_tarefamanu (peso 20)
        descr_tarefa_plano = (plano.descr_tarefa or '').strip().upper()
        descr_tarefa_roteiro = (roteiro.descr_tarefamanu or '').strip().upper()
        if descr_tarefa_plano and descr_tarefa_roteiro:
            total += 20
            if descr_tarefa_plano == descr_tarefa_roteiro:
                score += 20
        
        # sequencia_manutencao vs seq_seqplamanu (peso 20)
        if plano.sequencia_manutencao and roteiro.seq_seqplamanu:
            total += 20
            if plano.sequencia_manutencao == roteiro.seq_seqplamanu:
                score += 20
        
        if total == 0:
            return 0
        return (score / total * 100)
    
    for plano in planos:
        melhor_match = None
        melhor_score = 0
        
        # Buscar roteiros que correspondem exatamente
        for roteiro in roteiros:
            if campos_correspondem(plano, roteiro):
                melhor_match = roteiro
                melhor_score = 100
                break
        
        if melhor_match:
            # Verificar se já foi salvo em MeuPlanoPreventiva
            # Usar a mesma combinação de campos usada no get_or_create
            ja_salvo = MeuPlanoPreventiva.objects.filter(
                cd_maquina=plano.cd_maquina,
                numero_plano=plano.numero_plano,
                sequencia_manutencao=plano.sequencia_manutencao,
                sequencia_tarefa=plano.sequencia_tarefa
            ).exists()
            
            relacionamentos.append({
                'plano': plano,
                'roteiro': melhor_match,
                'descr_seqplamanu': melhor_match.descr_seqplamanu,
                'ja_salvo': ja_salvo,
            })
            planos_processados.add(plano.id)
            roteiros_processados.add(melhor_match.id)
        else:
            # Encontrar melhor match parcial para exibição (sempre encontrar o melhor, mesmo que score < 40%)
            # Isso permite mostrar análise de erros mesmo quando não há match parcial bom
            melhor_match_parcial = None
            melhor_score_parcial = 0
            for roteiro in roteiros:
                if roteiro.id not in roteiros_processados:
                    score = calcular_score_parcial(plano, roteiro)
                    if score > melhor_score_parcial:  # Sempre encontrar o melhor, mesmo que baixo
                        melhor_score_parcial = score
                        melhor_match_parcial = roteiro
            
            planos_sem_relacao.append({
                'plano': plano,
                'melhor_match_parcial': melhor_match_parcial,
                'score_parcial': melhor_score_parcial,
            })
    
    # Encontrar roteiros sem plano correspondente
    for roteiro in roteiros:
        if roteiro.id not in roteiros_processados:
            # Encontrar melhor match parcial para exibição (sempre encontrar o melhor, mesmo que score < 40%)
            # Isso permite mostrar análise de erros mesmo quando não há match parcial bom
            melhor_match_parcial = None
            melhor_score_parcial = 0
            for plano in planos:
                if plano.id not in planos_processados:
                    score = calcular_score_parcial(plano, roteiro)
                    if score > melhor_score_parcial:  # Sempre encontrar o melhor, mesmo que baixo
                        melhor_score_parcial = score
                        melhor_match_parcial = plano
            
            roteiros_sem_relacao.append({
                'roteiro': roteiro,
                'melhor_match_parcial': melhor_match_parcial,
                'score_parcial': melhor_score_parcial,
            })
    
    # Filtros - Obter valores ANTES de aplicar
    filter_maquina = request.GET.get('filter_maquina', '').strip()
    filter_descr_seqplamanu = request.GET.get('filter_descr_seqplamanu', '').strip()
    filter_tipo = request.GET.get('filter_tipo', 'all')  # all, matched, planos_sem, roteiros_sem, salvos
    filter_status = request.GET.get('filter_status', 'all')  # all, pendentes, salvos
    
    # Aplicar filtros
    relacionamentos_filtrados = relacionamentos.copy()
    planos_sem_relacao_filtrados = planos_sem_relacao.copy()
    roteiros_sem_relacao_filtrados = roteiros_sem_relacao.copy()
    
    if filter_maquina:
        try:
            maquina_num = int(float(filter_maquina))
            relacionamentos_filtrados = [r for r in relacionamentos_filtrados if (r['plano'].cd_maquina and r['plano'].cd_maquina == maquina_num) or (r['roteiro'].cd_maquina and r['roteiro'].cd_maquina == maquina_num)]
            planos_sem_relacao_filtrados = [p for p in planos_sem_relacao_filtrados if p['plano'].cd_maquina and p['plano'].cd_maquina == maquina_num]
            roteiros_sem_relacao_filtrados = [r for r in roteiros_sem_relacao_filtrados if r['roteiro'].cd_maquina and r['roteiro'].cd_maquina == maquina_num]
        except (ValueError, TypeError):
            filter_maquina_str = str(filter_maquina).lower()
            relacionamentos_filtrados = [r for r in relacionamentos_filtrados if 
                (r['plano'].cd_maquina and filter_maquina_str in str(r['plano'].cd_maquina).lower()) or 
                (r['roteiro'].cd_maquina and filter_maquina_str in str(r['roteiro'].cd_maquina).lower()) or
                (r['plano'].descr_maquina and filter_maquina_str in str(r['plano'].descr_maquina).lower()) or
                (r['roteiro'].descr_maquina and filter_maquina_str in str(r['roteiro'].descr_maquina).lower())]
            planos_sem_relacao_filtrados = [p for p in planos_sem_relacao_filtrados if 
                (p['plano'].cd_maquina and filter_maquina_str in str(p['plano'].cd_maquina).lower()) or
                (p['plano'].descr_maquina and filter_maquina_str in str(p['plano'].descr_maquina).lower())]
            roteiros_sem_relacao_filtrados = [r for r in roteiros_sem_relacao_filtrados if 
                (r['roteiro'].cd_maquina and filter_maquina_str in str(r['roteiro'].cd_maquina).lower()) or
                (r['roteiro'].descr_maquina and filter_maquina_str in str(r['roteiro'].descr_maquina).lower())]
    
    if filter_descr_seqplamanu:
        filter_descr_str = filter_descr_seqplamanu.lower()
        relacionamentos_filtrados = [r for r in relacionamentos_filtrados if r.get('descr_seqplamanu') and filter_descr_str in r['descr_seqplamanu'].lower()]
    
    if filter_status == 'pendentes':
        relacionamentos_filtrados = [r for r in relacionamentos_filtrados if not r.get('ja_salvo', False)]
    elif filter_status == 'salvos':
        relacionamentos_filtrados = [r for r in relacionamentos_filtrados if r.get('ja_salvo', False)]
    
    # Estatísticas de relacionamentos APÓS filtros
    total_relacionamentos = len(relacionamentos_filtrados)
    total_planos_sem_relacao = len(planos_sem_relacao_filtrados)
    total_roteiros_sem_relacao = len(roteiros_sem_relacao_filtrados)
    total_salvos = sum(1 for rel in relacionamentos_filtrados if rel.get('ja_salvo', False))
    total_pendentes = total_relacionamentos - total_salvos
    
    # Paginação para relacionamentos - usar listas filtradas
    if filter_tipo == 'matched':
        items_to_paginate = relacionamentos_filtrados
    elif filter_tipo == 'planos_sem':
        items_to_paginate = planos_sem_relacao_filtrados
    elif filter_tipo == 'roteiros_sem':
        items_to_paginate = roteiros_sem_relacao_filtrados
    else:
        items_to_paginate = relacionamentos_filtrados
    
    paginator = Paginator(items_to_paginate, 50)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except:
        page_obj = paginator.get_page(1)
    
    # Preparar dados para o contexto baseado no tipo de filtro - usar listas filtradas
    if filter_tipo == 'matched':
        relacionamentos_display = list(page_obj)
        planos_sem_display = planos_sem_relacao_filtrados[:50]
        roteiros_sem_display = roteiros_sem_relacao_filtrados[:50]
    elif filter_tipo == 'planos_sem':
        relacionamentos_display = relacionamentos_filtrados[:50]
        planos_sem_display = list(page_obj)
        roteiros_sem_display = roteiros_sem_relacao_filtrados[:50]
    elif filter_tipo == 'roteiros_sem':
        relacionamentos_display = relacionamentos_filtrados[:50]
        planos_sem_display = planos_sem_relacao_filtrados[:50]
        roteiros_sem_display = list(page_obj)
    else:  # all
        relacionamentos_display = relacionamentos_filtrados[:100]
        planos_sem_display = planos_sem_relacao_filtrados[:100]
        roteiros_sem_display = roteiros_sem_relacao_filtrados[:100]
    
    context = {
        'page_title': 'Análise de Roteiro e Plano de Preventiva',
        'active_page': 'analise_roteiro_plano_preventiva',
        'relacionamentos': relacionamentos_display,
        'planos_sem_relacao': planos_sem_display,
        'roteiros_sem_relacao': roteiros_sem_display,
        'total_planos': total_planos,
        'total_roteiros': total_roteiros,
        'total_relacionamentos': total_relacionamentos,
        'total_planos_sem_relacao': total_planos_sem_relacao,
        'total_roteiros_sem_relacao': total_roteiros_sem_relacao,
        'total_salvos': total_salvos,
        'total_pendentes': total_pendentes,
        'filter_maquina': filter_maquina,
        'filter_descr_seqplamanu': filter_descr_seqplamanu,
        'filter_tipo': filter_tipo,
        'filter_status': filter_status,
        'page_obj': page_obj,
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
        
        elif 'remover_relacionamentos' in request.POST:
            # Remoção em lote
            relacionamento_ids = request.POST.getlist('relacionamento_ids')
            if relacionamento_ids:
                try:
                    relacionamentos = MaquinaPrimariaSecundaria.objects.filter(id__in=relacionamento_ids)
                    count = relacionamentos.count()
                    if count > 0:
                        relacionamentos.delete()
                        messages.success(request, f'{count} relacionamento(s) removido(s) com sucesso.')
                    else:
                        messages.warning(request, 'Nenhum relacionamento válido foi encontrado para remover.')
                except Exception as e:
                    messages.error(request, f'Erro ao remover relacionamentos: {str(e)}')
            else:
                messages.warning(request, 'Nenhum relacionamento foi selecionado para remover.')
        
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
        update_fields = []
        if not only_new_records:
            update_existing = request.POST.get('update_existing', 'off') == 'on'
            # Se update_existing estiver marcado, pegar lista de campos para atualizar
            if update_existing:
                update_fields = request.POST.getlist('update_fields')
                # Se nenhum campo foi selecionado, atualizar todos (comportamento padrão)
                if not update_fields:
                    update_fields = [
                        'cd_unid', 'nome_unid', 'cs_tt_maquina', 'descr_maquina',
                        'cd_setormanut', 'descr_setormanut', 'cd_priomaqutv',
                        'nro_patrimonio', 'cd_modelo', 'cd_grupo', 'cd_tpcentativ',
                        'descr_gerenc'
                    ]
        
        try:
            from app.utils import upload_maquinas_from_file
            
            # Fazer upload dos dados
            # Se only_new_records estiver marcado, update_existing será False (ignora duplicados)
            created_count, updated_count, errors = upload_maquinas_from_file(
                file, 
                update_existing=update_existing,
                update_fields=update_fields if update_existing else None
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
            return render(request, 'importar/importar_manutentor.html', context)
        
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
            return render(request, 'importar/importar_manutentor.html', context)
        
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
    return render(request, 'importar/importar_manutentor.html', context)


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
            return render(request, 'importar/importar_ordens_corretiva_outros.html', context)
        
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
            return render(request, 'importar/importar_ordens_corretiva_outros.html', context)
        
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
    return render(request, 'importar/importar_ordens_corretiva_outros.html', context)


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


def importar_52_semanas(request):
    """Importar 52 Semanas page view"""
    if request.method == 'POST':
        # Verificar se há arquivo enviado
        if 'file' not in request.FILES:
            messages.error(request, 'Por favor, selecione um arquivo para importar.')
            context = {
                'page_title': 'Importar 52 Semanas',
                'active_page': 'importar_52_semanas'
            }
            return render(request, 'importar/importar_52_semanas.html', context)
        
        file = request.FILES['file']
        
        # Validar extensão do arquivo
        allowed_extensions = ['.xlsx', '.xls', '.xlsm']
        file_extension = '.' + file.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            messages.error(
                request, 
                f'Formato de arquivo não suportado. Use: {", ".join(allowed_extensions)}'
            )
            context = {
                'page_title': 'Importar 52 Semanas',
                'active_page': 'importar_52_semanas'
            }
            return render(request, 'importar/importar_52_semanas.html', context)
        
        # Verificar se deve apenas adicionar novos registros (ignorar duplicados)
        only_new_records = request.POST.get('only_new_records', 'off') == 'on'
        
        # Verificar se deve atualizar registros existentes
        # Se only_new_records estiver marcado, update_existing será ignorado
        update_existing = False
        if not only_new_records:
            update_existing = request.POST.get('update_existing', 'off') == 'on'
        
        try:
            from app.utils import upload_52_semanas_from_file
            import traceback
            
            # Fazer upload dos dados
            # Se only_new_records estiver marcado, update_existing será False (ignora duplicados)
            created_count, updated_count, errors = upload_52_semanas_from_file(
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
                messages.success(request, f'{created_count} semana(s) criada(s) com sucesso!')
            if updated_count > 0:
                messages.info(request, f'{updated_count} semana(s) atualizada(s)!')
            if created_count == 0 and updated_count == 0 and not errors:
                messages.info(request, 'Nenhum registro novo foi importado. Todas as semanas já existem no banco de dados.')
            
        except Exception as e:
            error_msg = f'Erro ao importar arquivo: {str(e)}'
            messages.error(request, error_msg)
            # Log detalhado do erro para debug
            import traceback
            print(f"Erro ao importar 52 semanas: {error_msg}")
            traceback.print_exc()
    
    context = {
        'page_title': 'Importar 52 Semanas',
        'active_page': 'importar_52_semanas'
    }
    return render(request, 'importar/importar_52_semanas.html', context)


def importar_notas_fiscais(request):
    """Importar Notas Fiscais page view"""
    from app.utils import upload_notas_fiscais_from_file
    from django.contrib import messages
    
    if request.method == 'POST':
        # Verificar se há arquivo enviado
        if 'file' not in request.FILES:
            messages.error(request, 'Por favor, selecione um arquivo para importar.')
            context = {
                'page_title': 'Importar Notas Fiscais',
                'active_page': 'importar_notas_fiscais'
            }
            return render(request, 'importar/importar_notas_fiscais.html', context)
        
        file = request.FILES['file']
        update_existing = request.POST.get('update_existing') == 'on'
        only_new_records = request.POST.get('only_new_records') == 'on'
        
        # Se "only_new_records" estiver marcado, não atualizar existentes
        if only_new_records:
            update_existing = False
        
        # Processar arquivo
        try:
            created_count, updated_count, errors = upload_notas_fiscais_from_file(file, update_existing=update_existing)
            
            # Mensagens de sucesso
            if created_count > 0:
                messages.success(request, f'{created_count} nota(s) fiscal(is) importada(s) com sucesso!')
            if updated_count > 0:
                messages.info(request, f'{updated_count} nota(s) fiscal(is) atualizada(s).')
            if created_count == 0 and updated_count == 0:
                messages.warning(request, 'Nenhuma nota fiscal foi importada. Verifique se há novos registros no arquivo.')
            
            # Mensagens de erro
            if errors:
                for error in errors[:10]:  # Limitar a 10 erros para não sobrecarregar
                    messages.error(request, error)
                if len(errors) > 10:
                    messages.error(request, f'... e mais {len(errors) - 10} erro(s). Verifique o console para mais detalhes.')
        
        except Exception as e:
            messages.error(request, f'Erro ao processar arquivo: {str(e)}')
    
    context = {
        'page_title': 'Importar Notas Fiscais',
        'active_page': 'importar_notas_fiscais'
    }
    return render(request, 'importar/importar_notas_fiscais.html', context)


def importar_requisicoes_almoxarifado(request):
    """Importar Requisições Almoxarifado page view"""
    if request.method == 'POST':
        # Verificar se há arquivo enviado
        if 'file' not in request.FILES:
            messages.error(request, 'Por favor, selecione um arquivo para importar.')
            context = {
                'page_title': 'Importar Requisições Almoxarifado',
                'active_page': 'importar_requisicoes_almoxarifado'
            }
            return render(request, 'importar/importar_requisicoes_almoxaridado.html', context)
        
        file = request.FILES['file']
        use_file_name_date = request.POST.get('use_file_name_date') == 'on'
        data_requisicao_str = request.POST.get('data_requisicao')
        
        # Se usar data do nome do arquivo, extrair do nome
        if use_file_name_date:
            import re
            file_name = file.name
            # Remover extensão
            name_without_ext = file_name.replace('.csv', '').replace('.CSV', '')
            # Tentar padrão DD.MM.YYYY
            date_pattern = r'(\d{2})\.(\d{2})\.(\d{4})'
            match = re.search(date_pattern, name_without_ext)
            
            if match:
                day = match.group(1)
                month = match.group(2)
                year = match.group(3)
                data_requisicao_str = f"{year}-{month}-{day}"
            else:
                messages.error(request, f'Não foi possível extrair a data do nome do arquivo "{file_name}". O formato esperado é DD.MM.YYYY (ex: 01.11.2025.csv).')
                context = {
                    'page_title': 'Importar Requisições Almoxarifado',
                    'active_page': 'importar_requisicoes_almoxarifado'
                }
                return render(request, 'importar/importar_requisicoes_almoxaridado.html', context)
        
        # Verificar se há data da requisição
        if not data_requisicao_str:
            messages.error(request, 'Por favor, informe a data da requisição ou marque a opção para usar a data do nome do arquivo.')
            context = {
                'page_title': 'Importar Requisições Almoxarifado',
                'active_page': 'importar_requisicoes_almoxarifado'
            }
            return render(request, 'importar/importar_requisicoes_almoxaridado.html', context)
        
        # Validar extensão do arquivo
        allowed_extensions = ['.csv']
        file_extension = '.' + file.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            messages.error(
                request, 
                f'Formato de arquivo não suportado. Use: {", ".join(allowed_extensions)}'
            )
            context = {
                'page_title': 'Importar Requisições Almoxarifado',
                'active_page': 'importar_requisicoes_almoxarifado'
            }
            return render(request, 'importar/importar_requisicoes_almoxaridado.html', context)
        
        # Verificar se deve apenas adicionar novos registros (ignorar duplicados)
        only_new_records = request.POST.get('only_new_records', 'off') == 'on'
        
        # Verificar se deve atualizar registros existentes
        # Se only_new_records estiver marcado, update_existing será ignorado
        update_existing = False
        if not only_new_records:
            update_existing = request.POST.get('update_existing', 'off') == 'on'
        
        try:
            from app.utils import upload_requisicoes_almoxarifado_from_file
            from datetime import datetime
            
            # Converter data_requisicao_str para date
            try:
                data_requisicao = datetime.strptime(data_requisicao_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, f'Formato de data inválido: {data_requisicao_str}. Use YYYY-MM-DD')
                context = {
                    'page_title': 'Importar Requisições Almoxarifado',
                    'active_page': 'importar_requisicoes_almoxarifado'
                }
                return render(request, 'importar/importar_requisicoes_almoxaridado.html', context)
            
            # Fazer upload dos dados
            created_count, updated_count, errors = upload_requisicoes_almoxarifado_from_file(
                file, 
                data_requisicao=data_requisicao,
                update_existing=update_existing
            )
            
            # Preparar mensagens
            if errors:
                for error in errors[:10]:  # Mostrar apenas os primeiros 10 erros
                    messages.warning(request, error)
                if len(errors) > 10:
                    messages.warning(request, f'... e mais {len(errors) - 10} erros.')
            
            if created_count > 0:
                messages.success(request, f'{created_count} requisição(ões) criada(s) com sucesso para a data {data_requisicao.strftime("%d/%m/%Y")}!')
            if updated_count > 0:
                messages.info(request, f'{updated_count} requisição(ões) atualizada(s) para a data {data_requisicao.strftime("%d/%m/%Y")}!')
            if created_count == 0 and updated_count == 0 and not errors:
                messages.info(request, f'Nenhum registro novo foi importado para a data {data_requisicao.strftime("%d/%m/%Y")}. Todas as requisições já existem no banco de dados.')
            
        except Exception as e:
            error_msg = f'Erro ao importar arquivo: {str(e)}'
            messages.error(request, error_msg)
            # Log detalhado do erro para debug
            import traceback
            print(f"Erro ao importar requisições almoxarifado: {error_msg}")
            traceback.print_exc()
    
    context = {
        'page_title': 'Importar Requisições Almoxarifado',
        'active_page': 'importar_requisicoes_almoxarifado'
    }
    return render(request, 'importar/importar_requisicoes_almoxaridado.html', context)


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
    from app.models import CentroAtividade, Maquina, MaquinaPrimariaSecundaria
    import json
    
    try:
        centro_atividade = CentroAtividade.objects.get(id=ca_id)
    except CentroAtividade.DoesNotExist:
        messages.error(request, 'Centro de Atividade não encontrado.')
        return redirect('consultar_locais_e_cas')
    
    # Buscar máquinas relacionadas a este Centro de Atividade
    # Máquinas podem estar relacionadas através de:
    # 1. LocalCentroAtividade (local_centro_atividade__centro_atividade)
    # 2. cd_tpcentativ (campo direto na tabela Maquina que corresponde ao número do CA)
    from django.db.models import Q
    
    maquinas_do_ca = Maquina.objects.filter(
        Q(local_centro_atividade__centro_atividade=centro_atividade) |
        Q(cd_tpcentativ=centro_atividade.ca)
    ).distinct()
    
    print(f"DEBUG: Centro de Atividade CA={centro_atividade.ca}, ID={centro_atividade.id}")
    print(f"DEBUG: Total de máquinas encontradas no CA (via local_centro_atividade): {Maquina.objects.filter(local_centro_atividade__centro_atividade=centro_atividade).count()}")
    print(f"DEBUG: Total de máquinas encontradas no CA (via cd_tpcentativ={centro_atividade.ca}): {Maquina.objects.filter(cd_tpcentativ=centro_atividade.ca).count()}")
    print(f"DEBUG: Total de máquinas encontradas no CA (total combinado): {maquinas_do_ca.count()}")
    
    # Buscar máquinas primárias (descr_gerenc = "MÁQUINAS PRINCIPAL") relacionadas a este CA
    maquinas_primarias = maquinas_do_ca.filter(
        descr_gerenc__iexact='MÁQUINAS PRINCIPAL'
    ).order_by('cd_maquina')
    
    print(f"DEBUG: Máquinas primárias encontradas: {maquinas_primarias.count()}")
    if maquinas_primarias.exists():
        for mp in maquinas_primarias[:5]:  # Mostrar apenas as 5 primeiras para debug
            print(f"  - Máquina Primária: {mp.cd_maquina} - {mp.descr_maquina}")
    
    # Buscar relacionamentos entre máquinas primárias e secundárias para estas máquinas
    relacionamentos = MaquinaPrimariaSecundaria.objects.filter(
        maquina_primaria__in=maquinas_primarias
    ).select_related(
        'maquina_primaria', 'maquina_secundaria'
    ).order_by('maquina_primaria__cd_maquina', 'maquina_secundaria__cd_maquina')
    
    print(f"DEBUG: Relacionamentos encontrados: {relacionamentos.count()}")
    
    # Construir lista de nós no formato OrgChartJS
    nodes = []
    
    # Função auxiliar para construir URL da imagem
    def get_image_url(maquina):
        if maquina.foto:
            return request.build_absolute_uri(maquina.foto.url)
        return None
    
    # Adicionar máquinas primárias como nós raiz (sem pid)
    for maq_prim in maquinas_primarias:
        node_data = {
            'id': maq_prim.id,
            'field_0': maq_prim.descr_maquina or 'Sem descrição',
            'field_1': str(maq_prim.cd_maquina)
        }
        # Adicionar imagem se existir usando img_0
        foto_url = get_image_url(maq_prim)
        if foto_url:
            node_data['img_0'] = foto_url
        nodes.append(node_data)
    
    # Adicionar máquinas secundárias como nós filhos (com pid)
    for rel in relacionamentos:
        maq_sec = rel.maquina_secundaria
        node_data = {
            'id': maq_sec.id,
            'pid': rel.maquina_primaria.id,
            'field_0': maq_sec.descr_maquina or 'Sem descrição',
            'field_1': str(maq_sec.cd_maquina)
        }
        # Adicionar imagem se existir usando img_0
        foto_url = get_image_url(maq_sec)
        if foto_url:
            node_data['img_0'] = foto_url
        nodes.append(node_data)
    
    print(f"DEBUG: Total de nós criados: {len(nodes)}")
    if nodes:
        print(f"DEBUG: Primeiro nó: {nodes[0]}")
    
    # Serializar JSON
    try:
        dados_json_str = json.dumps(nodes, ensure_ascii=False, default=str)
    except Exception as e:
        print(f"Erro ao serializar JSON: {e}")
        dados_json_str = json.dumps([{
            'id': 0,
            'name': 'Erro ao processar dados'
        }], ensure_ascii=False)
    
    context = {
        'page_title': f'Visualizar CA {centro_atividade.ca}',
        'active_page': 'consultar_locais_e_cas',
        'ca': centro_atividade,
        'dados_json': dados_json_str,
        'total_primarias': maquinas_primarias.count(),
        'total_relacionamentos': relacionamentos.count(),
        'total_maquinas': maquinas_do_ca.count(),
        'has_maquinas': maquinas_do_ca.exists(),
        'has_primarias': maquinas_primarias.exists()
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
        locais__local__iexact='INDÚSTRIA'
    ).distinct().order_by('ca'))
    
    centros_frigorifico = list(CentroAtividade.objects.filter(
        locais__local__iexact='FRIGORÍFICO'
    ).distinct().order_by('ca'))
    
    # Preparar dados para o organograma (OrgChartJS)
    from app.models import MaquinaPrimariaSecundaria
    maquinas_primarias_org = Maquina.objects.filter(
        descr_gerenc__iexact='MÁQUINAS PRINCIPAL'
    ).order_by('cd_maquina')
    
    relacionamentos_org = MaquinaPrimariaSecundaria.objects.select_related(
        'maquina_primaria', 'maquina_secundaria'
    ).order_by('maquina_primaria__cd_maquina', 'maquina_secundaria__cd_maquina')
    
    # Construir lista de nós no formato do OrgChartJS
    nodes_org = []
    
    # Adicionar máquinas primárias como nós raiz (sem pid)
    for maq_prim in maquinas_primarias_org:
        nodes_org.append({
            'id': maq_prim.id,
            'name': f"{maq_prim.cd_maquina} - {maq_prim.descr_maquina or 'Sem descrição'}"
        })
    
    # Adicionar máquinas secundárias como nós filhos (com pid)
    for rel in relacionamentos_org:
        maq_sec = rel.maquina_secundaria
        nodes_org.append({
            'id': maq_sec.id,
            'pid': rel.maquina_primaria.id,
            'name': f"{maq_sec.cd_maquina} - {maq_sec.descr_maquina or 'Sem descrição'}"
        })
    
    # Serializar JSON para o organograma
    try:
        dados_json_org = json.dumps(nodes_org, ensure_ascii=False, default=str)
    except Exception as e:
        print(f"Erro ao serializar JSON do organograma: {e}")
        dados_json_org = json.dumps([{
            'id': 0,
            'name': 'Erro ao processar dados'
        }], ensure_ascii=False)
    
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
        # Dados para organograma
        'dados_json_org': dados_json_org,
        'total_primarias_org': maquinas_primarias_org.count(),
        'total_relacionamentos_org': relacionamentos_org.count(),
    }
    return render(request, 'analise/analise_maquinas.html', context)


def analise_maquinas_importadas(request):
    """Página de análise de máquinas importadas com gráficos e estatísticas"""
    from app.models import Maquina
    from django.db.models import Count
    from datetime import datetime, timedelta
    from collections import defaultdict
    import json
    
    # Estatísticas básicas - apenas máquinas importadas (com created_at)
    total_importadas = Maquina.objects.exclude(created_at__isnull=True).count()
    total_geral = Maquina.objects.count()
    percentual_importadas = (total_importadas / total_geral * 100) if total_geral > 0 else 0
    
    # Máquinas importadas recentes (últimas 30 dias)
    data_30_dias_atras = datetime.now() - timedelta(days=30)
    importadas_recentes = Maquina.objects.filter(created_at__gte=data_30_dias_atras).exclude(created_at__isnull=True).count()
    
    # Máquinas importadas do mês atual
    mes_atual = datetime.now().replace(day=1)
    importadas_mes_atual = Maquina.objects.filter(created_at__gte=mes_atual).exclude(created_at__isnull=True).count()
    
    # Máquinas importadas por setor
    maquinas_importadas_por_setor = Maquina.objects.exclude(
        created_at__isnull=True
    ).exclude(
        cd_setormanut__isnull=True
    ).exclude(
        cd_setormanut=''
    ).values('cd_setormanut').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    setores_labels = [str(item['cd_setormanut']) for item in maquinas_importadas_por_setor]
    setores_data = [item['total'] for item in maquinas_importadas_por_setor]
    
    # Máquinas importadas por unidade (top 10)
    maquinas_importadas_por_unidade = Maquina.objects.exclude(
        created_at__isnull=True
    ).exclude(
        nome_unid__isnull=True
    ).exclude(
        nome_unid=''
    ).values('nome_unid').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    unidades_labels = [item['nome_unid'][:30] for item in maquinas_importadas_por_unidade]
    unidades_data = [item['total'] for item in maquinas_importadas_por_unidade]
    
    # Máquinas importadas por mês (últimos 12 meses)
    maquinas_importadas_por_mes = defaultdict(int)
    maquinas_importadas = Maquina.objects.exclude(created_at__isnull=True).order_by('created_at')
    for maquina in maquinas_importadas:
        if maquina.created_at:
            mes_ano = maquina.created_at.strftime('%Y-%m')
            maquinas_importadas_por_mes[mes_ano] += 1
    
    # Ordenar por data e pegar últimos 12 meses
    meses_ordenados = sorted(maquinas_importadas_por_mes.keys())[-12:]
    meses_labels = [datetime.strptime(m, '%Y-%m').strftime('%b/%Y') for m in meses_ordenados]
    meses_data = [maquinas_importadas_por_mes[m] for m in meses_ordenados]
    
    # Máquinas importadas recentes para exibir na tabela
    maquinas_importadas_recentes = Maquina.objects.exclude(
        created_at__isnull=True
    ).order_by('-created_at')[:50]
    
    # Agrupar máquinas importadas por descr_gerenc
    from collections import defaultdict
    maquinas_por_gerencia = defaultdict(list)
    maquinas_importadas_gerencia = Maquina.objects.exclude(
        created_at__isnull=True
    ).exclude(
        descr_gerenc__isnull=True
    ).exclude(
        descr_gerenc=''
    ).order_by('descr_gerenc', 'cd_maquina')
    
    for maquina in maquinas_importadas_gerencia:
        gerencia = maquina.descr_gerenc or 'Sem Classificação'
        maquinas_por_gerencia[gerencia].append(maquina)
    
    # Converter para lista ordenada por nome da gerência
    maquinas_por_gerencia_list = sorted(
        maquinas_por_gerencia.items(),
        key=lambda x: x[0]
    )
    
    context = {
        'page_title': 'Análise de Máquinas Importadas',
        'active_page': 'analise_maquinas_importadas',
        'total_importadas': total_importadas,
        'importadas_recentes': importadas_recentes,
        'importadas_mes_atual': importadas_mes_atual,
        'percentual_importadas': round(percentual_importadas, 1),
        'maquinas_importadas_recentes': maquinas_importadas_recentes,
        'maquinas_por_gerencia': maquinas_por_gerencia_list,
        # Dados para gráficos (JSON)
        'setores_labels': json.dumps(setores_labels),
        'setores_data': json.dumps(setores_data),
        'unidades_labels': json.dumps(unidades_labels),
        'unidades_data': json.dumps(unidades_data),
        'meses_labels': json.dumps(meses_labels),
        'meses_data': json.dumps(meses_data),
    }
    return render(request, 'maquinas/analise_maquinas_importadas.html', context)


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


def consultar_meu_plano(request):
    """Consultar/listar Meus Planos Preventiva (MeuPlanoPreventiva)"""
    from app.models import MeuPlanoPreventiva
    
    # Buscar todos os meus planos preventiva
    planos_list = MeuPlanoPreventiva.objects.all().select_related('maquina', 'roteiro_preventiva')
    
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
            Q(descr_plano__icontains=search_query) |
            Q(desc_detalhada_do_roteiro_preventiva__icontains=search_query) |
            Q(descr_seqplamanu__icontains=search_query)
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
    
    filter_desc_detalhada = request.GET.get('filter_desc_detalhada', '').strip()
    if filter_desc_detalhada:
        planos_list = planos_list.filter(desc_detalhada_do_roteiro_preventiva__icontains=filter_desc_detalhada)
    
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
    total_count = MeuPlanoPreventiva.objects.count()
    maquinas_count = MeuPlanoPreventiva.objects.exclude(cd_maquina__isnull=True).values('cd_maquina').distinct().count()
    setores_count = MeuPlanoPreventiva.objects.exclude(cd_setor__isnull=True).exclude(cd_setor='').values('cd_setor').distinct().count()
    planos_com_roteiro = MeuPlanoPreventiva.objects.exclude(roteiro_preventiva__isnull=True).count()
    
    context = {
        'page_title': 'Consultar Meus Planos Preventiva',
        'active_page': 'consultar_meu_plano',
        'planos': planos,
        'total_count': total_count,
        'maquinas_count': maquinas_count,
        'setores_count': setores_count,
        'planos_com_roteiro': planos_com_roteiro,
        # Preservar filtros no contexto
        'search_query': search_query,
        'filter_maquina': filter_maquina,
        'filter_plano': filter_plano,
        'filter_seq_manutencao': filter_seq_manutencao,
        'filter_data': filter_data,
        'filter_periodo': filter_periodo,
        'filter_seq_tarefa': filter_seq_tarefa,
        'filter_tarefa': filter_tarefa,
        'filter_desc_detalhada': filter_desc_detalhada,
        'filter_descr_seqplamanu': filter_descr_seqplamanu,
        'filter_funcionario': filter_funcionario,
        'filter_setor': filter_setor,
    }
    return render(request, 'consultar/consultar_meu_plano.html', context)


def consultar_requisicoes_almoxarifado(request):
    """Consultar/listar requisições de almoxarifado com filtros avançados"""
    from app.models import RequisicaoAlmoxarifado
    from decimal import Decimal
    
    # Busca geral
    search_query = request.GET.get('search', '').strip()
    requisicoes_list = RequisicaoAlmoxarifado.objects.all()
    
    # Aplicar busca geral
    if search_query:
        requisicoes_list = requisicoes_list.filter(
            Q(cd_item__icontains=search_query) |
            Q(descr_item__icontains=search_query) |
            Q(cd_centro_ativ__icontains=search_query) |
            Q(cd_usu_criou__icontains=search_query) |
            Q(cd_usu_atend__icontains=search_query) |
            Q(descr_operacao__icontains=search_query) |
            Q(descr_local_fisic__icontains=search_query)
        )
    
    # Filtros específicos
    filter_data = request.GET.get('filter_data', '').strip()
    if filter_data:
        try:
            from datetime import datetime
            data_obj = datetime.strptime(filter_data, '%Y-%m-%d').date()
            requisicoes_list = requisicoes_list.filter(data_requisicao=data_obj)
        except ValueError:
            requisicoes_list = requisicoes_list.filter(data_requisicao__icontains=filter_data)
    
    filter_item = request.GET.get('filter_item', '').strip()
    if filter_item:
        try:
            item_num = int(float(filter_item))
            requisicoes_list = requisicoes_list.filter(cd_item=item_num)
        except (ValueError, TypeError):
            requisicoes_list = requisicoes_list.filter(cd_item__icontains=filter_item)
    
    filter_descricao = request.GET.get('filter_descricao', '').strip()
    if filter_descricao:
        requisicoes_list = requisicoes_list.filter(descr_item__icontains=filter_descricao)
    
    filter_quantidade = request.GET.get('filter_quantidade', '').strip()
    if filter_quantidade:
        try:
            qtd_num = Decimal(filter_quantidade)
            requisicoes_list = requisicoes_list.filter(qtde_movto_estoq=qtd_num)
        except (ValueError, TypeError):
            requisicoes_list = requisicoes_list.filter(qtde_movto_estoq__icontains=filter_quantidade)
    
    filter_valor = request.GET.get('filter_valor', '').strip()
    if filter_valor:
        try:
            valor_num = Decimal(filter_valor)
            requisicoes_list = requisicoes_list.filter(vlr_movto_estoq=valor_num)
        except (ValueError, TypeError):
            requisicoes_list = requisicoes_list.filter(vlr_movto_estoq__icontains=filter_valor)
    
    filter_centro = request.GET.get('filter_centro', '').strip()
    if filter_centro:
        try:
            centro_num = int(float(filter_centro))
            requisicoes_list = requisicoes_list.filter(cd_centro_ativ=centro_num)
        except (ValueError, TypeError):
            requisicoes_list = requisicoes_list.filter(cd_centro_ativ__icontains=filter_centro)
    
    filter_usuario_criou = request.GET.get('filter_usuario_criou', '').strip()
    if filter_usuario_criou:
        requisicoes_list = requisicoes_list.filter(cd_usu_criou__icontains=filter_usuario_criou)
    
    filter_usuario_atend = request.GET.get('filter_usuario_atend', '').strip()
    if filter_usuario_atend:
        requisicoes_list = requisicoes_list.filter(cd_usu_atend__icontains=filter_usuario_atend)
    
    filter_operacao = request.GET.get('filter_operacao', '').strip()
    if filter_operacao:
        requisicoes_list = requisicoes_list.filter(descr_operacao__icontains=filter_operacao)
    
    filter_local = request.GET.get('filter_local', '').strip()
    if filter_local:
        requisicoes_list = requisicoes_list.filter(descr_local_fisic__icontains=filter_local)
    
    # Ordenar por data de requisição (mais recente primeiro) e código do item
    requisicoes_list = requisicoes_list.order_by('-data_requisicao', 'cd_item')
    
    # Paginação
    paginator = Paginator(requisicoes_list, 100)  # 100 itens por página
    page_number = request.GET.get('page', 1)
    requisicoes = paginator.get_page(page_number)
    
    # Estatísticas
    total_count = RequisicaoAlmoxarifado.objects.count()
    itens_count = RequisicaoAlmoxarifado.objects.values('cd_item').distinct().count()
    centros_count = RequisicaoAlmoxarifado.objects.exclude(cd_centro_ativ__isnull=True).values('cd_centro_ativ').distinct().count()
    
    # Calcular valor total (soma de quantidade * valor, usando valores absolutos)
    valor_total = Decimal('0.00')
    for req in RequisicaoAlmoxarifado.objects.all():
        if req.qtde_movto_estoq and req.vlr_movto_estoq:
            # Usar valor absoluto da quantidade (já que geralmente é negativa para saída)
            qtd_abs = abs(req.qtde_movto_estoq)
            valor_total += qtd_abs * abs(req.vlr_movto_estoq)
    
    context = {
        'page_title': 'Consultar Requisições Almoxarifado',
        'active_page': 'consultar_requisicoes_almoxarifado',
        'requisicoes': requisicoes,
        'total_count': total_count,
        'itens_count': itens_count,
        'centros_count': centros_count,
        'valor_total': valor_total,
        # Preservar filtros no contexto
        'search_query': search_query,
        'filter_data': filter_data,
        'filter_item': filter_item,
        'filter_descricao': filter_descricao,
        'filter_quantidade': filter_quantidade,
        'filter_valor': filter_valor,
        'filter_centro': filter_centro,
        'filter_usuario_criou': filter_usuario_criou,
        'filter_usuario_atend': filter_usuario_atend,
        'filter_operacao': filter_operacao,
        'filter_local': filter_local,
    }
    return render(request, 'consultar/consultar_requisicoes_almoxarifado.html', context)


def consultar_52_semanas(request):
    """Consultar/listar Semanas 52"""
    from app.models import Semana52
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    # Buscar todas as semanas
    semanas_list = Semana52.objects.all()
    
    # Filtro de busca geral
    search_query = request.GET.get('search', '').strip()
    if search_query:
        search_conditions = Q()
        
        # Para campos de texto, usar icontains
        search_conditions |= (
            Q(semana__icontains=search_query)
        )
        
        # Tentar buscar por data
        try:
            from datetime import datetime
            # Tentar diferentes formatos de data
            search_date = datetime.strptime(search_query, '%d/%m/%Y').date()
            search_conditions |= Q(inicio=search_date) | Q(fim=search_date)
        except (ValueError, TypeError):
            try:
                search_date = datetime.strptime(search_query, '%Y-%m-%d').date()
                search_conditions |= Q(inicio=search_date) | Q(fim=search_date)
            except (ValueError, TypeError):
                pass
        
        semanas_list = semanas_list.filter(search_conditions)
    
    # Filtros por coluna individual
    filter_semana = request.GET.get('filter_semana', '').strip()
    if filter_semana:
        semanas_list = semanas_list.filter(semana__icontains=filter_semana)
    
    filter_inicio = request.GET.get('filter_inicio', '').strip()
    if filter_inicio:
        # Tentar converter para data
        try:
            from datetime import datetime
            inicio_date = datetime.strptime(filter_inicio, '%d/%m/%Y').date()
            semanas_list = semanas_list.filter(inicio=inicio_date)
        except (ValueError, TypeError):
            # Se não for data válida, buscar como string na representação da data
            semanas_list = semanas_list.filter(inicio__icontains=filter_inicio)
    
    filter_fim = request.GET.get('filter_fim', '').strip()
    if filter_fim:
        # Tentar converter para data
        try:
            from datetime import datetime
            fim_date = datetime.strptime(filter_fim, '%d/%m/%Y').date()
            semanas_list = semanas_list.filter(fim=fim_date)
        except (ValueError, TypeError):
            # Se não for data válida, buscar como string na representação da data
            semanas_list = semanas_list.filter(fim__icontains=filter_fim)
    
    # Ordenar por data de início
    semanas_list = semanas_list.order_by('inicio', 'semana')
    
    # Adicionar campo calculado de duração
    from datetime import timedelta
    semanas_com_duracao = []
    for semana in semanas_list:
        duracao_dias = None
        if semana.inicio and semana.fim:
            duracao_dias = (semana.fim - semana.inicio).days + 1
        semanas_com_duracao.append({
            'semana': semana,
            'duracao_dias': duracao_dias
        })
    
    # Paginação
    paginator = Paginator(semanas_com_duracao, 25)  # 25 itens por página
    page_number = request.GET.get('page', 1)
    try:
        semanas = paginator.page(page_number)
    except:
        semanas = paginator.page(1)
    
    # Estatísticas
    total_count = Semana52.objects.count()
    
    context = {
        'page_title': 'Consultar 52 Semanas',
        'active_page': 'consultar_52_semanas',
        'semanas': semanas,
        'total_count': total_count,
        'search_query': search_query,
        'filter_semana': filter_semana,
        'filter_inicio': filter_inicio,
        'filter_fim': filter_fim,
    }
    return render(request, 'consultar/consultar_52_semanas.html', context)


def analise_geral_plano_preventiva_pcm(request):
    """Análise geral dos dados de Plano Preventiva PCM - Dashboard com estatísticas"""
    from app.models import (
        MeuPlanoPreventiva, PlanoPreventiva, RoteiroPreventiva,
        MaquinaPrimariaSecundaria, Maquina, MeuPlanoPreventivaDocumento, Semana52
    )
    from django.db.models import Count, Q
    from datetime import date, timedelta
    
    # ========== ESTATÍSTICAS MEU PLANO PREVENTIVA ==========
    total_meus_planos = MeuPlanoPreventiva.objects.count()
    meus_planos_com_roteiro = MeuPlanoPreventiva.objects.exclude(roteiro_preventiva__isnull=True).count()
    meus_planos_sem_roteiro = total_meus_planos - meus_planos_com_roteiro
    meus_planos_com_desc_detalhada = MeuPlanoPreventiva.objects.exclude(
        desc_detalhada_do_roteiro_preventiva__isnull=True
    ).exclude(desc_detalhada_do_roteiro_preventiva='').count()
    
    # Máquinas únicas em MeuPlanoPreventiva
    maquinas_unicas_meus_planos = MeuPlanoPreventiva.objects.exclude(
        cd_maquina__isnull=True
    ).values('cd_maquina').distinct().count()
    
    # Setores únicos
    setores_unicos_meus_planos = MeuPlanoPreventiva.objects.exclude(
        cd_setor__isnull=True
    ).exclude(cd_setor='').values('cd_setor').distinct().count()
    
    # Planos com documentos associados
    planos_com_documentos = MeuPlanoPreventiva.objects.filter(
        documentos_associados__isnull=False
    ).distinct().count()
    
    # ========== ESTATÍSTICAS ANÁLISE ROTEIRO/PLANO ==========
    total_planos = PlanoPreventiva.objects.count()
    total_roteiros = RoteiroPreventiva.objects.count()
    
    # Função para verificar correspondência exata
    def campos_correspondem(plano, roteiro):
        if not plano.cd_maquina or not roteiro.cd_maquina:
            return False
        if plano.cd_maquina != roteiro.cd_maquina:
            return False
        
        descr_plano = (plano.descr_maquina or '').strip().upper()
        descr_roteiro = (roteiro.descr_maquina or '').strip().upper()
        if descr_plano and descr_roteiro:
            if descr_plano != descr_roteiro:
                return False
        elif descr_plano or descr_roteiro:
            return False
        
        if not plano.sequencia_tarefa or not roteiro.cd_tarefamanu:
            return False
        if plano.sequencia_tarefa != roteiro.cd_tarefamanu:
            return False
        
        descr_tarefa_plano = (plano.descr_tarefa or '').strip().upper()
        descr_tarefa_roteiro = (roteiro.descr_tarefamanu or '').strip().upper()
        if descr_tarefa_plano and descr_tarefa_roteiro:
            if descr_tarefa_plano != descr_tarefa_roteiro:
                return False
        elif descr_tarefa_plano or descr_tarefa_roteiro:
            return False
        
        if not plano.sequencia_manutencao or not roteiro.seq_seqplamanu:
            return False
        if plano.sequencia_manutencao != roteiro.seq_seqplamanu:
            return False
        
        return True
    
    # Contar relacionamentos encontrados
    relacionamentos_encontrados = 0
    planos_processados = set()
    roteiros_processados = set()
    
    planos_list = PlanoPreventiva.objects.all()
    roteiros_list = RoteiroPreventiva.objects.all()
    
    for plano in planos_list:
        for roteiro in roteiros_list:
            if campos_correspondem(plano, roteiro):
                relacionamentos_encontrados += 1
                planos_processados.add(plano.id)
                roteiros_processados.add(roteiro.id)
                break
    
    planos_sem_relacao = total_planos - len(planos_processados)
    roteiros_sem_relacao = total_roteiros - len(roteiros_processados)
    
    # Relacionamentos já confirmados (salvos em MeuPlanoPreventiva)
    relacionamentos_confirmados = MeuPlanoPreventiva.objects.exclude(
        roteiro_preventiva__isnull=True
    ).count()
    
    relacionamentos_pendentes = max(0, relacionamentos_encontrados - relacionamentos_confirmados)
    
    # ========== ESTATÍSTICAS MÁQUINAS PRIMÁRIAS/SECUNDÁRIAS ==========
    maquinas_primarias_total = Maquina.objects.filter(
        descr_gerenc__iexact='MÁQUINAS PRINCIPAL'
    ).count()
    
    maquinas_secundarias_total = Maquina.objects.exclude(
        descr_gerenc__iexact='MÁQUINAS PRINCIPAL'
    ).count()
    
    relacionamentos_maquinas = MaquinaPrimariaSecundaria.objects.count()
    
    # Máquinas primárias que têm relacionamentos
    primarias_com_relacionamentos = MaquinaPrimariaSecundaria.objects.values(
        'maquina_primaria_id'
    ).distinct().count()
    
    # Máquinas secundárias relacionadas
    secundarias_relacionadas = MaquinaPrimariaSecundaria.objects.values(
        'maquina_secundaria_id'
    ).distinct().count()
    
    # Máquinas primárias sem relacionamentos
    primarias_sem_relacionamentos = maquinas_primarias_total - primarias_com_relacionamentos
    
    # Máquinas secundárias disponíveis (não relacionadas)
    secundarias_disponiveis = maquinas_secundarias_total - secundarias_relacionadas
    
    # ========== PERCENTUAIS E TAXAS ==========
    taxa_cobertura_planos = (relacionamentos_encontrados / total_planos * 100) if total_planos > 0 else 0
    taxa_cobertura_roteiros = (relacionamentos_encontrados / total_roteiros * 100) if total_roteiros > 0 else 0
    taxa_confirmacao = (relacionamentos_confirmados / relacionamentos_encontrados * 100) if relacionamentos_encontrados > 0 else 0
    
    taxa_meus_planos_com_roteiro = (meus_planos_com_roteiro / total_meus_planos * 100) if total_meus_planos > 0 else 0
    taxa_meus_planos_com_desc = (meus_planos_com_desc_detalhada / total_meus_planos * 100) if total_meus_planos > 0 else 0
    
    taxa_primarias_relacionadas = (primarias_com_relacionamentos / maquinas_primarias_total * 100) if maquinas_primarias_total > 0 else 0
    
    # ========== ESTATÍSTICAS SEMANA52 ==========
    total_semanas = Semana52.objects.count()
    semanas_com_dados = Semana52.objects.exclude(inicio__isnull=True).exclude(fim__isnull=True).count()
    
    # Semanas ordenadas por data de início
    semanas_ordenadas = Semana52.objects.exclude(inicio__isnull=True).order_by('inicio')
    
    # Calcular estatísticas de datas
    semanas_list = list(semanas_ordenadas)
    if semanas_list:
        primeira_semana = semanas_list[0]
        ultima_semana = semanas_list[-1]
        primeira_data = primeira_semana.inicio if primeira_semana else None
        ultima_data = ultima_semana.fim if ultima_semana else None
        
        # Calcular duração total em dias
        if primeira_data and ultima_data:
            duracao_total_dias = (ultima_data - primeira_data).days + 1
        else:
            duracao_total_dias = 0
        
        # Calcular média de duração por semana e adicionar duração a cada semana
        duracoes = []
        semanas_com_duracao = []
        # Processar todas as semanas para calcular média, mas limitar preview a 10
        for semana in semanas_list:
            duracao_semana = None
            if semana.inicio and semana.fim:
                duracao_semana = (semana.fim - semana.inicio).days + 1
                duracoes.append(duracao_semana)
            # Adicionar apenas as primeiras 10 para preview
            if len(semanas_com_duracao) < 10:
                semanas_com_duracao.append({
                    'semana': semana,
                    'duracao_dias': duracao_semana
                })
        
        duracao_media = sum(duracoes) / len(duracoes) if duracoes else 0
    else:
        primeira_data = None
        ultima_data = None
        duracao_total_dias = 0
        duracao_media = 0
        semanas_com_duracao = []
    
    # Semanas do ano atual
    hoje = date.today()
    ano_atual = hoje.year
    semanas_ano_atual = Semana52.objects.filter(inicio__year=ano_atual).count()
    
    # Semanas futuras (ainda não iniciadas)
    semanas_futuras = Semana52.objects.filter(inicio__gt=hoje).count()
    
    # Semanas passadas (já finalizadas)
    semanas_passadas = Semana52.objects.filter(fim__lt=hoje).count()
    
    # Semana atual (hoje está entre inicio e fim)
    semana_atual = Semana52.objects.filter(inicio__lte=hoje, fim__gte=hoje).first()
    
    context = {
        'page_title': 'Análise Geral - Plano Preventiva PCM',
        'active_page': 'analise_geral_plano_preventiva_pcm',
        
        # Meus Planos Preventiva
        'total_meus_planos': total_meus_planos,
        'meus_planos_com_roteiro': meus_planos_com_roteiro,
        'meus_planos_sem_roteiro': meus_planos_sem_roteiro,
        'meus_planos_com_desc_detalhada': meus_planos_com_desc_detalhada,
        'maquinas_unicas_meus_planos': maquinas_unicas_meus_planos,
        'setores_unicos_meus_planos': setores_unicos_meus_planos,
        'planos_com_documentos': planos_com_documentos,
        'taxa_meus_planos_com_roteiro': taxa_meus_planos_com_roteiro,
        'taxa_meus_planos_com_desc': taxa_meus_planos_com_desc,
        
        # Análise Roteiro/Plano
        'total_planos': total_planos,
        'total_roteiros': total_roteiros,
        'relacionamentos_encontrados': relacionamentos_encontrados,
        'relacionamentos_confirmados': relacionamentos_confirmados,
        'relacionamentos_pendentes': relacionamentos_pendentes,
        'planos_sem_relacao': planos_sem_relacao,
        'roteiros_sem_relacao': roteiros_sem_relacao,
        'taxa_cobertura_planos': taxa_cobertura_planos,
        'taxa_cobertura_roteiros': taxa_cobertura_roteiros,
        'taxa_confirmacao': taxa_confirmacao,
        
        # Máquinas Primárias/Secundárias
        'maquinas_primarias_total': maquinas_primarias_total,
        'maquinas_secundarias_total': maquinas_secundarias_total,
        'relacionamentos_maquinas': relacionamentos_maquinas,
        'primarias_com_relacionamentos': primarias_com_relacionamentos,
        'secundarias_relacionadas': secundarias_relacionadas,
        'primarias_sem_relacionamentos': primarias_sem_relacionamentos,
        'secundarias_disponiveis': secundarias_disponiveis,
        'taxa_primarias_relacionadas': taxa_primarias_relacionadas,
        
        # Semana52
        'total_semanas': total_semanas,
        'semanas_com_dados': semanas_com_dados,
        'semanas_ordenadas': semanas_ordenadas[:10],  # Primeiras 10 para preview
        'semanas_com_duracao': semanas_com_duracao,  # Primeiras 10 com duração calculada
        'primeira_data': primeira_data,
        'ultima_data': ultima_data,
        'duracao_total_dias': duracao_total_dias,
        'duracao_media': duracao_media,
        'semanas_ano_atual': semanas_ano_atual,
        'semanas_futuras': semanas_futuras,
        'semanas_passadas': semanas_passadas,
        'semana_atual': semana_atual,
    }
    
    return render(request, 'planejamento/analise_geral_plano_preventiva_pcm.html', context)


def analise_ordens_de_servico(request):
    """Análise de Ordens de Serviço - Dashboard com estatísticas"""
    from app.models import OrdemServicoCorretiva, PlanoPreventiva, OrdemServicoCorretivaFicha
    from django.db.models import Count, Q, Avg
    from collections import defaultdict
    
    # Estatísticas básicas
    total_corretivas = OrdemServicoCorretiva.objects.count()
    total_preventivas = PlanoPreventiva.objects.count()
    total_ordens = total_corretivas + total_preventivas
    
    # ========== ESTATÍSTICAS ORDEMSERVICOCORRETIVA ==========
    # Ordens por setor (top 10)
    ordens_por_setor = OrdemServicoCorretiva.objects.exclude(
        descr_setormanut__isnull=True
    ).exclude(
        descr_setormanut=''
    ).values('descr_setormanut').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    # Ordens por unidade (top 10)
    ordens_por_unidade = OrdemServicoCorretiva.objects.exclude(
        nome_unid__isnull=True
    ).exclude(
        nome_unid=''
    ).values('nome_unid').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    # Ordens por tipo de manutenção
    ordens_por_tipo_manut = OrdemServicoCorretiva.objects.exclude(
        descr_tpmanuttv__isnull=True
    ).exclude(
        descr_tpmanuttv=''
    ).values('descr_tpmanuttv').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    # Ordens por situação
    ordens_por_situacao = OrdemServicoCorretiva.objects.exclude(
        descr_sitordsetv__isnull=True
    ).exclude(
        descr_sitordsetv=''
    ).values('descr_sitordsetv').annotate(
        total=Count('id')
    ).order_by('-total')
    
    # Ordens com e sem máquina
    ordens_com_maquina = OrdemServicoCorretiva.objects.exclude(cd_maquina__isnull=True).count()
    ordens_sem_maquina = total_corretivas - ordens_com_maquina
    
    # Ordens com e sem funcionário executor
    ordens_com_executor = OrdemServicoCorretiva.objects.exclude(
        nm_func_exec__isnull=True
    ).exclude(
        nm_func_exec=''
    ).count()
    ordens_sem_executor = total_corretivas - ordens_com_executor
    
    # Ordens com e sem funcionário solicitante
    ordens_com_solicitante = OrdemServicoCorretiva.objects.exclude(
        nm_func_solic_os__isnull=True
    ).exclude(
        nm_func_solic_os=''
    ).count()
    ordens_sem_solicitante = total_corretivas - ordens_com_solicitante
    
    # Top 10 máquinas com mais ordens
    top_maquinas = OrdemServicoCorretiva.objects.exclude(
        cd_maquina__isnull=True
    ).values('cd_maquina', 'descr_maquina').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    # Top 10 funcionários executores
    top_executores = OrdemServicoCorretiva.objects.exclude(
        nm_func_exec__isnull=True
    ).exclude(
        nm_func_exec=''
    ).values('nm_func_exec').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    # ========== ESTATÍSTICAS ORDEMSERVICOCORRETIVAFICHA ==========
    total_fichas = OrdemServicoCorretivaFicha.objects.count()
    ordens_com_fichas = OrdemServicoCorretiva.objects.filter(fichas__isnull=False).distinct().count()
    ordens_sem_fichas = total_corretivas - ordens_com_fichas
    
    # Média de fichas por ordem
    if ordens_com_fichas > 0:
        media_fichas_por_ordem = total_fichas / ordens_com_fichas
    else:
        media_fichas_por_ordem = 0
    
    # Top 10 ordens com mais fichas
    top_ordens_fichas = OrdemServicoCorretiva.objects.annotate(
        num_fichas=Count('fichas')
    ).filter(
        num_fichas__gt=0
    ).order_by('-num_fichas')[:10]
    
    # Top 10 funcionários executores de fichas
    top_executores_fichas = OrdemServicoCorretivaFicha.objects.exclude(
        nm_func_exec_os__isnull=True
    ).exclude(
        nm_func_exec_os=''
    ).values('nm_func_exec_os').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    # Percentuais
    taxa_ordens_com_maquina = (ordens_com_maquina / total_corretivas * 100) if total_corretivas > 0 else 0
    taxa_ordens_com_executor = (ordens_com_executor / total_corretivas * 100) if total_corretivas > 0 else 0
    taxa_ordens_com_fichas = (ordens_com_fichas / total_corretivas * 100) if total_corretivas > 0 else 0
    
    context = {
        'page_title': 'Análise de Ordens de Serviço',
        'active_page': 'analise_ordens_de_servico',
        'total_ordens': total_ordens,
        'total_corretivas': total_corretivas,
        'total_preventivas': total_preventivas,
        
        # OrdemServicoCorretiva
        'ordens_por_setor': ordens_por_setor,
        'ordens_por_unidade': ordens_por_unidade,
        'ordens_por_tipo_manut': ordens_por_tipo_manut,
        'ordens_por_situacao': ordens_por_situacao,
        'ordens_com_maquina': ordens_com_maquina,
        'ordens_sem_maquina': ordens_sem_maquina,
        'ordens_com_executor': ordens_com_executor,
        'ordens_sem_executor': ordens_sem_executor,
        'ordens_com_solicitante': ordens_com_solicitante,
        'ordens_sem_solicitante': ordens_sem_solicitante,
        'top_maquinas': top_maquinas,
        'top_executores': top_executores,
        'taxa_ordens_com_maquina': taxa_ordens_com_maquina,
        'taxa_ordens_com_executor': taxa_ordens_com_executor,
        
        # OrdemServicoCorretivaFicha
        'total_fichas': total_fichas,
        'ordens_com_fichas': ordens_com_fichas,
        'ordens_sem_fichas': ordens_sem_fichas,
        'media_fichas_por_ordem': media_fichas_por_ordem,
        'top_ordens_fichas': top_ordens_fichas,
        'top_executores_fichas': top_executores_fichas,
        'taxa_ordens_com_fichas': taxa_ordens_com_fichas,
    }
    
    return render(request, 'ordens_de_servico/analise_ordens_de_servico.html', context)


def config_analise_ordens(request):
    """Configuração de Análise de Ordens de Serviço"""
    from django.contrib import messages
    
    if request.method == 'POST':
        # Aqui você pode processar e salvar as configurações
        # Por enquanto, apenas mostra uma mensagem de sucesso
        messages.success(request, 'Configurações salvas com sucesso!')
        return redirect('config_analise_ordens')
    
    context = {
        'page_title': 'Configuração de Análise de Ordens de Serviço',
        'active_page': 'config_analise_ordens',
    }
    
    return render(request, 'ordens_de_servico/config_analise_ordens.html', context)


def agrupar_acoes_do_plano_por_data(request):
    """Agrupar ações do plano por data de execução"""
    from app.models import MeuPlanoPreventiva
    from django.db.models import Count, Q
    from collections import defaultdict
    from datetime import datetime
    
    # Buscar todos os planos
    planos = MeuPlanoPreventiva.objects.all().order_by('dt_execucao', 'cd_maquina', 'sequencia_manutencao')
    
    # Agrupar por data de execução
    planos_por_data = defaultdict(list)
    planos_sem_data = []
    
    for plano in planos:
        if plano.dt_execucao:
            # Tentar parsear a data (formato DD/MM/YYYY)
            try:
                # Remover espaços e tentar diferentes formatos
                data_str = plano.dt_execucao.strip()
                if '/' in data_str:
                    # Formato DD/MM/YYYY
                    data_obj = datetime.strptime(data_str, '%d/%m/%Y').date()
                elif '-' in data_str:
                    # Formato YYYY-MM-DD
                    data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
                else:
                    # Tentar outros formatos
                    data_obj = datetime.strptime(data_str, '%Y%m%d').date()
                
                planos_por_data[data_obj].append(plano)
            except (ValueError, AttributeError):
                # Se não conseguir parsear, adicionar aos sem data
                planos_sem_data.append(plano)
        else:
            planos_sem_data.append(plano)
    
    # Ordenar as datas
    datas_ordenadas = sorted(planos_por_data.keys())
    
    # Estatísticas
    total_planos = planos.count()
    total_com_data = sum(len(planos_por_data[data]) for data in datas_ordenadas)
    total_sem_data = len(planos_sem_data)
    total_datas_unicas = len(datas_ordenadas)
    
    # Agrupar por semana (opcional - para análise semanal)
    planos_por_semana = defaultdict(list)
    for data, planos_list in planos_por_data.items():
        # Calcular número da semana do ano
        semana_ano = data.isocalendar()[1]
        ano = data.year
        chave_semana = f"{ano}-W{semana_ano:02d}"
        planos_por_semana[chave_semana].extend(planos_list)
    
    semanas_ordenadas = sorted(planos_por_semana.keys())
    
    # Converter defaultdict para dict e criar lista de tuplas para facilitar acesso no template
    planos_por_data_list = [(data, planos_por_data[data]) for data in datas_ordenadas]
    planos_por_semana_list = [(semana, planos_por_semana[semana]) for semana in semanas_ordenadas]
    
    context = {
        'page_title': 'Agrupar Ações do Plano por Data',
        'active_page': 'agrupar_acoes_do_plano_por_data',
        'planos_por_data': dict(planos_por_data),
        'planos_por_data_list': planos_por_data_list,
        'datas_ordenadas': datas_ordenadas,
        'planos_sem_data': planos_sem_data,
        'planos_por_semana': dict(planos_por_semana),
        'planos_por_semana_list': planos_por_semana_list,
        'semanas_ordenadas': semanas_ordenadas,
        'total_planos': total_planos,
        'total_com_data': total_com_data,
        'total_sem_data': total_sem_data,
        'total_datas_unicas': total_datas_unicas,
    }
    
    return render(request, 'planejamento/agrupar_acoes_do_plano_por_data.html', context)


def agrupar_preventiva_por_data(request):
    """Agrupar preventivas por data de execução"""
    from app.models import PlanoPreventiva
    from django.db.models import Count, Q
    from collections import defaultdict
    from datetime import datetime
    
    # Buscar todos os planos preventiva
    preventivas = PlanoPreventiva.objects.all().order_by('dt_execucao', 'cd_maquina', 'sequencia_manutencao')
    
    # Agrupar por data de execução
    preventivas_por_data = defaultdict(list)
    preventivas_sem_data = []
    
    for preventiva in preventivas:
        if preventiva.dt_execucao:
            # Tentar parsear a data (formato DD/MM/YYYY)
            try:
                # Remover espaços e tentar diferentes formatos
                data_str = preventiva.dt_execucao.strip()
                if '/' in data_str:
                    # Formato DD/MM/YYYY
                    data_obj = datetime.strptime(data_str, '%d/%m/%Y').date()
                elif '-' in data_str:
                    # Formato YYYY-MM-DD
                    data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
                else:
                    # Tentar outros formatos
                    data_obj = datetime.strptime(data_str, '%Y%m%d').date()
                
                preventivas_por_data[data_obj].append(preventiva)
            except (ValueError, AttributeError):
                # Se não conseguir parsear, adicionar aos sem data
                preventivas_sem_data.append(preventiva)
        else:
            preventivas_sem_data.append(preventiva)
    
    # Ordenar as datas
    datas_ordenadas = sorted(preventivas_por_data.keys())
    
    # Estatísticas
    total_preventivas = preventivas.count()
    total_com_data = sum(len(preventivas_por_data[data]) for data in datas_ordenadas)
    total_sem_data = len(preventivas_sem_data)
    total_datas_unicas = len(datas_ordenadas)
    
    # Agrupar por semana (opcional - para análise semanal)
    preventivas_por_semana = defaultdict(list)
    for data, preventivas_list in preventivas_por_data.items():
        # Calcular número da semana do ano
        semana_ano = data.isocalendar()[1]
        ano = data.year
        chave_semana = f"{ano}-W{semana_ano:02d}"
        preventivas_por_semana[chave_semana].extend(preventivas_list)
    
    semanas_ordenadas = sorted(preventivas_por_semana.keys())
    
    # Converter defaultdict para dict e criar lista de tuplas para facilitar acesso no template
    preventivas_por_data_list = [(data, preventivas_por_data[data]) for data in datas_ordenadas]
    preventivas_por_semana_list = [(semana, preventivas_por_semana[semana]) for semana in semanas_ordenadas]
    
    context = {
        'page_title': 'Agrupar Preventiva por Data',
        'active_page': 'agrupar_preventiva_por_data',
        'preventivas_por_data': dict(preventivas_por_data),
        'preventivas_por_data_list': preventivas_por_data_list,
        'datas_ordenadas': datas_ordenadas,
        'preventivas_sem_data': preventivas_sem_data,
        'preventivas_por_semana': dict(preventivas_por_semana),
        'preventivas_por_semana_list': preventivas_por_semana_list,
        'semanas_ordenadas': semanas_ordenadas,
        'total_preventivas': total_preventivas,
        'total_com_data': total_com_data,
        'total_sem_data': total_sem_data,
        'total_datas_unicas': total_datas_unicas,
    }
    
    return render(request, 'planejamento/agrupar_preventiva_por_data.html', context)


def criar_cronograma_planejado_preventiva(request):
    """Criar cronograma planejado de preventivas"""
    from app.models import MeuPlanoPreventiva, Semana52, Maquina
    from django.db.models import Q
    from datetime import datetime, date
    from collections import defaultdict
    
    # Parâmetros de seleção (para a nova função)
    selected_maquina_id = request.GET.get('maquina_id', None)
    selected_plano_id = request.GET.get('plano_id', None)
    selected_maquina = None
    selected_plano = None
    
    if selected_maquina_id:
        try:
            selected_maquina = Maquina.objects.get(id=selected_maquina_id)
        except Maquina.DoesNotExist:
            pass
    
    if selected_plano_id:
        try:
            selected_plano = MeuPlanoPreventiva.objects.get(id=selected_plano_id)
        except MeuPlanoPreventiva.DoesNotExist:
            pass
    
    # Buscar todas as máquinas e planos para popular os selects
    todas_maquinas = Maquina.objects.all().order_by('cd_maquina')
    todos_planos = MeuPlanoPreventiva.objects.all().order_by('cd_maquina', 'numero_plano', 'sequencia_manutencao')[:500]  # Limitar a 500 para performance
    
    # Buscar setores únicos para o filtro
    setores_unicos = Maquina.objects.exclude(
        cd_setormanut__isnull=True
    ).exclude(
        cd_setormanut=''
    ).values_list('cd_setormanut', flat=True).distinct().order_by('cd_setormanut')
    
    # Buscar todas as semanas do ano
    semanas = Semana52.objects.all().order_by('inicio')
    
    # Buscar todos os planos preventiva PCM
    planos = MeuPlanoPreventiva.objects.all().order_by('dt_execucao', 'cd_maquina', 'sequencia_manutencao')
    
    # Se uma máquina foi selecionada, filtrar planos por essa máquina
    if selected_maquina:
        planos = planos.filter(cd_maquina=selected_maquina.cd_maquina)
    
    # Se um plano foi selecionado, filtrar apenas esse plano
    if selected_plano:
        planos = planos.filter(id=selected_plano.id)
    
    # Buscar agendamentos de cronograma
    from app.models import AgendamentoCronograma
    agendamentos = AgendamentoCronograma.objects.all().select_related('maquina', 'plano_preventiva', 'semana').order_by('data_planejada')
    
    # Agrupar planos por semana
    planos_por_semana = defaultdict(list)
    planos_sem_data = []
    
    for plano in planos:
        if plano.dt_execucao:
            try:
                # Tentar parsear a data
                data_str = plano.dt_execucao.strip()
                if '/' in data_str:
                    data_obj = datetime.strptime(data_str, '%d/%m/%Y').date()
                elif '-' in data_str:
                    data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
                else:
                    data_obj = datetime.strptime(data_str, '%Y%m%d').date()
                
                # Encontrar a semana correspondente
                semana_encontrada = None
                for semana in semanas:
                    if semana.inicio and semana.fim:
                        if semana.inicio <= data_obj <= semana.fim:
                            semana_encontrada = semana
                            break
                
                if semana_encontrada:
                    planos_por_semana[semana_encontrada].append(plano)
                else:
                    planos_sem_data.append(plano)
            except (ValueError, AttributeError):
                planos_sem_data.append(plano)
        else:
            planos_sem_data.append(plano)
    
    # Agrupar agendamentos por semana
    agendamentos_por_semana = defaultdict(list)
    agendamentos_sem_semana = []
    
    for agendamento in agendamentos:
        if agendamento.semana:
            agendamentos_por_semana[agendamento.semana].append(agendamento)
        else:
            agendamentos_sem_semana.append(agendamento)
    
    # Estatísticas
    total_planos = planos.count()
    total_com_semana = sum(len(planos_por_semana[semana]) for semana in semanas)
    total_sem_semana = len(planos_sem_data)
    total_agendamentos = agendamentos.count()
    total_agendamentos_com_semana = sum(len(agendamentos_por_semana[semana]) for semana in semanas)
    
    # Criar lista de tuplas para facilitar acesso no template
    planos_por_semana_list = [(semana, planos_por_semana[semana]) for semana in semanas if semana in planos_por_semana]
    agendamentos_por_semana_list = [(semana, agendamentos_por_semana[semana]) for semana in semanas if semana in agendamentos_por_semana]
    
    # Criar lista combinada de semanas com agendamentos e planos
    semanas_com_dados = []
    for semana in semanas:
        agendamentos_semana = agendamentos_por_semana.get(semana, [])
        planos_semana = planos_por_semana.get(semana, [])
        if agendamentos_semana or planos_semana:
            semanas_com_dados.append((semana, agendamentos_semana, planos_semana))
    
    context = {
        'page_title': 'Criar Calendário Planejado de Preventivas',
        'active_page': 'criar_cronograma_planejado_preventiva',
        'semanas': semanas,
        'planos_por_semana': dict(planos_por_semana),
        'planos_por_semana_list': planos_por_semana_list,
        'planos_sem_data': planos_sem_data,
        'agendamentos_por_semana': dict(agendamentos_por_semana),
        'agendamentos_por_semana_list': agendamentos_por_semana_list,
        'agendamentos_sem_semana': agendamentos_sem_semana,
        'semanas_com_dados': semanas_com_dados,
        'total_planos': total_planos,
        'total_com_semana': total_com_semana,
        'total_sem_semana': total_sem_semana,
        'total_agendamentos': total_agendamentos,
        'total_agendamentos_com_semana': total_agendamentos_com_semana,
        'selected_maquina': selected_maquina,
        'selected_plano': selected_plano,
        'selected_maquina_id': selected_maquina_id,
        'selected_plano_id': selected_plano_id,
        'todas_maquinas': todas_maquinas,
        'todos_planos': todos_planos,
        'setores_unicos': setores_unicos,
    }
    
    return render(request, 'planejamento/criar_cronograma_planejado_preventiva.html', context)


def api_search_maquinas(request):
    """API endpoint para buscar máquinas"""
    from app.models import Maquina
    from django.http import JsonResponse
    
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    maquinas = Maquina.objects.all()
    
    # Buscar por código ou descrição
    try:
        query_num = int(float(query))
        maquinas = maquinas.filter(
            Q(cd_maquina=query_num) |
            Q(descr_maquina__icontains=query)
        )
    except (ValueError, TypeError):
        maquinas = maquinas.filter(
            Q(descr_maquina__icontains=query) |
            Q(cd_setormanut__icontains=query) |
            Q(nome_unid__icontains=query)
        )
    
    # Limitar a 20 resultados
    maquinas = maquinas[:20]
    
    results = []
    for maquina in maquinas:
        results.append({
            'id': maquina.id,
            'cd_maquina': maquina.cd_maquina,
            'descr_maquina': maquina.descr_maquina or '',
            'cd_setormanut': maquina.cd_setormanut or '',
            'nome_unid': maquina.nome_unid or '',
        })
    
    return JsonResponse({'results': results})


def api_search_planos_pcm(request):
    """API endpoint para buscar planos PCM"""
    from app.models import MeuPlanoPreventiva
    from django.http import JsonResponse
    
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    planos = MeuPlanoPreventiva.objects.all()
    
    # Buscar por código da máquina, número do plano ou descrição
    try:
        query_num = int(float(query))
        planos = planos.filter(
            Q(cd_maquina=query_num) |
            Q(numero_plano=query_num) |
            Q(descr_maquina__icontains=query) |
            Q(descr_tarefa__icontains=query)
        )
    except (ValueError, TypeError):
        planos = planos.filter(
            Q(descr_maquina__icontains=query) |
            Q(descr_tarefa__icontains=query) |
            Q(descr_plano__icontains=query)
        )
    
    # Limitar a 20 resultados
    planos = planos[:20]
    
    results = []
    for plano in planos:
        results.append({
            'id': plano.id,
            'cd_maquina': plano.cd_maquina,
            'descr_maquina': plano.descr_maquina or '',
            'numero_plano': plano.numero_plano,
            'sequencia_manutencao': plano.sequencia_manutencao,
            'sequencia_tarefa': plano.sequencia_tarefa,
            'descr_tarefa': plano.descr_tarefa or '',
        })
    
    return JsonResponse({'results': results})


def salvar_agendamentos_cronograma(request):
    """Salvar múltiplos agendamentos de cronograma com suporte a periodicidade"""
    from app.models import AgendamentoCronograma
    from django.http import JsonResponse
    from datetime import datetime, date, timedelta
    import json
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        agendamentos_data = data.get('agendamentos', [])
        
        if not agendamentos_data:
            return JsonResponse({'success': False, 'error': 'Nenhum agendamento fornecido'})
        
        saved_count = 0
        errors = []
        
        for agendamento_data in agendamentos_data:
            try:
                tipo = agendamento_data.get('tipo')
                item_id = agendamento_data.get('id')
                data_planejada_str = agendamento_data.get('data_planejada')
                nome_grupo = agendamento_data.get('nome_grupo', '').strip() or None
                periodicidade = agendamento_data.get('periodicidade')
                
                if not tipo or not item_id or not data_planejada_str:
                    errors.append(f'Agendamento inválido: campos obrigatórios faltando')
                    continue
                
                # Parse da data inicial
                try:
                    data_planejada = datetime.strptime(data_planejada_str, '%Y-%m-%d').date()
                except ValueError:
                    errors.append(f'Data inválida: {data_planejada_str}')
                    continue
                
                # Obter objeto máquina ou plano
                maquina_obj = None
                plano_obj = None
                
                if tipo == 'maquina':
                    from app.models import Maquina
                    try:
                        maquina_obj = Maquina.objects.get(id=item_id)
                    except Maquina.DoesNotExist:
                        errors.append(f'Máquina com ID {item_id} não encontrada')
                        continue
                elif tipo == 'plano':
                    from app.models import MeuPlanoPreventiva
                    try:
                        plano_obj = MeuPlanoPreventiva.objects.get(id=item_id)
                    except MeuPlanoPreventiva.DoesNotExist:
                        errors.append(f'Plano com ID {item_id} não encontrado')
                        continue
                else:
                    errors.append(f'Tipo de agendamento inválido: {tipo}')
                    continue
                
                # Calcular datas se houver periodicidade
                if periodicidade and periodicidade > 0:
                    # Calcular todas as datas até o final do ano
                    ano_atual = date.today().year
                    fim_do_ano = date(ano_atual, 12, 31)
                    
                    datas_agendamento = []
                    data_atual = data_planejada
                    
                    while data_atual <= fim_do_ano:
                        datas_agendamento.append(data_atual)
                        data_atual = data_atual + timedelta(days=periodicidade)
                else:
                    # Sem periodicidade, apenas uma data
                    datas_agendamento = [data_planejada]
                
                # Criar agendamentos para cada data
                for data_agendamento in datas_agendamento:
                    try:
                        agendamento = AgendamentoCronograma(
                            tipo_agendamento=tipo,
                            data_planejada=data_agendamento,
                            nome_grupo=nome_grupo,
                            periodicidade=periodicidade if periodicidade and periodicidade > 0 else None,
                            created_by=request.user.username if request.user.is_authenticated else 'Sistema'
                        )
                        
                        if tipo == 'maquina':
                            agendamento.maquina = maquina_obj
                        elif tipo == 'plano':
                            agendamento.plano_preventiva = plano_obj
                        
                        agendamento.full_clean()
                        agendamento.save()
                        saved_count += 1
                    except Exception as e:
                        errors.append(f'Erro ao salvar agendamento para data {data_agendamento}: {str(e)}')
                        continue
                
            except Exception as e:
                errors.append(f'Erro ao processar agendamento: {str(e)}')
                continue
        
        if saved_count > 0:
            return JsonResponse({
                'success': True,
                'saved_count': saved_count,
                'total': len(agendamentos_data),
                'errors': errors if errors else None
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Nenhum agendamento foi salvo',
                'errors': errors
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


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
    """Visualizar análise detalhada da relação entre um PlanoPreventiva e um RoteiroPreventiva - Função limpa para recriar do zero"""
    from django.shortcuts import redirect
    from django.contrib import messages
    
    messages.info(request, 'Esta funcionalidade está sendo recriada.')
    return redirect('analise_roteiro_plano_preventiva')


def erro_analise_plano_roteiro(request, plano_id=None, roteiro_id=None):
    """Visualizar análise de erros - o que está faltando para encontrar match entre PlanoPreventiva e RoteiroPreventiva"""
    from app.models import PlanoPreventiva, RoteiroPreventiva
    from django.shortcuts import redirect
    from django.contrib import messages
    
    # Se não há IDs, mostrar visão geral de todos os registros sem match
    if plano_id is None or roteiro_id is None:
        return erro_analise_plano_roteiro_geral(request)
    
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
    
    # Analisar o que está faltando para ter match
    erros = []
    problemas = []
    campos_comparados = []  # Lista de todos os campos para exibição completa
    
    # Verificar cd_maquina
    if not plano.cd_maquina or not roteiro.cd_maquina:
        erros.append({
            'campo': 'cd_maquina',
            'label': 'Código da Máquina',
            'problema': 'Um ou ambos os campos estão vazios',
            'plano_valor': plano.cd_maquina,
            'roteiro_valor': roteiro.cd_maquina,
            'solucao': 'Ambos os registros precisam ter o código da máquina preenchido e devem ser iguais',
            'tipo': 'vazio'
        })
    elif plano.cd_maquina != roteiro.cd_maquina:
        erros.append({
            'campo': 'cd_maquina',
            'label': 'Código da Máquina',
            'problema': 'Os valores são diferentes',
            'plano_valor': plano.cd_maquina,
            'roteiro_valor': roteiro.cd_maquina,
            'solucao': f'O código da máquina no Plano ({plano.cd_maquina}) deve ser igual ao do Roteiro ({roteiro.cd_maquina})',
            'tipo': 'diferente'
        })
    
    # Verificar descr_maquina
    descr_plano = (plano.descr_maquina or '').strip().upper()
    descr_roteiro = (roteiro.descr_maquina or '').strip().upper()
    campo_match = True
    if not descr_plano or not descr_roteiro:
        campo_match = False
        erros.append({
            'campo': 'descr_maquina',
            'label': 'Descrição da Máquina',
            'problema': 'Um ou ambos os campos estão vazios',
            'plano_valor': plano.descr_maquina,
            'roteiro_valor': roteiro.descr_maquina,
            'solucao': 'Ambos os registros precisam ter a descrição da máquina preenchida e devem ser iguais',
            'tipo': 'vazio'
        })
    elif descr_plano != descr_roteiro:
        campo_match = False
        erros.append({
            'campo': 'descr_maquina',
            'label': 'Descrição da Máquina',
            'problema': 'Os valores são diferentes',
            'plano_valor': plano.descr_maquina,
            'roteiro_valor': roteiro.descr_maquina,
            'solucao': 'As descrições da máquina devem ser idênticas (ignorando maiúsculas/minúsculas)',
            'tipo': 'diferente'
        })
    campos_comparados.append({
        'campo': 'descr_maquina',
        'label': 'Descrição da Máquina',
        'plano_valor': plano.descr_maquina,
        'roteiro_valor': roteiro.descr_maquina,
        'match': campo_match
    })
    
    # Verificar sequencia_tarefa vs cd_tarefamanu
    campo_match = True
    if not plano.sequencia_tarefa or not roteiro.cd_tarefamanu:
        campo_match = False
        erros.append({
            'campo': 'sequencia_tarefa',
            'label': 'Sequência Tarefa (Plano) / Código Tarefa (Roteiro)',
            'problema': 'Um ou ambos os campos estão vazios',
            'plano_valor': plano.sequencia_tarefa,
            'roteiro_valor': roteiro.cd_tarefamanu,
            'solucao': 'O campo "Sequência Tarefa" do Plano deve ser igual ao campo "Código Tarefa" do Roteiro',
            'tipo': 'vazio'
        })
    elif plano.sequencia_tarefa != roteiro.cd_tarefamanu:
        campo_match = False
        erros.append({
            'campo': 'sequencia_tarefa',
            'label': 'Sequência Tarefa (Plano) / Código Tarefa (Roteiro)',
            'problema': 'Os valores são diferentes',
            'plano_valor': plano.sequencia_tarefa,
            'roteiro_valor': roteiro.cd_tarefamanu,
            'solucao': f'O campo "Sequência Tarefa" do Plano ({plano.sequencia_tarefa}) deve ser igual ao campo "Código Tarefa" do Roteiro ({roteiro.cd_tarefamanu})',
            'tipo': 'diferente'
        })
    campos_comparados.append({
        'campo': 'sequencia_tarefa',
        'label': 'Sequência Tarefa (Plano) / Código Tarefa (Roteiro)',
        'plano_valor': plano.sequencia_tarefa,
        'roteiro_valor': roteiro.cd_tarefamanu,
        'match': campo_match
    })
    
    # Verificar descr_tarefa vs descr_tarefamanu
    descr_tarefa_plano = (plano.descr_tarefa or '').strip().upper()
    descr_tarefa_roteiro = (roteiro.descr_tarefamanu or '').strip().upper()
    campo_match = True
    if not descr_tarefa_plano or not descr_tarefa_roteiro:
        campo_match = False
        erros.append({
            'campo': 'descr_tarefa',
            'label': 'Descrição Tarefa (Plano) / Descrição Tarefa (Roteiro)',
            'problema': 'Um ou ambos os campos estão vazios',
            'plano_valor': plano.descr_tarefa,
            'roteiro_valor': roteiro.descr_tarefamanu,
            'solucao': 'O campo "Descrição Tarefa" do Plano deve ser igual ao campo "Descrição Tarefa" do Roteiro',
            'tipo': 'vazio'
        })
    elif descr_tarefa_plano != descr_tarefa_roteiro:
        campo_match = False
        erros.append({
            'campo': 'descr_tarefa',
            'label': 'Descrição Tarefa (Plano) / Descrição Tarefa (Roteiro)',
            'problema': 'Os valores são diferentes',
            'plano_valor': plano.descr_tarefa,
            'roteiro_valor': roteiro.descr_tarefamanu,
            'solucao': 'As descrições da tarefa devem ser idênticas (ignorando maiúsculas/minúsculas)',
            'tipo': 'diferente'
        })
    campos_comparados.append({
        'campo': 'descr_tarefa',
        'label': 'Descrição Tarefa (Plano) / Descrição Tarefa (Roteiro)',
        'plano_valor': plano.descr_tarefa,
        'roteiro_valor': roteiro.descr_tarefamanu,
        'match': campo_match
    })
    
    # Verificar sequencia_manutencao vs seq_seqplamanu
    campo_match = True
    if not plano.sequencia_manutencao or not roteiro.seq_seqplamanu:
        campo_match = False
        erros.append({
            'campo': 'sequencia_manutencao',
            'label': 'Sequência Manutenção (Plano) / Sequência Plano (Roteiro)',
            'problema': 'Um ou ambos os campos estão vazios',
            'plano_valor': plano.sequencia_manutencao,
            'roteiro_valor': roteiro.seq_seqplamanu,
            'solucao': 'O campo "Sequência Manutenção" do Plano deve ser igual ao campo "Sequência Plano" do Roteiro',
            'tipo': 'vazio'
        })
    elif plano.sequencia_manutencao != roteiro.seq_seqplamanu:
        campo_match = False
        erros.append({
            'campo': 'sequencia_manutencao',
            'label': 'Sequência Manutenção (Plano) / Sequência Plano (Roteiro)',
            'problema': 'Os valores são diferentes',
            'plano_valor': plano.sequencia_manutencao,
            'roteiro_valor': roteiro.seq_seqplamanu,
            'solucao': f'O campo "Sequência Manutenção" do Plano ({plano.sequencia_manutencao}) deve ser igual ao campo "Sequência Plano" do Roteiro ({roteiro.seq_seqplamanu})',
            'tipo': 'diferente'
        })
    campos_comparados.append({
        'campo': 'sequencia_manutencao',
        'label': 'Sequência Manutenção (Plano) / Sequência Plano (Roteiro)',
        'plano_valor': plano.sequencia_manutencao,
        'roteiro_valor': roteiro.seq_seqplamanu,
        'match': campo_match
    })
    
    # Resumo dos problemas
    total_erros = len(erros)
    campos_vazios = sum(1 for e in erros if e.get('tipo') == 'vazio')
    campos_diferentes = sum(1 for e in erros if e.get('tipo') == 'diferente')
    total_campos = 5  # Total de campos comparados
    campos_match = total_campos - total_erros
    percentual_match = (campos_match / total_campos * 100) if total_campos > 0 else 0
    
    context = {
        'page_title': f'Análise de Erros: Plano {plano.numero_plano} ↔ Roteiro {roteiro.cd_planmanut}',
        'active_page': 'analise_roteiro_plano_preventiva',
        'plano': plano,
        'roteiro': roteiro,
        'erros': erros,
        'total_erros': total_erros,
        'campos_vazios': campos_vazios,
        'campos_diferentes': campos_diferentes,
        'total_campos': total_campos,
        'campos_match': campos_match,
        'percentual_match': percentual_match,
        'campos_comparados': campos_comparados,
    }
    return render(request, 'planejamento/erro_analise_plano_roteiro.html', context)


def erro_analise_plano_roteiro_geral(request):
    """Visão geral de análise de erros - todos os registros sem match e o que está faltando"""
    from app.models import PlanoPreventiva, RoteiroPreventiva
    from django.core.paginator import Paginator
    
    # Buscar todos os registros
    planos = PlanoPreventiva.objects.all()
    roteiros = RoteiroPreventiva.objects.all()
    
    # Função para verificar se campos correspondem (mesma lógica da análise principal)
    def campos_correspondem(plano, roteiro):
        if not plano.cd_maquina or not roteiro.cd_maquina:
            return False
        if plano.cd_maquina != roteiro.cd_maquina:
            return False
        
        descr_plano = (plano.descr_maquina or '').strip().upper()
        descr_roteiro = (roteiro.descr_maquina or '').strip().upper()
        if descr_plano and descr_roteiro:
            if descr_plano != descr_roteiro:
                return False
        elif descr_plano or descr_roteiro:
            return False
        
        if not plano.sequencia_tarefa or not roteiro.cd_tarefamanu:
            return False
        if plano.sequencia_tarefa != roteiro.cd_tarefamanu:
            return False
        
        descr_tarefa_plano = (plano.descr_tarefa or '').strip().upper()
        descr_tarefa_roteiro = (roteiro.descr_tarefamanu or '').strip().upper()
        if descr_tarefa_plano and descr_tarefa_roteiro:
            if descr_tarefa_plano != descr_tarefa_roteiro:
                return False
        elif descr_tarefa_plano or descr_tarefa_roteiro:
            return False
        
        if not plano.sequencia_manutencao or not roteiro.seq_seqplamanu:
            return False
        if plano.sequencia_manutencao != roteiro.seq_seqplamanu:
            return False
        
        return True
    
    # Função para analisar erros de um par plano-roteiro
    def analisar_erros(plano, roteiro):
        erros = []
        
        # Verificar cd_maquina
        if not plano.cd_maquina or not roteiro.cd_maquina:
            erros.append('cd_maquina')
        elif plano.cd_maquina != roteiro.cd_maquina:
            erros.append('cd_maquina')
        
        # Verificar descr_maquina
        descr_plano = (plano.descr_maquina or '').strip().upper()
        descr_roteiro = (roteiro.descr_maquina or '').strip().upper()
        if not descr_plano or not descr_roteiro:
            erros.append('descr_maquina')
        elif descr_plano != descr_roteiro:
            erros.append('descr_maquina')
        
        # Verificar sequencia_tarefa vs cd_tarefamanu
        if not plano.sequencia_tarefa or not roteiro.cd_tarefamanu:
            erros.append('sequencia_tarefa')
        elif plano.sequencia_tarefa != roteiro.cd_tarefamanu:
            erros.append('sequencia_tarefa')
        
        # Verificar descr_tarefa vs descr_tarefamanu
        descr_tarefa_plano = (plano.descr_tarefa or '').strip().upper()
        descr_tarefa_roteiro = (roteiro.descr_tarefamanu or '').strip().upper()
        if not descr_tarefa_plano or not descr_tarefa_roteiro:
            erros.append('descr_tarefa')
        elif descr_tarefa_plano != descr_tarefa_roteiro:
            erros.append('descr_tarefa')
        
        # Verificar sequencia_manutencao vs seq_seqplamanu
        if not plano.sequencia_manutencao or not roteiro.seq_seqplamanu:
            erros.append('sequencia_manutencao')
        elif plano.sequencia_manutencao != roteiro.seq_seqplamanu:
            erros.append('sequencia_manutencao')
        
        return erros
    
    # Encontrar planos sem match
    planos_sem_match = []
    planos_processados = set()
    roteiros_processados = set()
    
    for plano in planos:
        tem_match = False
        melhor_match = None
        melhor_erros = []
        
        for roteiro in roteiros:
            if campos_correspondem(plano, roteiro):
                tem_match = True
                planos_processados.add(plano.id)
                roteiros_processados.add(roteiro.id)
                break
            else:
                # Analisar erros para encontrar o melhor match parcial
                erros = analisar_erros(plano, roteiro)
                if not melhor_match or len(erros) < len(melhor_erros):
                    melhor_match = roteiro
                    melhor_erros = erros
        
        if not tem_match:
            planos_sem_match.append({
                'plano': plano,
                'melhor_match': melhor_match,
                'erros': melhor_erros,
                'total_erros': len(melhor_erros) if melhor_erros else 5,
            })
    
    # Encontrar roteiros sem match
    roteiros_sem_match = []
    for roteiro in roteiros:
        if roteiro.id not in roteiros_processados:
            melhor_match = None
            melhor_erros = []
            
            for plano in planos:
                if plano.id not in planos_processados:
                    erros = analisar_erros(plano, roteiro)
                    if not melhor_match or len(erros) < len(melhor_erros):
                        melhor_match = plano
                        melhor_erros = erros
            
            roteiros_sem_match.append({
                'roteiro': roteiro,
                'melhor_match': melhor_match,
                'erros': melhor_erros,
                'total_erros': len(melhor_erros) if melhor_erros else 5,
            })
    
    # Estatísticas gerais
    total_planos_sem_match = len(planos_sem_match)
    total_roteiros_sem_match = len(roteiros_sem_match)
    
    # Contar tipos de erros mais comuns
    erros_comuns = {}
    for item in planos_sem_match + roteiros_sem_match:
        for erro in item['erros']:
            erros_comuns[erro] = erros_comuns.get(erro, 0) + 1
    
    context = {
        'page_title': 'Análise Geral de Erros - Correspondências não encontradas',
        'active_page': 'analise_roteiro_plano_preventiva',
        'planos_sem_match': planos_sem_match[:50],  # Limitar para performance
        'roteiros_sem_match': roteiros_sem_match[:50],
        'total_planos_sem_match': total_planos_sem_match,
        'total_roteiros_sem_match': total_roteiros_sem_match,
        'erros_comuns': sorted(erros_comuns.items(), key=lambda x: x[1], reverse=True),
        'is_geral': True,
    }
    return render(request, 'planejamento/erro_analise_plano_roteiro.html', context)


def relacionar_roteiro_plano(request):
    """Página para relacionar manualmente Roteiros e Planos que não têm match"""
    from app.models import PlanoPreventiva, RoteiroPreventiva, MeuPlanoPreventiva
    from django.contrib import messages
    from django.db import transaction
    from django.core.paginator import Paginator
    
    # Processar criação de relacionamento manual
    if request.method == 'POST' and 'criar_relacionamento' in request.POST:
        plano_id = request.POST.get('plano_id')
        roteiro_id = request.POST.get('roteiro_id')
        tipo = request.POST.get('tipo')  # 'roteiro_sem' ou 'plano_sem'
        
        if not plano_id or not roteiro_id:
            messages.error(request, 'Por favor, selecione tanto um Plano quanto um Roteiro.')
        else:
            try:
                plano = PlanoPreventiva.objects.get(id=plano_id)
                roteiro = RoteiroPreventiva.objects.get(id=roteiro_id)
                
                # Verificar se já existe um MeuPlanoPreventiva para este plano
                meu_plano, created = MeuPlanoPreventiva.objects.get_or_create(
                    cd_maquina=plano.cd_maquina,
                    sequencia_manutencao=plano.sequencia_manutencao,
                    sequencia_tarefa=plano.sequencia_tarefa,
                    defaults={
                        'cd_unid': plano.cd_unid,
                        'nome_unid': plano.nome_unid,
                        'cd_setor': plano.cd_setor,
                        'descr_setor': plano.descr_setor,
                        'cd_atividade': plano.cd_atividade,
                        'descr_maquina': plano.descr_maquina,
                        'nro_patrimonio': plano.nro_patrimonio,
                        'numero_plano': plano.numero_plano,
                        'descr_plano': plano.descr_plano,
                        'dt_execucao': plano.dt_execucao,
                        'quantidade_periodo': plano.quantidade_periodo,
                        'descr_tarefa': plano.descr_tarefa,
                        'cd_funcionario': plano.cd_funcionario,
                        'nome_funcionario': plano.nome_funcionario,
                        'descr_seqplamanu': plano.descr_seqplamanu,
                        'desc_detalhada_do_roteiro_preventiva': roteiro.descr_seqplamanu,
                        'roteiro_preventiva': roteiro,
                        'maquina': plano.maquina,
                    }
                )
                
                # Se já existia, atualizar
                if not created:
                    meu_plano.desc_detalhada_do_roteiro_preventiva = roteiro.descr_seqplamanu
                    meu_plano.roteiro_preventiva = roteiro
                    meu_plano.save()
                
                messages.success(request, f'Relacionamento criado com sucesso! Plano {plano.id} vinculado ao Roteiro {roteiro.id} em MeuPlanoPreventiva.')
            except PlanoPreventiva.DoesNotExist:
                messages.error(request, 'Plano não encontrado.')
            except RoteiroPreventiva.DoesNotExist:
                messages.error(request, 'Roteiro não encontrado.')
            except Exception as e:
                messages.error(request, f'Erro ao criar relacionamento: {str(e)}')
    
    # Buscar todos os registros
    planos = PlanoPreventiva.objects.all()
    roteiros = RoteiroPreventiva.objects.all()
    
    # Função para verificar se campos correspondem
    def campos_correspondem(plano, roteiro):
        if not plano.cd_maquina or not roteiro.cd_maquina:
            return False
        if plano.cd_maquina != roteiro.cd_maquina:
            return False
        
        descr_plano = (plano.descr_maquina or '').strip().upper()
        descr_roteiro = (roteiro.descr_maquina or '').strip().upper()
        if descr_plano and descr_roteiro:
            if descr_plano != descr_roteiro:
                return False
        elif descr_plano or descr_roteiro:
            return False
        
        if not plano.sequencia_tarefa or not roteiro.cd_tarefamanu:
            return False
        if plano.sequencia_tarefa != roteiro.cd_tarefamanu:
            return False
        
        descr_tarefa_plano = (plano.descr_tarefa or '').strip().upper()
        descr_tarefa_roteiro = (roteiro.descr_tarefamanu or '').strip().upper()
        if descr_tarefa_plano and descr_tarefa_roteiro:
            if descr_tarefa_plano != descr_tarefa_roteiro:
                return False
        elif descr_tarefa_plano or descr_tarefa_roteiro:
            return False
        
        if not plano.sequencia_manutencao or not roteiro.seq_seqplamanu:
            return False
        if plano.sequencia_manutencao != roteiro.seq_seqplamanu:
            return False
        
        return True
    
    # Encontrar relacionamentos existentes
    relacionamentos = []
    planos_processados = set()
    roteiros_processados = set()
    
    for plano in planos:
        for roteiro in roteiros:
            if campos_correspondem(plano, roteiro):
                relacionamentos.append((plano.id, roteiro.id))
                planos_processados.add(plano.id)
                roteiros_processados.add(roteiro.id)
                break
    
    # Encontrar planos sem match
    planos_sem_match = [p for p in planos if p.id not in planos_processados]
    
    # Encontrar roteiros sem match
    roteiros_sem_match = [r for r in roteiros if r.id not in roteiros_processados]
    
    # Paginação
    page_planos = request.GET.get('page_planos', 1)
    page_roteiros = request.GET.get('page_roteiros', 1)
    
    paginator_planos = Paginator(planos_sem_match, 20)
    paginator_roteiros = Paginator(roteiros_sem_match, 20)
    
    planos_paginated = paginator_planos.get_page(page_planos)
    roteiros_paginated = paginator_roteiros.get_page(page_roteiros)
    
    context = {
        'page_title': 'Relacionar Roteiro e Plano Manualmente',
        'active_page': 'relacionar_roteiro_plano',
        'planos_sem_match': planos_paginated,
        'roteiros_sem_match': roteiros_paginated,
        'total_planos_sem_match': len(planos_sem_match),
        'total_roteiros_sem_match': len(roteiros_sem_match),
        'todos_planos': list(planos.values('id', 'numero_plano', 'cd_maquina', 'descr_maquina', 'sequencia_manutencao', 'sequencia_tarefa')),
        'todos_roteiros': list(roteiros.values('id', 'cd_planmanut', 'cd_maquina', 'descr_maquina', 'seq_seqplamanu', 'cd_tarefamanu')),
    }
    return render(request, 'planejamento/relacionar_roteiro_plano.html', context)


def visualizar_comparacao_roteiro_plano(request, plano_id, roteiro_id):
    """Visualizar comparação detalhada entre um PlanoPreventiva e um RoteiroPreventiva"""
    from app.models import PlanoPreventiva, RoteiroPreventiva, MeuPlanoPreventiva
    from django.shortcuts import redirect
    from django.contrib import messages
    
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
    
    # Função para verificar se os campos correspondem
    def verificar_correspondencia(plano, roteiro):
        """Verifica se os campos principais correspondem exatamente"""
        comparacoes = {}
        
        # Comparar cd_maquina
        comparacoes['cd_maquina'] = {
            'plano': plano.cd_maquina,
            'roteiro': roteiro.cd_maquina,
            'match': plano.cd_maquina == roteiro.cd_maquina if plano.cd_maquina and roteiro.cd_maquina else False,
            'campo_plano': 'cd_maquina',
            'campo_roteiro': 'cd_maquina',
            'label': 'Código da Máquina'
        }
        
        # Comparar descr_maquina
        descr_plano = (plano.descr_maquina or '').strip().upper()
        descr_roteiro = (roteiro.descr_maquina or '').strip().upper()
        comparacoes['descr_maquina'] = {
            'plano': plano.descr_maquina,
            'roteiro': roteiro.descr_maquina,
            'match': descr_plano == descr_roteiro if descr_plano and descr_roteiro else False,
            'campo_plano': 'descr_maquina',
            'campo_roteiro': 'descr_maquina',
            'label': 'Descrição da Máquina'
        }
        
        # Comparar sequencia_tarefa (Plano) com cd_tarefamanu (Roteiro)
        comparacoes['sequencia_tarefa'] = {
            'plano': plano.sequencia_tarefa,
            'roteiro': roteiro.cd_tarefamanu,
            'match': plano.sequencia_tarefa == roteiro.cd_tarefamanu if plano.sequencia_tarefa and roteiro.cd_tarefamanu else False,
            'campo_plano': 'sequencia_tarefa',
            'campo_roteiro': 'cd_tarefamanu',
            'label': 'Sequência Tarefa / Código Tarefa'
        }
        
        # Comparar descr_tarefa (Plano) com descr_tarefamanu (Roteiro)
        descr_tarefa_plano = (plano.descr_tarefa or '').strip().upper()
        descr_tarefa_roteiro = (roteiro.descr_tarefamanu or '').strip().upper()
        comparacoes['descr_tarefa'] = {
            'plano': plano.descr_tarefa,
            'roteiro': roteiro.descr_tarefamanu,
            'match': descr_tarefa_plano == descr_tarefa_roteiro if descr_tarefa_plano and descr_tarefa_roteiro else False,
            'campo_plano': 'descr_tarefa',
            'campo_roteiro': 'descr_tarefamanu',
            'label': 'Descrição Tarefa'
        }
        
        # Comparar sequencia_manutencao (Plano) com seq_seqplamanu (Roteiro)
        comparacoes['sequencia_manutencao'] = {
            'plano': plano.sequencia_manutencao,
            'roteiro': roteiro.seq_seqplamanu,
            'match': plano.sequencia_manutencao == roteiro.seq_seqplamanu if plano.sequencia_manutencao and roteiro.seq_seqplamanu else False,
            'campo_plano': 'sequencia_manutencao',
            'campo_roteiro': 'seq_seqplamanu',
            'label': 'Sequência Manutenção'
        }
        
        return comparacoes
    
    # Verificar correspondências
    comparacoes = verificar_correspondencia(plano, roteiro)
    
    # Contar matches
    total_campos = len(comparacoes)
    campos_match = sum(1 for comp in comparacoes.values() if comp['match'])
    percentual_match = (campos_match / total_campos * 100) if total_campos > 0 else 0
    
    # Verificar se corresponde completamente (todos os campos)
    corresponde_completamente = all(comp['match'] for comp in comparacoes.values())
    
    # Verificar se já foi salvo em MeuPlanoPreventiva
    ja_salvo = MeuPlanoPreventiva.objects.filter(
        cd_maquina=plano.cd_maquina,
        sequencia_manutencao=plano.sequencia_manutencao,
        sequencia_tarefa=plano.sequencia_tarefa
    ).exists()
    
    context = {
        'page_title': f'Comparação: Plano {plano.numero_plano} ↔ Roteiro {roteiro.cd_planmanut}',
        'active_page': 'analise_roteiro_plano_preventiva',
        'plano': plano,
        'roteiro': roteiro,
        'comparacoes': comparacoes,
        'total_campos': total_campos,
        'campos_match': campos_match,
        'percentual_match': percentual_match,
        'corresponde_completamente': corresponde_completamente,
        'ja_salvo': ja_salvo,
        'descr_seqplamanu': roteiro.descr_seqplamanu,
    }
    return render(request, 'visualizar/visualizar_comparacao_roteiro_plano.html', context)


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
    return render(request, 'visualizar/visualizar_plano_preventiva.html', context)


def visualizar_plano_pcm(request, plano_id):
    """Visualizar detalhes de um MeuPlanoPreventiva específico"""
    from app.models import MeuPlanoPreventiva, MeuPlanoPreventivaDocumento
    from django.shortcuts import redirect
    from django.contrib import messages
    
    try:
        plano = MeuPlanoPreventiva.objects.select_related('maquina', 'roteiro_preventiva').get(id=plano_id)
    except MeuPlanoPreventiva.DoesNotExist:
        messages.error(request, 'Plano PCM não encontrado.')
        return redirect('consultar_meu_plano')
    
    # Buscar documentos associados
    documentos_associados = MeuPlanoPreventivaDocumento.objects.filter(
        meu_plano_preventiva=plano
    ).select_related('maquina_documento').order_by('-created_at')
    
    context = {
        'page_title': f'Visualizar Plano PCM - Plano {plano.numero_plano}',
        'active_page': 'consultar_meu_plano',
        'plano': plano,
        'documentos_associados': documentos_associados,
    }
    return render(request, 'visualizar/visualizar_plano_pcm.html', context)


def gerar_pdf_plano_pcm(request, plano_id):
    """Gerar PDF com informações do MeuPlanoPreventiva e documentos associados"""
    from app.models import MeuPlanoPreventiva, MeuPlanoPreventivaDocumento
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.pdfgen import canvas
    from io import BytesIO
    import os
    from django.conf import settings
    
    try:
        plano = MeuPlanoPreventiva.objects.select_related('maquina', 'roteiro_preventiva').get(id=plano_id)
    except MeuPlanoPreventiva.DoesNotExist:
        from django.contrib import messages
        messages.error(request, 'Plano PCM não encontrado.')
        from django.shortcuts import redirect
        return redirect('consultar_meu_plano')
    
    # Buscar documentos associados
    documentos_associados = MeuPlanoPreventivaDocumento.objects.filter(
        meu_plano_preventiva=plano
    ).select_related('maquina_documento').order_by('-created_at')
    
    # Criar buffer para o PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    
    # Container para os elementos do PDF
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#FF9800'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1976D2'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#424242'),
        spaceAfter=8,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )
    
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    normal_style.leading = 14
    
    # Título
    elements.append(Paragraph("PLANO PCM - MANUTENÇÃO PREVENTIVA", title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Informações do Plano
    elements.append(Paragraph("INFORMAÇÕES DO PLANO", heading_style))
    
    plano_data = [
        ['<b>Número do Plano:</b>', str(plano.numero_plano) if plano.numero_plano else 'Não informado'],
        ['<b>Descrição do Plano:</b>', plano.descr_plano or 'Não informado'],
        ['<b>Sequência Manutenção:</b>', str(plano.sequencia_manutencao) if plano.sequencia_manutencao else 'Não informado'],
        ['<b>Sequência Tarefa:</b>', str(plano.sequencia_tarefa) if plano.sequencia_tarefa else 'Não informado'],
        ['<b>Data Execução:</b>', plano.dt_execucao or 'Não informado'],
        ['<b>Período (dias):</b>', str(plano.quantidade_periodo) if plano.quantidade_periodo else 'Não informado'],
    ]
    
    plano_table = Table(plano_data, colWidths=[6*cm, 10*cm])
    plano_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E3F2FD')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1976D2')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(plano_table)
    elements.append(Spacer(1, 0.3*cm))
    
    # Descrição da Tarefa
    if plano.descr_tarefa:
        elements.append(Paragraph("<b>Descrição da Tarefa:</b>", subheading_style))
        elements.append(Paragraph(plano.descr_tarefa, normal_style))
        elements.append(Spacer(1, 0.3*cm))
    
    # DESCR_SEQPLAMANU
    if plano.descr_seqplamanu:
        elements.append(Paragraph("<b>Descrição Sequência Plano Manutenção (DESCR_SEQPLAMANU):</b>", subheading_style))
        elements.append(Paragraph(plano.descr_seqplamanu, normal_style))
        elements.append(Spacer(1, 0.3*cm))
    
    # Descrição Detalhada do Roteiro
    if plano.desc_detalhada_do_roteiro_preventiva:
        elements.append(Paragraph("<b>Descrição Detalhada do Roteiro Preventiva:</b>", subheading_style))
        elements.append(Paragraph(plano.desc_detalhada_do_roteiro_preventiva, normal_style))
        elements.append(Spacer(1, 0.3*cm))
    
    elements.append(Spacer(1, 0.5*cm))
    
    # Informações da Máquina
    elements.append(Paragraph("INFORMAÇÕES DA MÁQUINA", heading_style))
    
    maquina_data = [
        ['<b>Código da Máquina:</b>', str(plano.cd_maquina) if plano.cd_maquina else 'Não informado'],
        ['<b>Descrição da Máquina:</b>', plano.descr_maquina or 'Não informado'],
        ['<b>Nº Patrimônio:</b>', plano.nro_patrimonio or 'Não informado'],
    ]
    
    maquina_table = Table(maquina_data, colWidths=[6*cm, 10*cm])
    maquina_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E3F2FD')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1976D2')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(maquina_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Informações do Funcionário
    elements.append(Paragraph("FUNCIONÁRIO RESPONSÁVEL", heading_style))
    
    funcionario_data = [
        ['<b>Código Funcionário:</b>', plano.cd_funcionario or 'Não informado'],
        ['<b>Nome Funcionário:</b>', plano.nome_funcionario or 'Não informado'],
    ]
    
    funcionario_table = Table(funcionario_data, colWidths=[6*cm, 10*cm])
    funcionario_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E3F2FD')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1976D2')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(funcionario_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Informações de Unidade e Setor
    elements.append(Paragraph("UNIDADE E SETOR", heading_style))
    
    unidade_data = [
        ['<b>Código Unidade:</b>', str(plano.cd_unid) if plano.cd_unid else 'Não informado'],
        ['<b>Nome Unidade:</b>', plano.nome_unid or 'Não informado'],
        ['<b>Código Setor:</b>', plano.cd_setor or 'Não informado'],
        ['<b>Descrição Setor:</b>', plano.descr_setor or 'Não informado'],
        ['<b>Código Atividade:</b>', str(plano.cd_atividade) if plano.cd_atividade else 'Não informado'],
    ]
    
    unidade_table = Table(unidade_data, colWidths=[6*cm, 10*cm])
    unidade_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E3F2FD')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1976D2')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(unidade_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Documentos Associados
    elements.append(Paragraph("DOCUMENTOS ASSOCIADOS", heading_style))
    
    if documentos_associados:
        elements.append(Paragraph(f"Total de documentos associados: <b>{documentos_associados.count()}</b>", normal_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Cabeçalho da tabela de documentos
        doc_header = [['<b>#</b>', '<b>Nome do Arquivo</b>', '<b>Comentário Original</b>', '<b>Comentário Adicional</b>', '<b>Data Associação</b>']]
        
        doc_data = doc_header.copy()
        for idx, associacao in enumerate(documentos_associados, 1):
            nome_arquivo = os.path.basename(associacao.maquina_documento.arquivo.name) if associacao.maquina_documento.arquivo else 'N/A'
            comentario_original = associacao.maquina_documento.comentario or '-'
            comentario_adicional = associacao.comentario or '-'
            data_associacao = associacao.created_at.strftime('%d/%m/%Y %H:%M') if associacao.created_at else '-'
            
            doc_data.append([
                str(idx),
                nome_arquivo[:50] + '...' if len(nome_arquivo) > 50 else nome_arquivo,
                comentario_original[:40] + '...' if len(comentario_original) > 40 else comentario_original,
                comentario_adicional[:40] + '...' if len(comentario_adicional) > 40 else comentario_adicional,
                data_associacao
            ])
        
        doc_table = Table(doc_data, colWidths=[1*cm, 5*cm, 4*cm, 4*cm, 2*cm])
        doc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(doc_table)
    else:
        elements.append(Paragraph("<i>Nenhum documento associado a este plano PCM.</i>", normal_style))
    
    elements.append(Spacer(1, 0.5*cm))
    
    # Informações do Sistema
    elements.append(Paragraph("INFORMAÇÕES DO SISTEMA", heading_style))
    
    sistema_data = [
        ['<b>ID do Registro:</b>', str(plano.id)],
        ['<b>Data de Criação:</b>', plano.created_at.strftime('%d/%m/%Y %H:%M:%S') if plano.created_at else 'N/A'],
        ['<b>Última Atualização:</b>', plano.updated_at.strftime('%d/%m/%Y %H:%M:%S') if plano.updated_at else 'N/A'],
    ]
    
    sistema_table = Table(sistema_data, colWidths=[6*cm, 10*cm])
    sistema_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E3F2FD')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1976D2')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(sistema_table)
    
    # Construir PDF principal
    doc.build(elements)
    
    # Obter o PDF principal
    buffer.seek(0)
    pdf_principal = buffer.getvalue()
    
    # Mesclar PDFs dos documentos associados
    try:
        from PyPDF2 import PdfReader, PdfWriter
        import tempfile
        
        # Criar um writer para o PDF final
        pdf_writer = PdfWriter()
        
        # Adicionar o PDF principal
        pdf_principal_reader = PdfReader(BytesIO(pdf_principal))
        for page in pdf_principal_reader.pages:
            pdf_writer.add_page(page)
        
        # Processar documentos associados
        pdfs_mesclados = 0
        pdfs_nao_mesclados = []
        
        for associacao in documentos_associados:
            if associacao.maquina_documento and associacao.maquina_documento.arquivo:
                arquivo_path = associacao.maquina_documento.arquivo.path
                nome_arquivo = os.path.basename(arquivo_path)
                extensao = os.path.splitext(nome_arquivo)[1].lower()
                
                # Verificar se é PDF
                if extensao == '.pdf' and os.path.exists(arquivo_path):
                    try:
                        # Ler o PDF do documento
                        with open(arquivo_path, 'rb') as pdf_file:
                            pdf_reader = PdfReader(pdf_file)
                            
                            # Adicionar diretamente todas as páginas do PDF do documento
                            for page in pdf_reader.pages:
                                pdf_writer.add_page(page)
                            
                            pdfs_mesclados += 1
                    except Exception as e:
                        # Se houver erro ao processar o PDF, apenas registrar e continuar
                        pdfs_nao_mesclados.append(nome_arquivo)
                        print(f"Erro ao mesclar PDF {nome_arquivo}: {str(e)}")
                else:
                    # Não é PDF ou arquivo não existe - criar página informativa
                    try:
                        info_buffer = BytesIO()
                        info_doc = SimpleDocTemplate(info_buffer, pagesize=A4)
                        info_elements = []
                        
                        info_elements.append(Spacer(1, 8*cm))
                        info_elements.append(Paragraph(f"<b>DOCUMENTO ANEXO:</b> {nome_arquivo}", heading_style))
                        info_elements.append(Spacer(1, 0.3*cm))
                        info_elements.append(Paragraph(f"<i>Este arquivo não é um PDF e não pode ser incluído diretamente no documento.</i>", normal_style))
                        info_elements.append(Spacer(1, 0.2*cm))
                        info_elements.append(Paragraph(f"<b>Tipo de arquivo:</b> {extensao or 'Desconhecido'}", normal_style))
                        if associacao.maquina_documento.comentario:
                            info_elements.append(Paragraph(f"<b>Comentário:</b> {associacao.maquina_documento.comentario}", normal_style))
                        if associacao.comentario:
                            info_elements.append(Paragraph(f"<b>Comentário Adicional:</b> {associacao.comentario}", normal_style))
                        
                        info_doc.build(info_elements)
                        info_buffer.seek(0)
                        info_reader = PdfReader(info_buffer)
                        if info_reader.pages:
                            pdf_writer.add_page(info_reader.pages[0])
                    except Exception as e:
                        print(f"Erro ao criar página informativa para {nome_arquivo}: {str(e)}")
                    pdfs_nao_mesclados.append(nome_arquivo)
        
        # Criar buffer final com o PDF mesclado
        buffer_final = BytesIO()
        pdf_writer.write(buffer_final)
        buffer_final.seek(0)
        pdf_final = buffer_final.getvalue()
        
    except ImportError:
        # Se PyPDF2 não estiver instalado, usar apenas o PDF principal
        pdf_final = pdf_principal
    except Exception as e:
        # Em caso de erro na mesclagem, usar apenas o PDF principal
        print(f"Erro ao mesclar PDFs: {str(e)}")
        pdf_final = pdf_principal
    
    # Criar resposta HTTP
    response = HttpResponse(pdf_final, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Plano_PCM_{plano.numero_plano}_{plano.cd_maquina}.pdf"'
    
    return response


def editar_plano_pcm(request, plano_id):
    """Editar um MeuPlanoPreventiva existente"""
    from app.forms import MeuPlanoPreventivaForm
    from app.models import MeuPlanoPreventiva, Maquina, RoteiroPreventiva, MaquinaDocumento, MeuPlanoPreventivaDocumento
    
    try:
        plano = MeuPlanoPreventiva.objects.get(id=plano_id)
    except MeuPlanoPreventiva.DoesNotExist:
        messages.error(request, 'Plano PCM não encontrado.')
        return redirect('consultar_meu_plano')
    
    if request.method == 'POST':
        form = MeuPlanoPreventivaForm(request.POST, instance=plano)
        
        if form.is_valid():
            try:
                plano = form.save()
                messages.success(request, f'Plano PCM {plano.numero_plano} atualizado com sucesso!')
                return redirect('visualizar_plano_pcm', plano_id=plano.id)
            except Exception as e:
                messages.error(request, f'Erro ao atualizar plano PCM: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = MeuPlanoPreventivaForm(instance=plano)
    
    # Buscar máquinas e roteiros para os selects
    maquinas = Maquina.objects.all().order_by('cd_maquina')[:100]  # Limitar para performance
    roteiros = RoteiroPreventiva.objects.all().order_by('cd_maquina', 'cd_planmanut')[:100]  # Limitar para performance
    
    # Buscar documentos da máquina associada (se houver)
    documentos_maquina = []
    documentos_associados = []
    associacoes = []
    documentos_associados_ids = []
    associacoes_dict = {}  # Dicionário para mapear documento_id -> associacao_id
    if plano.maquina:
        documentos_maquina = MaquinaDocumento.objects.filter(maquina=plano.maquina).order_by('-created_at')
        # Buscar associações existentes
        associacoes = MeuPlanoPreventivaDocumento.objects.filter(
            meu_plano_preventiva=plano
        ).select_related('maquina_documento').order_by('-created_at')
        documentos_associados_ids = list(associacoes.values_list('maquina_documento_id', flat=True))
        documentos_associados = MaquinaDocumento.objects.filter(id__in=documentos_associados_ids).order_by('-created_at')
        # Criar dicionário para facilitar busca no template
        for associacao in associacoes:
            associacoes_dict[associacao.maquina_documento.id] = associacao.id
    
    context = {
        'page_title': f'Editar Plano PCM - Plano {plano.numero_plano}',
        'active_page': 'consultar_meu_plano',
        'form': form,
        'plano': plano,
        'maquinas': maquinas,
        'roteiros': roteiros,
        'documentos_maquina': documentos_maquina,
        'documentos_associados': documentos_associados,
        'associacoes': associacoes,
        'documentos_associados_ids': documentos_associados_ids,
        'associacoes_dict': associacoes_dict,
    }
    return render(request, 'editar/editar_plano_pcm.html', context)


def associar_documento_plano_pcm(request, plano_id, documento_id):
    """Associar um documento de máquina a um MeuPlanoPreventiva"""
    from app.models import MeuPlanoPreventiva, MaquinaDocumento, MeuPlanoPreventivaDocumento
    
    # Aceitar tanto GET quanto POST
    if request.method not in ['GET', 'POST']:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)
        messages.error(request, 'Método não permitido.')
        return redirect('editar_plano_pcm', plano_id=plano_id)
    
    try:
        plano = MeuPlanoPreventiva.objects.get(id=plano_id)
    except MeuPlanoPreventiva.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Plano PCM não encontrado'}, status=404)
        messages.error(request, 'Plano PCM não encontrado.')
        return redirect('editar_plano_pcm', plano_id=plano_id)
    
    try:
        documento = MaquinaDocumento.objects.get(id=documento_id)
    except MaquinaDocumento.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Documento não encontrado'}, status=404)
        messages.error(request, 'Documento não encontrado.')
        return redirect('editar_plano_pcm', plano_id=plano_id)
    
    # Verificar se já está associado
    if MeuPlanoPreventivaDocumento.objects.filter(meu_plano_preventiva=plano, maquina_documento=documento).exists():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Este documento já está associado a este plano'}, status=400)
        messages.warning(request, 'Este documento já está associado a este plano.')
        return redirect('editar_plano_pcm', plano_id=plano_id)
    
    # Criar associação
    try:
        comentario = request.POST.get('comentario', '').strip() if request.method == 'POST' else ''
        
        # Debug: imprimir informações
        print(f"Associando documento {documento_id} ao plano {plano_id}")
        print(f"Plano: {plano}")
        print(f"Documento: {documento}")
        print(f"Comentário: {comentario}")
        
        associacao = MeuPlanoPreventivaDocumento.objects.create(
            meu_plano_preventiva=plano,
            maquina_documento=documento,
            comentario=comentario if comentario else None
        )
        
        print(f"Associação criada com sucesso! ID: {associacao.id}")
        
        # Se for requisição AJAX, retornar JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Documento associado com sucesso!',
                'associacao_id': associacao.id
            })
        
        messages.success(request, 'Documento associado com sucesso!')
        return redirect('editar_plano_pcm', plano_id=plano_id)
    except Exception as e:
        import traceback
        print(f"ERRO ao associar documento {documento_id} ao plano {plano_id}:")
        traceback.print_exc()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': f'Erro ao associar documento: {str(e)}'}, status=500)
        messages.error(request, f'Erro ao associar documento: {str(e)}')
        return redirect('editar_plano_pcm', plano_id=plano_id)


def remover_documento_plano_pcm(request, plano_id, associacao_id):
    """Remover associação de documento de um MeuPlanoPreventiva"""
    from app.models import MeuPlanoPreventiva, MeuPlanoPreventivaDocumento
    
    try:
        plano = MeuPlanoPreventiva.objects.get(id=plano_id)
    except MeuPlanoPreventiva.DoesNotExist:
        messages.error(request, 'Plano PCM não encontrado.')
        return redirect('editar_plano_pcm', plano_id=plano_id)
    
    try:
        associacao = MeuPlanoPreventivaDocumento.objects.get(id=associacao_id, meu_plano_preventiva=plano)
        associacao.delete()
        messages.success(request, 'Associação de documento removida com sucesso!')
    except MeuPlanoPreventivaDocumento.DoesNotExist:
        messages.error(request, 'Associação não encontrada.')
    
    return redirect('editar_plano_pcm', plano_id=plano_id)


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


def adicionar_documento_maquina(request, maquina_id):
    """Adicionar documento a uma máquina"""
    from app.models import Maquina, MaquinaDocumento
    import os
    
    print(f"DEBUG - adicionar_documento_maquina chamado. Método: {request.method}, maquina_id: {maquina_id}")
    
    try:
        maquina = Maquina.objects.get(id=maquina_id)
    except Maquina.DoesNotExist:
        print(f"DEBUG - Máquina {maquina_id} não encontrada")
        messages.error(request, 'Máquina não encontrada.')
        return redirect('consultar_maquinas')
    
    if request.method == 'POST':
        print(f"DEBUG - Método POST recebido")
        print(f"DEBUG - request.FILES: {list(request.FILES.keys())}")
        print(f"DEBUG - request.POST: {dict(request.POST)}")
        
        # Verificar se arquivo foi enviado
        if 'arquivo' not in request.FILES:
            print("DEBUG - Arquivo não encontrado em request.FILES")
            messages.error(request, 'Por favor, selecione um arquivo para upload.')
            return redirect('editar_maquina', maquina_id=maquina_id)
        
        arquivo = request.FILES['arquivo']
        comentario = request.POST.get('comentario', '').strip()
        
        print(f"DEBUG - Arquivo recebido: {arquivo.name}, Tamanho: {arquivo.size}, Content-Type: {arquivo.content_type}")
        print(f"DEBUG - Comentário: {comentario}")
        print(f"DEBUG - Máquina ID: {maquina.id}, Máquina: {maquina}")
        
        # Criar documento diretamente
        try:
            documento = MaquinaDocumento(
                maquina=maquina,
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
    
    return redirect('editar_maquina', maquina_id=maquina_id)


def remover_documento_maquina(request, maquina_id, documento_id):
    """Remover documento de uma máquina"""
    from app.models import Maquina, MaquinaDocumento
    import os
    
    try:
        maquina = Maquina.objects.get(id=maquina_id)
    except Maquina.DoesNotExist:
        messages.error(request, 'Máquina não encontrada.')
        return redirect('consultar_maquinas')
    
    try:
        documento = MaquinaDocumento.objects.get(id=documento_id, maquina=maquina)
        # Deletar arquivo físico se existir
        if documento.arquivo:
            if os.path.isfile(documento.arquivo.path):
                os.remove(documento.arquivo.path)
        documento.delete()
        messages.success(request, 'Documento removido com sucesso!')
    except MaquinaDocumento.DoesNotExist:
        messages.error(request, 'Documento não encontrado.')
    
    return redirect('editar_maquina', maquina_id=maquina_id)


def visualizar_maquina(request, maquina_id):
    """Visualizar detalhes de uma máquina específica"""
    from app.models import Maquina, ItemEstoque, MaquinaPeca, MaquinaPrimariaSecundaria, PlanoPreventiva, MaquinaDocumento, MeuPlanoPreventiva
    
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
    
    # Buscar MeuPlanoPreventiva relacionados a esta máquina
    meus_planos_preventiva = MeuPlanoPreventiva.objects.filter(
        Q(maquina=maquina) | Q(cd_maquina=maquina.cd_maquina)
    ).order_by('dt_execucao', 'numero_plano', 'sequencia_manutencao')
    
    # Buscar documentos relacionados a esta máquina
    documentos_maquina = MaquinaDocumento.objects.filter(maquina=maquina).order_by('-created_at')
    
    # Verificar se é máquina principal
    is_maquina_principal = maquina.descr_gerenc and 'MÁQUINAS PRINCIPAL' in maquina.descr_gerenc.upper()
    
    # Se for máquina principal, buscar IDs das máquinas secundárias
    maquinas_secundarias_ids = []
    if is_maquina_principal and relacionamentos_como_primaria.exists():
        maquinas_secundarias_ids = relacionamentos_como_primaria.values_list('maquina_secundaria_id', flat=True)
    
    context = {
        'page_title': f'Visualizar Máquina {maquina.cd_maquina}',
        'active_page': 'consultar_maquinas',
        'maquina': maquina,
        'pecas_relacionadas': pecas_relacionadas,
        'itens_disponiveis': itens_disponiveis,
        'relacionamentos_como_primaria': relacionamentos_como_primaria,
        'relacionamentos_como_secundaria': relacionamentos_como_secundaria,
        'planos_preventiva': planos_preventiva,
        'meus_planos_preventiva': meus_planos_preventiva,
        'documentos_maquina': documentos_maquina,
        'is_maquina_principal': is_maquina_principal,
        'maquinas_secundarias_ids': list(maquinas_secundarias_ids),
    }
    return render(request, 'visualizar/visualizar_maquina.html', context)


def calendario_planos_maquina(request, maquina_id):
    """Endpoint JSON para fornecer eventos do calendário de MeuPlanoPreventiva para uma máquina"""
    from app.models import Maquina, MeuPlanoPreventiva
    from django.http import JsonResponse
    from datetime import datetime
    from django.db.models import Q
    
    try:
        maquina = Maquina.objects.get(id=maquina_id)
    except Maquina.DoesNotExist:
        return JsonResponse({'error': 'Máquina não encontrada'}, status=404)
    
    # Buscar MeuPlanoPreventiva relacionados a esta máquina
    planos = MeuPlanoPreventiva.objects.filter(
        Q(maquina=maquina) | Q(cd_maquina=maquina.cd_maquina)
    ).exclude(
        dt_execucao__isnull=True
    ).exclude(
        dt_execucao=''
    )
    
    # Converter para formato de eventos do FullCalendar
    events = []
    for plano in planos:
        if plano.dt_execucao:
            try:
                # Tentar parsear a data (formato DD/MM/YYYY ou YYYY-MM-DD)
                data_str = plano.dt_execucao.strip()
                if '/' in data_str:
                    # Formato DD/MM/YYYY
                    data_obj = datetime.strptime(data_str, '%d/%m/%Y').date()
                elif '-' in data_str:
                    # Formato YYYY-MM-DD
                    data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
                else:
                    continue  # Pular se não conseguir parsear
                
                # Criar título do evento
                titulo_parts = []
                if plano.numero_plano:
                    titulo_parts.append(f"Plano {plano.numero_plano}")
                if plano.sequencia_manutencao:
                    titulo_parts.append(f"Seq: {plano.sequencia_manutencao}")
                if plano.descr_tarefa:
                    titulo_parts.append(plano.descr_tarefa[:50])
                
                titulo = " - ".join(titulo_parts) if titulo_parts else f"Manutenção Preventiva - {plano.cd_maquina}"
                
                # Criar descrição/tooltip
                descricao_parts = []
                if plano.descr_tarefa:
                    descricao_parts.append(f"Tarefa: {plano.descr_tarefa}")
                if plano.nome_funcionario:
                    descricao_parts.append(f"Funcionário: {plano.nome_funcionario}")
                if plano.descr_setor:
                    descricao_parts.append(f"Setor: {plano.descr_setor}")
                if plano.quantidade_periodo:
                    descricao_parts.append(f"Período: {plano.quantidade_periodo} dias")
                
                descricao = "\n".join(descricao_parts)
                
                # Determinar cor baseada em informações do plano
                cor = '#3788d8'  # Azul padrão
                if plano.quantidade_periodo and plano.quantidade_periodo > 30:
                    cor = '#dc3545'  # Vermelho para períodos longos
                elif plano.quantidade_periodo and plano.quantidade_periodo <= 7:
                    cor = '#28a745'  # Verde para períodos curtos
                
                events.append({
                    'id': plano.id,
                    'title': titulo,
                    'start': data_obj.isoformat(),
                    'allDay': True,
                    'backgroundColor': cor,
                    'borderColor': cor,
                    'textColor': '#ffffff',
                    'extendedProps': {
                        'plano_id': plano.id,
                        'numero_plano': plano.numero_plano,
                        'sequencia_manutencao': plano.sequencia_manutencao,
                        'descricao': descricao,
                        'url': f"/plano-pcm/visualizar/{plano.id}/" if plano.id else None,
                    }
                })
            except (ValueError, AttributeError):
                # Se não conseguir parsear a data, pular este plano
                continue
    
    return JsonResponse(events, safe=False)


def calendario_planos_secundarias(request, maquina_id):
    """Endpoint JSON para fornecer eventos do calendário de MeuPlanoPreventiva para máquinas secundárias de uma máquina principal"""
    from app.models import Maquina, MeuPlanoPreventiva, MaquinaPrimariaSecundaria
    from django.http import JsonResponse
    from datetime import datetime
    from django.db.models import Q
    
    try:
        maquina_principal = Maquina.objects.get(id=maquina_id)
    except Maquina.DoesNotExist:
        return JsonResponse({'error': 'Máquina não encontrada'}, status=404)
    
    # Verificar se é máquina principal
    is_maquina_principal = maquina_principal.descr_gerenc and 'MÁQUINAS PRINCIPAL' in maquina_principal.descr_gerenc.upper()
    
    if not is_maquina_principal:
        return JsonResponse({'error': 'Esta máquina não é uma máquina principal'}, status=400)
    
    # Buscar máquinas secundárias relacionadas
    relacionamentos = MaquinaPrimariaSecundaria.objects.filter(
        maquina_primaria=maquina_principal
    ).select_related('maquina_secundaria')
    
    if not relacionamentos.exists():
        return JsonResponse([], safe=False)  # Retornar lista vazia se não houver máquinas secundárias
    
    # Obter IDs e códigos das máquinas secundárias
    maquinas_secundarias_ids = relacionamentos.values_list('maquina_secundaria_id', flat=True)
    maquinas_secundarias_codigos = relacionamentos.values_list('maquina_secundaria__cd_maquina', flat=True)
    
    # Buscar MeuPlanoPreventiva relacionados às máquinas secundárias
    planos = MeuPlanoPreventiva.objects.filter(
        Q(maquina_id__in=maquinas_secundarias_ids) | Q(cd_maquina__in=maquinas_secundarias_codigos)
    ).exclude(
        dt_execucao__isnull=True
    ).exclude(
        dt_execucao=''
    )
    
    # Converter para formato de eventos do FullCalendar
    events = []
    for plano in planos:
        if plano.dt_execucao:
            try:
                # Tentar parsear a data (formato DD/MM/YYYY ou YYYY-MM-DD)
                data_str = plano.dt_execucao.strip()
                if '/' in data_str:
                    # Formato DD/MM/YYYY
                    data_obj = datetime.strptime(data_str, '%d/%m/%Y').date()
                elif '-' in data_str:
                    # Formato YYYY-MM-DD
                    data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
                else:
                    continue  # Pular se não conseguir parsear
                
                # Criar título do evento (incluir código da máquina secundária)
                titulo_parts = []
                titulo_parts.append(f"Máq: {plano.cd_maquina}")
                if plano.numero_plano:
                    titulo_parts.append(f"Plano {plano.numero_plano}")
                if plano.sequencia_manutencao:
                    titulo_parts.append(f"Seq: {plano.sequencia_manutencao}")
                if plano.descr_tarefa:
                    titulo_parts.append(plano.descr_tarefa[:40])
                
                titulo = " - ".join(titulo_parts) if titulo_parts else f"Manutenção Preventiva - {plano.cd_maquina}"
                
                # Criar descrição/tooltip
                descricao_parts = []
                descricao_parts.append(f"Máquina: {plano.cd_maquina} - {plano.descr_maquina or 'Sem descrição'}")
                if plano.descr_tarefa:
                    descricao_parts.append(f"Tarefa: {plano.descr_tarefa}")
                if plano.nome_funcionario:
                    descricao_parts.append(f"Funcionário: {plano.nome_funcionario}")
                if plano.descr_setor:
                    descricao_parts.append(f"Setor: {plano.descr_setor}")
                if plano.quantidade_periodo:
                    descricao_parts.append(f"Período: {plano.quantidade_periodo} dias")
                
                descricao = "\n".join(descricao_parts)
                
                # Determinar cor baseada em informações do plano (usar cor diferente para distinguir)
                cor = '#6c757d'  # Cinza para máquinas secundárias
                if plano.quantidade_periodo and plano.quantidade_periodo > 30:
                    cor = '#dc3545'  # Vermelho para períodos longos
                elif plano.quantidade_periodo and plano.quantidade_periodo <= 7:
                    cor = '#28a745'  # Verde para períodos curtos
                
                # Buscar ID da máquina relacionada para criar link
                maquina_relacionada_id = None
                if plano.maquina_id:
                    maquina_relacionada_id = plano.maquina_id
                else:
                    # Tentar encontrar pelo código
                    try:
                        maquina_obj = Maquina.objects.get(cd_maquina=plano.cd_maquina)
                        maquina_relacionada_id = maquina_obj.id
                    except Maquina.DoesNotExist:
                        pass
                
                events.append({
                    'id': f'sec_{plano.id}',
                    'title': titulo,
                    'start': data_obj.isoformat(),
                    'allDay': True,
                    'backgroundColor': cor,
                    'borderColor': cor,
                    'textColor': '#ffffff',
                    'extendedProps': {
                        'plano_id': plano.id,
                        'maquina_id': maquina_relacionada_id,
                        'maquina_codigo': plano.cd_maquina,
                        'numero_plano': plano.numero_plano,
                        'sequencia_manutencao': plano.sequencia_manutencao,
                        'descricao': descricao,
                        'url': f"/plano-pcm/visualizar/{plano.id}/" if plano.id else None,
                        'maquina_url': f"/maquinas/visualizar/{maquina_relacionada_id}/" if maquina_relacionada_id else None,
                    }
                })
            except (ValueError, AttributeError):
                # Se não conseguir parsear a data, pular este plano
                continue
    
    return JsonResponse(events, safe=False)


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
    
    # Buscar documentos relacionados à máquina
    from app.models import MaquinaDocumento
    documentos = MaquinaDocumento.objects.filter(maquina=maquina).order_by('-created_at')
    
    context = {
        'page_title': f'Editar Máquina {maquina.cd_maquina}',
        'active_page': 'consultar_maquinas',
        'form': form,
        'maquina': maquina,
        'documentos': documentos,
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


def analise_manutentores(request):
    """Página de análise de manutentores com gráficos e estatísticas"""
    from app.models import Manutentor, ManutentorMaquina, ManutencaoTerceiro, Maquina
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    from collections import defaultdict
    import json
    
    # Estatísticas básicas
    total_count = Manutentor.objects.count()
    
    # Manutentores por turno
    manutentores_por_turno = Manutentor.objects.values('turno').annotate(
        total=Count('Matricula')
    ).order_by('turno')
    
    turnos_labels = [item['turno'] for item in manutentores_por_turno]
    turnos_data = [item['total'] for item in manutentores_por_turno]
    
    # Manutentores por local de trabalho
    manutentores_por_local = Manutentor.objects.values('local_trab').annotate(
        total=Count('Matricula')
    ).order_by('local_trab')
    
    locais_labels = [item['local_trab'] for item in manutentores_por_local]
    locais_data = [item['total'] for item in manutentores_por_local]
    
    # Manutentores por cargo (top 10)
    manutentores_por_cargo = Manutentor.objects.exclude(
        Cargo__isnull=True
    ).exclude(
        Cargo=''
    ).values('Cargo').annotate(
        total=Count('Matricula')
    ).order_by('-total')[:10]
    
    cargos_labels = [item['Cargo'][:30] for item in manutentores_por_cargo]
    cargos_data = [item['total'] for item in manutentores_por_cargo]
    
    # Manutentores com máquinas relacionadas
    manutentores_com_maquinas = Manutentor.objects.filter(
        maquinas__isnull=False
    ).distinct().count()
    
    manutentores_sem_maquinas = total_count - manutentores_com_maquinas
    percentual_com_maquinas = (manutentores_com_maquinas / total_count * 100) if total_count > 0 else 0
    
    # Manutentores com manutenções de terceiros
    manutentores_com_manutencoes = Manutentor.objects.filter(
        manutencaoterceiro__isnull=False
    ).distinct().count()
    
    # Top manutentores por quantidade de máquinas
    top_manutentores_maquinas = Manutentor.objects.annotate(
        total_maquinas=Count('maquinas')
    ).filter(
        total_maquinas__gt=0
    ).order_by('-total_maquinas')[:10]
    
    top_manutentores_maquinas_list = [
        {
            'manutentor': m,
            'total': m.total_maquinas
        }
        for m in top_manutentores_maquinas
    ]
    
    # Top manutentores por quantidade de manutenções de terceiros
    top_manutentores_manutencoes = Manutentor.objects.annotate(
        total_manutencoes=Count('manutencaoterceiro')
    ).filter(
        total_manutencoes__gt=0
    ).order_by('-total_manutencoes')[:10]
    
    top_manutentores_manutencoes_list = [
        {
            'manutentor': m,
            'total': m.total_manutencoes
        }
        for m in top_manutentores_manutencoes
    ]
    
    # Manutentores por mês (últimos 12 meses)
    manutentores_por_mes = defaultdict(int)
    manutentores = Manutentor.objects.all().order_by('created_at')
    for manutentor in manutentores:
        if manutentor.created_at:
            mes_ano = manutentor.created_at.strftime('%Y-%m')
            manutentores_por_mes[mes_ano] += 1
    
    # Ordenar por data e pegar últimos 12 meses
    meses_ordenados = sorted(manutentores_por_mes.keys())[-12:]
    meses_labels = [datetime.strptime(m, '%Y-%m').strftime('%b/%Y') for m in meses_ordenados]
    meses_data = [manutentores_por_mes[m] for m in meses_ordenados]
    
    # Manutentores recentes (últimos 30 dias)
    data_30_dias_atras = datetime.now() - timedelta(days=30)
    manutentores_recentes = Manutentor.objects.filter(
        created_at__gte=data_30_dias_atras
    ).count()
    
    # Manutentores do mês atual
    mes_atual = datetime.now().replace(day=1)
    manutentores_mes_atual = Manutentor.objects.filter(
        created_at__gte=mes_atual
    ).count()
    
    # Distribuição de máquinas por manutentor
    distribuicao_maquinas = Manutentor.objects.annotate(
        total_maquinas=Count('maquinas')
    ).values('total_maquinas').annotate(
        count=Count('Matricula')
    ).order_by('total_maquinas')
    
    distribuicao_maquinas_labels = [f"{item['total_maquinas']} máquina(s)" for item in distribuicao_maquinas]
    distribuicao_maquinas_data = [item['count'] for item in distribuicao_maquinas]
    
    # Total de máquinas relacionadas
    total_maquinas_relacionadas = ManutentorMaquina.objects.count()
    
    # Total de manutenções de terceiros relacionadas
    total_manutencoes_relacionadas = ManutencaoTerceiro.objects.exclude(
        manutentor__isnull=True
    ).count()
    
    context = {
        'page_title': 'Análise de Manutentores',
        'active_page': 'analise_manutentores',
        'total_count': total_count,
        'manutentores_recentes': manutentores_recentes,
        'manutentores_mes_atual': manutentores_mes_atual,
        'manutentores_com_maquinas': manutentores_com_maquinas,
        'manutentores_sem_maquinas': manutentores_sem_maquinas,
        'percentual_com_maquinas': round(percentual_com_maquinas, 1),
        'manutentores_com_manutencoes': manutentores_com_manutencoes,
        'total_maquinas_relacionadas': total_maquinas_relacionadas,
        'total_manutencoes_relacionadas': total_manutencoes_relacionadas,
        # Dados para gráficos (JSON)
        'turnos_labels': json.dumps(turnos_labels),
        'turnos_data': json.dumps(turnos_data),
        'locais_labels': json.dumps(locais_labels),
        'locais_data': json.dumps(locais_data),
        'cargos_labels': json.dumps(cargos_labels),
        'cargos_data': json.dumps(cargos_data),
        'meses_labels': json.dumps(meses_labels),
        'meses_data': json.dumps(meses_data),
        'distribuicao_maquinas_labels': json.dumps(distribuicao_maquinas_labels),
        'distribuicao_maquinas_data': json.dumps(distribuicao_maquinas_data),
        # Dados para tabelas
        'top_manutentores_maquinas': top_manutentores_maquinas_list,
        'top_manutentores_manutencoes': top_manutentores_manutencoes_list,
    }
    return render(request, 'analise/analise_manutentores.html', context)


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
            manutencoes_list = manutencoes_list.filter(manutentor__Matricula=manutentor_id)
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
    ).select_related('manutentor').values_list('manutentor__Matricula', 'manutentor__Nome').distinct().order_by('manutentor__Nome')
    
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
    print(f"\n{'='*80}")
    print(f"VIEW CADASTRAR_MANUTENCAO_TERCEIRO CALLED - Method: {request.method}")
    print(f"URL: {request.path}")
    print(f"{'='*80}\n")
    
    from app.forms import ManutencaoTerceiroForm
    
    if request.method == 'POST':
        print(f"\n{'='*80}")
        print("POST REQUEST RECEBIDO!")
        print(f"POST keys: {list(request.POST.keys())}")
        print(f"POST data: {dict(request.POST)}")
        print(f"{'='*80}\n")
        
        form = ManutencaoTerceiroForm(request.POST)
        
        print(f"\nForm is_valid: {form.is_valid()}")
        if not form.is_valid():
            print(f"\n{'='*60}")
            print("FORMULÁRIO INVÁLIDO!")
            print(f"Erros: {form.errors}")
            print(f"Non-field errors: {form.non_field_errors()}")
            print(f"{'='*60}\n")
        
        if form.is_valid():
            try:
                print("Tentando salvar manutenção terceiro...")
                print(f"Cleaned data: {form.cleaned_data}")
                manutencao = form.save(commit=False)
                print(f"Manutenção objeto criado: {manutencao}")
                print(f"Título: {manutencao.titulo}, Empresa: {manutencao.empresa}")
                manutencao.save()
                print(f"Manutenção salva com sucesso! ID: {manutencao.id}")
                messages.success(request, f'Manutenção de terceiro "{manutencao.titulo}" cadastrada com sucesso!')
                return redirect('home')
            except Exception as e:
                import traceback
                print(f"DEBUG - Erro ao salvar manutenção terceiro: {str(e)}")
                print(f"DEBUG - Traceback: {traceback.format_exc()}")
                messages.error(request, f'Erro ao cadastrar manutenção de terceiro: {str(e)}')
        else:
            # Exibir erros de validação específicos
            print(f"\n{'='*60}")
            print("FORMULÁRIO INVÁLIDO - EXIBINDO ERROS")
            print(f"Total de campos com erro: {len(form.errors)}")
            print(f"Erros: {form.errors}")
            print(f"{'='*60}\n")
            
            missing_required = []
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields else field
                print(f"  Campo '{field}' ({field_label}): {errors}")
                for error in errors:
                    error_str = str(error).lower()
                    if 'required' in error_str or 'obrigatório' in error_str:
                        if field_label not in missing_required:
                            missing_required.append(field_label)
                        messages.warning(request, f'<strong>{field_label}</strong>: Este campo é obrigatório e deve ser preenchido.')
                    else:
                        messages.error(request, f'<strong>{field_label}</strong>: {error}')
            
            # Mostrar erros não relacionados a campos específicos
            if form.non_field_errors():
                print(f"Non-field errors: {form.non_field_errors()}")
                for error in form.non_field_errors():
                    messages.error(request, f'Erro no formulário: {error}')
            
            if missing_required:
                messages.warning(request, f'<strong>Atenção:</strong> {len(missing_required)} campo(s) obrigatório(s) não preenchido(s): {", ".join(missing_required)}. Por favor, preencha todos os campos marcados com <span class="text-danger">*</span>.')
            elif form.errors:
                messages.error(request, 'Por favor, corrija os erros no formulário antes de continuar.')
            else:
                messages.error(request, 'Ocorreu um erro ao processar o formulário. Por favor, tente novamente.')
    else:
        print("GET request - mostrando formulário vazio")
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
                    messages.success(request, f'Manutentor {manutentor.Matricula} cadastrado com sucesso! {maquinas_adicionadas} máquina(s) relacionada(s).')
                else:
                    messages.success(request, f'Manutentor {manutentor.Matricula} cadastrado com sucesso!')
                
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


def visualizar_manutentor(request, matricula):
    """Visualizar detalhes de um manutentor específico"""
    from app.models import Manutentor, ManutentorMaquina, Maquina
    
    try:
        manutentor = Manutentor.objects.get(Matricula=matricula)
    except Manutentor.DoesNotExist:
        messages.error(request, 'Manutentor não encontrado.')
        return redirect('consultar_manutentores')
    
    # Buscar máquinas relacionadas
    maquinas_relacionadas = ManutentorMaquina.objects.filter(manutentor=manutentor).select_related('maquina')
    
    # Buscar máquinas já relacionadas para excluir da lista de disponíveis
    maquinas_ids_relacionadas = maquinas_relacionadas.values_list('maquina_id', flat=True)
    maquinas_disponiveis = Maquina.objects.exclude(id__in=maquinas_ids_relacionadas).order_by('cd_maquina')
    
    context = {
        'page_title': f'Visualizar Manutentor {manutentor.Matricula}',
        'active_page': 'consultar_manutentores',
        'manutentor': manutentor,
        'maquinas_relacionadas': maquinas_relacionadas,
        'maquinas_disponiveis': maquinas_disponiveis,
    }
    return render(request, 'visualizar/visualizar_manutentor.html', context)


def editar_manutentor(request, matricula):
    """Editar um manutentor existente"""
    from app.forms import ManutentorForm
    from app.models import Manutentor, ManutentorMaquina, Maquina
    
    try:
        manutentor = Manutentor.objects.get(Matricula=matricula)
    except Manutentor.DoesNotExist:
        messages.error(request, 'Manutentor não encontrado.')
        return redirect('consultar_manutentores')
    
    # Buscar máquinas relacionadas
    maquinas_relacionadas = ManutentorMaquina.objects.filter(manutentor=manutentor).select_related('maquina')
    
    # Buscar máquinas já relacionadas para excluir da lista de disponíveis
    maquinas_ids_relacionadas = maquinas_relacionadas.values_list('maquina_id', flat=True)
    
    # Buscar apenas máquinas primárias (MÁQUINAS PRINCIPAL) que ainda não estão relacionadas
    maquinas_primarias_disponiveis = Maquina.objects.filter(
        descr_gerenc__iexact='MÁQUINAS PRINCIPAL'
    ).exclude(
        id__in=maquinas_ids_relacionadas
    ).order_by('cd_maquina')
    
    if request.method == 'POST':
        # Garantir que a Matricula não seja alterada (é a primary key)
        post_data = request.POST.copy()
        post_data['Matricula'] = manutentor.Matricula
        
        form = ManutentorForm(post_data, instance=manutentor)
        
        if form.is_valid():
            try:
                manutentor = form.save()
                messages.success(request, f'Manutentor {manutentor.Matricula} atualizado com sucesso!')
                return redirect('visualizar_manutentor', matricula=manutentor.Matricula)
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                print(f"Erro ao salvar manutentor: {error_detail}")
                messages.error(request, f'Erro ao atualizar manutentor: {str(e)}')
        else:
            handle_form_errors(form, request)
    else:
        form = ManutentorForm(instance=manutentor)
        # Tornar o campo Matricula readonly na edição (é a primary key)
        form.fields['Matricula'].widget.attrs['readonly'] = True
        form.fields['Matricula'].widget.attrs['class'] = 'form-control bg-light'
    
    context = {
        'page_title': f'Editar Manutentor {manutentor.Matricula}',
        'active_page': 'consultar_manutentores',
        'form': form,
        'manutentor': manutentor,
        'maquinas_relacionadas': maquinas_relacionadas,
        'maquinas_primarias_disponiveis': maquinas_primarias_disponiveis,
    }
    return render(request, 'editar/editar_manutentor.html', context)


def consultar_manutentores(request):
    """Consultar/listar manutentores cadastrados com filtros avançados"""
    from app.models import Manutentor, TURNO, LOCAL_TRABALHO
    from datetime import datetime
    
    # Buscar todos os manutentores
    manutentores_list = Manutentor.objects.all()
    
    # Filtro de busca geral (texto)
    search_query = request.GET.get('search', '').strip()
    if search_query:
        manutentores_list = manutentores_list.filter(
            Q(Matricula__icontains=search_query) |
            Q(Nome__icontains=search_query) |
            Q(Cargo__icontains=search_query) |
            Q(turno__icontains=search_query) |
            Q(local_trab__icontains=search_query)
        )
    
    # Filtros específicos
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
    
    # Ordenar por nome e matricula
    manutentores_list = manutentores_list.order_by('Nome', 'Matricula')
    
    # Paginação
    paginator = Paginator(manutentores_list, 50)  # 50 itens por página
    page_number = request.GET.get('page', 1)
    manutentores = paginator.get_page(page_number)
    
    # Estatísticas
    total_count = Manutentor.objects.count()
    turnos_count = Manutentor.objects.exclude(turno__isnull=True).exclude(turno='').values('turno').distinct().count()
    locais_count = Manutentor.objects.exclude(local_trab__isnull=True).exclude(local_trab='').values('local_trab').distinct().count()
    
    # Obter valores únicos para os dropdowns de filtros
    cargos_unicos = Manutentor.objects.exclude(
        Cargo__isnull=True
    ).exclude(
        Cargo=''
    ).values_list('Cargo', flat=True).distinct().order_by('Cargo')
    
    
    context = {
        'page_title': 'Consultar Manutentores',
        'active_page': 'consultar_manutentores',
        'manutentores': manutentores,
        'total_count': total_count,
        'turnos_count': turnos_count,
        'locais_count': locais_count,
        # Valores para dropdowns
        'turnos': TURNO,
        'locais_trabalho': LOCAL_TRABALHO,
        'cargos_unicos': cargos_unicos,
        # Valores dos filtros ativos
        'filtro_turno': filtro_turno,
        'filtro_local_trab': filtro_local_trab,
        'filtro_cargo': filtro_cargo,
    }
    return render(request, 'consultar/consultar_manutentores.html', context)


def consultar_agendamentos(request):
    """Consultar/listar agendamentos de cronograma cadastrados com visitas"""
    from app.models import AgendamentoCronograma, Visitas
    from django.db.models import Q
    from django.core.paginator import Paginator
    from datetime import datetime
    
    # Buscar todos os agendamentos com visitas relacionadas
    agendamentos_list = AgendamentoCronograma.objects.select_related('maquina', 'plano_preventiva', 'semana').prefetch_related('visitas').all()
    
    # Filtro de busca geral (incluindo campos de visitas)
    search_query = request.GET.get('search', '').strip()
    if search_query:
        agendamentos_list = agendamentos_list.filter(
            Q(nome_grupo__icontains=search_query) |
            Q(maquina__cd_maquina__icontains=search_query) |
            Q(maquina__descr_maquina__icontains=search_query) |
            Q(plano_preventiva__numero_plano__icontains=search_query) |
            Q(plano_preventiva__descr_plano__icontains=search_query) |
            Q(observacoes__icontains=search_query) |
            Q(visitas__titulo__icontains=search_query) |
            Q(visitas__descricao__icontains=search_query) |
            Q(visitas__nome_contato__icontains=search_query)
        ).distinct()
    
    # Filtros específicos
    filtro_tipo = request.GET.get('filtro_tipo', '')
    if filtro_tipo:
        agendamentos_list = agendamentos_list.filter(tipo_agendamento=filtro_tipo)
    
    filtro_data_inicio = request.GET.get('filtro_data_inicio', '')
    if filtro_data_inicio:
        try:
            data_ini = datetime.strptime(filtro_data_inicio, '%Y-%m-%d').date()
            agendamentos_list = agendamentos_list.filter(data_planejada__gte=data_ini)
        except ValueError:
            pass
    
    filtro_data_fim = request.GET.get('filtro_data_fim', '')
    if filtro_data_fim:
        try:
            data_f = datetime.strptime(filtro_data_fim, '%Y-%m-%d').date()
            agendamentos_list = agendamentos_list.filter(data_planejada__lte=data_f)
        except ValueError:
            pass
    
    # Ordenar por data planejada
    agendamentos_list = agendamentos_list.order_by('data_planejada', 'tipo_agendamento')
    
    # Paginação
    paginator = Paginator(agendamentos_list, 50)  # 50 itens por página
    page_number = request.GET.get('page', 1)
    agendamentos = paginator.get_page(page_number)
    
    # Estatísticas
    total_count = AgendamentoCronograma.objects.count()
    tipo_maquina_count = AgendamentoCronograma.objects.filter(tipo_agendamento='maquina').count()
    tipo_plano_count = AgendamentoCronograma.objects.filter(tipo_agendamento='plano').count()
    visitas_count = Visitas.objects.count()
    
    context = {
        'page_title': 'Consultar Agendamentos',
        'active_page': 'consultar_agendamentos',
        'agendamentos': agendamentos,
        'total_count': total_count,
        'tipo_maquina_count': tipo_maquina_count,
        'tipo_plano_count': tipo_plano_count,
        'visitas_count': visitas_count,
        'filtro_tipo': filtro_tipo,
        'filtro_data_inicio': filtro_data_inicio,
        'filtro_data_fim': filtro_data_fim,
        'search_query': search_query,
    }
    return render(request, 'consultar/consultar_agendamentos.html', context)


def consultar_visitas(request):
    """Consultar/listar visitas cadastradas"""
    from app.models import Visitas
    from django.db.models import Q
    from django.core.paginator import Paginator
    from datetime import datetime
    
    # Buscar todas as visitas
    visitas_list = Visitas.objects.all()
    
    # Filtro de busca geral
    search_query = request.GET.get('search', '').strip()
    if search_query:
        visitas_list = visitas_list.filter(
            Q(titulo__icontains=search_query) |
            Q(descricao__icontains=search_query) |
            Q(nome_contato__icontains=search_query) |
            Q(numero_contato__icontains=search_query)
        )
    
    # Filtros específicos
    filtro_data_inicio = request.GET.get('filtro_data_inicio', '')
    if filtro_data_inicio:
        try:
            data_ini = datetime.strptime(filtro_data_inicio, '%Y-%m-%d').date()
            visitas_list = visitas_list.filter(data__date__gte=data_ini)
        except ValueError:
            pass
    
    filtro_data_fim = request.GET.get('filtro_data_fim', '')
    if filtro_data_fim:
        try:
            data_f = datetime.strptime(filtro_data_fim, '%Y-%m-%d').date()
            visitas_list = visitas_list.filter(data__date__lte=data_f)
        except ValueError:
            pass
    
    # Ordenar por data (mais recente primeiro)
    visitas_list = visitas_list.order_by('-data', '-created_at')
    
    # Paginação
    paginator = Paginator(visitas_list, 50)  # 50 itens por página
    page_number = request.GET.get('page', 1)
    visitas = paginator.get_page(page_number)
    
    # Estatísticas
    total_count = Visitas.objects.count()
    com_documentos_count = Visitas.objects.exclude(documento__isnull=True).exclude(documento='').count()
    com_contato_count = Visitas.objects.exclude(nome_contato__isnull=True).exclude(nome_contato='').count()
    
    context = {
        'page_title': 'Consultar Visitas',
        'active_page': 'consultar_visitas',
        'visitas': visitas,
        'total_count': total_count,
        'com_documentos_count': com_documentos_count,
        'com_contato_count': com_contato_count,
        'filtro_data_inicio': filtro_data_inicio,
        'filtro_data_fim': filtro_data_fim,
        'search_query': search_query,
    }
    return render(request, 'consultar/consultar_visitas.html', context)


def consultar_notas_fiscais(request):
    """Consultar/listar notas fiscais cadastradas"""
    from app.models import NotaFiscal
    from django.db.models import Q, Sum
    from django.core.paginator import Paginator
    from decimal import Decimal
    
    # Buscar todas as notas fiscais
    notas_list = NotaFiscal.objects.all()
    
    # Filtro de busca geral
    search_query = request.GET.get('search', '').strip()
    if search_query:
        notas_list = notas_list.filter(
            Q(nota__icontains=search_query) |
            Q(serie__icontains=search_query) |
            Q(emitente__icontains=search_query) |
            Q(nome_fantasia_emitente__icontains=search_query) |
            Q(unidade__icontains=search_query) |
            Q(nome_unidade__icontains=search_query) |
            Q(centro_atividade__icontains=search_query) |
            Q(nome_centro_atividade__icontains=search_query) |
            Q(situacao__icontains=search_query) |
            Q(observacoes__icontains=search_query)
        )
    
    # Filtros específicos
    filtro_emitente = request.GET.get('filtro_emitente', '')
    if filtro_emitente:
        notas_list = notas_list.filter(emitente__icontains=filtro_emitente)
    
    filtro_unidade = request.GET.get('filtro_unidade', '')
    if filtro_unidade:
        notas_list = notas_list.filter(unidade__icontains=filtro_unidade)
    
    filtro_situacao = request.GET.get('filtro_situacao', '')
    if filtro_situacao:
        notas_list = notas_list.filter(situacao__icontains=filtro_situacao)
    
    filtro_total_min = request.GET.get('filtro_total_min', '')
    if filtro_total_min:
        try:
            total_min = Decimal(filtro_total_min)
            notas_list = notas_list.filter(total_nota__gte=total_min)
        except (ValueError, TypeError):
            pass
    
    filtro_total_max = request.GET.get('filtro_total_max', '')
    if filtro_total_max:
        try:
            total_max = Decimal(filtro_total_max)
            notas_list = notas_list.filter(total_nota__lte=total_max)
        except (ValueError, TypeError):
            pass
    
    # Ordenar por data de emissão (mais recente primeiro) ou por número da nota
    notas_list = notas_list.order_by('-data_emissao', '-nota', '-created_at')
    
    # Paginação
    paginator = Paginator(notas_list, 50)  # 50 itens por página
    page_number = request.GET.get('page', 1)
    notas = paginator.get_page(page_number)
    
    # Estatísticas
    total_count = NotaFiscal.objects.count()
    total_valor = NotaFiscal.objects.aggregate(total=Sum('total_nota'))['total'] or Decimal('0.00')
    situacoes_count = NotaFiscal.objects.values('situacao').distinct().count()
    unidades_count = NotaFiscal.objects.values('unidade').distinct().count()
    
    context = {
        'page_title': 'Consultar Notas Fiscais',
        'active_page': 'consultar_notas_fiscais',
        'notas': notas,
        'total_count': total_count,
        'total_valor': total_valor,
        'situacoes_count': situacoes_count,
        'unidades_count': unidades_count,
        'filtro_emitente': filtro_emitente,
        'filtro_unidade': filtro_unidade,
        'filtro_situacao': filtro_situacao,
        'filtro_total_min': filtro_total_min,
        'filtro_total_max': filtro_total_max,
        'search_query': search_query,
    }
    return render(request, 'consultar/consultar_notas_fiscais.html', context)


def visualizar_nota_fiscal(request, nota_id):
    """Visualizar detalhes completos de uma Nota Fiscal"""
    from app.models import NotaFiscal
    
    try:
        nota = NotaFiscal.objects.get(id=nota_id)
    except NotaFiscal.DoesNotExist:
        messages.error(request, 'Nota Fiscal não encontrada.')
        return redirect('consultar_notas_fiscais')
    
    context = {
        'page_title': f'Visualizar Nota Fiscal {nota.nota or nota.id}',
        'active_page': 'consultar_notas_fiscais',
        'nota': nota,
    }
    return render(request, 'visualizar/visualizar_nota_fiscal.html', context)


def cadastrar_visita(request):
    """Cadastrar nova visita"""
    print(f"\n{'='*80}")
    print(f"VIEW CADASTRAR_VISITA CALLED - Method: {request.method}")
    print(f"URL: {request.path}")
    print(f"{'='*80}\n")
    
    from app.forms import VisitasForm
    from app.models import Visitas
    
    if request.method == 'POST':
        print(f"\n{'='*60}")
        print("DEBUG - POST request recebido")
        print(f"POST data: {dict(request.POST)}")
        print(f"FILES data: {dict(request.FILES)}")
        print(f"{'='*60}\n")
        
        form = VisitasForm(request.POST, request.FILES)
        
        print(f"Form is_valid: {form.is_valid()}")
        if not form.is_valid():
            print(f"Form errors: {form.errors}")
            print(f"Form data: {form.data}")
            print(f"Form cleaned_data: {form.cleaned_data if hasattr(form, 'cleaned_data') else 'N/A'}")
        
        if form.is_valid():
            try:
                print("Tentando salvar visita...")
                print(f"Cleaned data: {form.cleaned_data}")
                visita = form.save(commit=False)
                print(f"Visita objeto criado: {visita}")
                print(f"Título: {visita.titulo}")
                visita.save()
                print(f"Visita salva com sucesso! ID: {visita.id}, Título: {visita.titulo}")
                messages.success(request, f'Visita "{visita.titulo}" cadastrada com sucesso!')
                return redirect('consultar_visitas')
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"\n{'='*60}")
                print(f"DEBUG - Erro ao salvar visita: {str(e)}")
                print(f"DEBUG - Traceback: {error_details}")
                print(f"{'='*60}\n")
                messages.error(request, f'Erro ao cadastrar visita: {str(e)}')
        else:
            # Usar helper function para exibir erros
            print(f"\n{'='*60}")
            print("Formulário inválido!")
            print(f"Erros: {form.errors}")
            print(f"{'='*60}\n")
            handle_form_errors(form, request)
            # Mostrar erros não relacionados a campos específicos
            if form.non_field_errors():
                for error in form.non_field_errors():
                    messages.error(request, f'Erro no formulário: {error}')
    else:
        form = VisitasForm()
    
    context = {
        'page_title': 'Cadastrar Visita',
        'active_page': 'cadastrar_visita',
        'form': form
    }
    return render(request, 'cadastrar/cadastrar_visita.html', context)


def gerenciar_projeto(request):
    """Página de gerenciamento administrativo do projeto"""
    from app.models import (
        Maquina, MaquinaDocumento, OrdemServicoCorretiva, OrdemServicoCorretivaFicha,
        CentroAtividade, LocalCentroAtividade, Semana52, Manutentor, ManutentorMaquina,
        ItemEstoque, ManutencaoCsv, ManutencaoTerceiro, MaquinaPeca,
        MaquinaPrimariaSecundaria, PlanoPreventiva, PlanoPreventivaDocumento,
        MeuPlanoPreventiva, MeuPlanoPreventivaDocumento, AgendamentoCronograma,
        RoteiroPreventiva, RequisicaoAlmoxarifado, NotaFiscal, Visitas
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
        {
            'nome': 'Meus Planos Preventiva',
            'modelo': MeuPlanoPreventiva,
            'key': 'meu_plano_preventiva',
            'icone': 'fas fa-calendar-alt',
            'cor': 'info',
            'descricao': 'Planos preventiva com descrição detalhada do roteiro'
        },
        {
            'nome': 'Roteiros Preventiva',
            'modelo': RoteiroPreventiva,
            'key': 'roteiro_preventiva',
            'icone': 'fas fa-route',
            'cor': 'primary',
            'descricao': 'Roteiros de manutenção preventiva'
        },
        {
            'nome': 'Documentos das Máquinas',
            'modelo': MaquinaDocumento,
            'key': 'maquina_documento',
            'icone': 'fas fa-file-pdf',
            'cor': 'primary',
            'descricao': 'Documentos relacionados às máquinas'
        },
        {
            'nome': 'Semanas 52',
            'modelo': Semana52,
            'key': 'semana52',
            'icone': 'fas fa-calendar-week',
            'cor': 'info',
            'descricao': 'Semanas do ano (52 semanas)'
        },
        {
            'nome': 'Documentos Meus Planos Preventiva',
            'modelo': MeuPlanoPreventivaDocumento,
            'key': 'meu_plano_preventiva_documento',
            'icone': 'fas fa-file-alt',
            'cor': 'info',
            'descricao': 'Documentos associados aos planos PCM'
        },
        {
            'nome': 'Agendamentos Cronograma',
            'modelo': AgendamentoCronograma,
            'key': 'agendamento_cronograma',
            'icone': 'fas fa-calendar-day',
            'cor': 'success',
            'descricao': 'Agendamentos de máquinas e planos no cronograma'
        },
        {
            'nome': 'Requisições Almoxarifado',
            'modelo': RequisicaoAlmoxarifado,
            'key': 'requisicao_almoxarifado',
            'icone': 'fas fa-shopping-cart',
            'cor': 'warning',
            'descricao': 'Requisições de itens retirados do almoxarifado'
        },
        {
            'nome': 'Notas Fiscais',
            'modelo': NotaFiscal,
            'key': 'nota_fiscal',
            'icone': 'fas fa-file-invoice-dollar',
            'cor': 'info',
            'descricao': 'Notas fiscais cadastradas no sistema'
        },
        {
            'nome': 'Visitas',
            'modelo': Visitas,
            'key': 'visitas',
            'icone': 'fas fa-calendar-check',
            'cor': 'success',
            'descricao': 'Visitas e agendamentos cadastrados'
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
    # Buscar pelos keys específicos para garantir que pegamos os valores corretos
    maquinas_count = next((t['count'] for t in tabelas_info if t['key'] == 'maquinas'), 0)
    ordens_count = next((t['count'] for t in tabelas_info if t['key'] == 'ordens'), 0)
    centros_count = next((t['count'] for t in tabelas_info if t['key'] == 'centros'), 0)
    manutentores_count = next((t['count'] for t in tabelas_info if t['key'] == 'manutentores'), 0)
    
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
        Maquina, MaquinaDocumento, OrdemServicoCorretiva, OrdemServicoCorretivaFicha,
        CentroAtividade, LocalCentroAtividade, Semana52, Manutentor, ManutentorMaquina,
        ItemEstoque, ManutencaoCsv, ManutencaoTerceiro, MaquinaPeca,
        MaquinaPrimariaSecundaria, PlanoPreventiva, PlanoPreventivaDocumento,
        MeuPlanoPreventiva, MeuPlanoPreventivaDocumento, AgendamentoCronograma,
        RoteiroPreventiva, RequisicaoAlmoxarifado, NotaFiscal, Visitas
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
        'meu_plano_preventiva': {'modelo': MeuPlanoPreventiva, 'nome': 'Meus Planos Preventiva'},
        'roteiro_preventiva': {'modelo': RoteiroPreventiva, 'nome': 'Roteiros Preventiva'},
        'maquina_documento': {'modelo': MaquinaDocumento, 'nome': 'Documentos das Máquinas'},
        'semana52': {'modelo': Semana52, 'nome': 'Semanas 52'},
        'meu_plano_preventiva_documento': {'modelo': MeuPlanoPreventivaDocumento, 'nome': 'Documentos Meus Planos Preventiva'},
        'agendamento_cronograma': {'modelo': AgendamentoCronograma, 'nome': 'Agendamentos Cronograma'},
        'requisicao_almoxarifado': {'modelo': RequisicaoAlmoxarifado, 'nome': 'Requisições Almoxarifado'},
        'nota_fiscal': {'modelo': NotaFiscal, 'nome': 'Notas Fiscais'},
        'visitas': {'modelo': Visitas, 'nome': 'Visitas'},
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


def adicionar_maquina_manutentor(request, matricula):
    """Adicionar uma ou múltiplas máquinas a um manutentor"""
    from app.models import Manutentor, ManutentorMaquina, Maquina
    from django.db import IntegrityError, transaction
    
    print(f"=== ADICIONAR MAQUINA MANUTENTOR ===")
    print(f"Method: {request.method}")
    print(f"Matricula: {matricula}")
    print(f"POST data: {request.POST}")
    print(f"POST keys: {list(request.POST.keys())}")
    
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('editar_manutentor', matricula=matricula)
    
    try:
        manutentor = Manutentor.objects.get(Matricula=matricula)
    except Manutentor.DoesNotExist:
        messages.error(request, 'Manutentor não encontrado.')
        return redirect('consultar_manutentores')
    
    # Obter máquina primária e máquinas secundárias selecionadas
    maquina_primaria_id = request.POST.get('maquina_primaria')
    maquinas_secundarias_ids = request.POST.getlist('maquinas_secundarias')
    observacoes = request.POST.get('observacoes', '').strip()
    
    print(f"maquina_primaria_id: {maquina_primaria_id}")
    print(f"maquinas_secundarias_ids: {maquinas_secundarias_ids}")
    print(f"observacoes: {observacoes}")
    
    if not maquina_primaria_id:
        messages.error(request, 'Por favor, selecione uma máquina primária.')
        return redirect('editar_manutentor', matricula=matricula)
    
    if not maquinas_secundarias_ids:
        messages.error(request, 'Por favor, selecione pelo menos uma máquina secundária.')
        return redirect('editar_manutentor', matricula=matricula)
    
    # Processar todas as máquinas em uma transação
    sucesso_count = 0
    ja_existente_count = 0
    erro_count = 0
    maquinas_nao_encontradas = []
    
    try:
        with transaction.atomic():
            # Primeiro, adicionar a máquina primária
            try:
                maquina_primaria = Maquina.objects.get(id=maquina_primaria_id)
                
                # Verificar se já existe relação com a primária
                if ManutentorMaquina.objects.filter(manutentor=manutentor, maquina=maquina_primaria).exists():
                    ja_existente_count += 1
                else:
                    # Criar relação com a máquina primária
                    try:
                        relacionamento = ManutentorMaquina.objects.create(
                            manutentor=manutentor,
                            maquina=maquina_primaria,
                            observacoes=observacoes if observacoes else None
                        )
                        print(f"Relacionamento criado (primária): {relacionamento}")
                        sucesso_count += 1
                    except IntegrityError as ie:
                        print(f"IntegrityError ao criar relacionamento (primária): {ie}")
                        ja_existente_count += 1
                    except Exception as create_error:
                        print(f"Erro ao criar relacionamento (primária): {create_error}")
                        raise create_error
            except Maquina.DoesNotExist:
                maquinas_nao_encontradas.append(maquina_primaria_id)
                erro_count += 1
                messages.error(request, 'Máquina primária não encontrada.')
                return redirect('editar_manutentor', matricula=matricula)
            
            # Depois, adicionar todas as máquinas secundárias
            for maquina_secundaria_id in maquinas_secundarias_ids:
                try:
                    maquina_secundaria = Maquina.objects.get(id=maquina_secundaria_id)
                    
                    # Verificar se já existe relação
                    if ManutentorMaquina.objects.filter(manutentor=manutentor, maquina=maquina_secundaria).exists():
                        ja_existente_count += 1
                    else:
                        # Criar relação
                        try:
                            relacionamento = ManutentorMaquina.objects.create(
                                manutentor=manutentor,
                                maquina=maquina_secundaria,
                                observacoes=observacoes if observacoes else None
                            )
                            print(f"Relacionamento criado (secundária): {relacionamento}")
                            sucesso_count += 1
                        except IntegrityError as ie:
                            print(f"IntegrityError ao criar relacionamento (secundária): {ie}")
                            ja_existente_count += 1
                        except Exception as create_error:
                            print(f"Erro ao criar relacionamento (secundária): {create_error}")
                            raise create_error
                
                except Maquina.DoesNotExist:
                    maquinas_nao_encontradas.append(maquina_secundaria_id)
                    erro_count += 1
                except Exception as e:
                    erro_count += 1
                    print(f"Erro ao adicionar máquina secundária {maquina_secundaria_id}: {str(e)}")
        
        # Mensagens de resultado
        if sucesso_count > 0:
            messages.success(request, f'{sucesso_count} máquina(s) adicionada(s) com sucesso ao manutentor {manutentor.Matricula}.')
        
        if ja_existente_count > 0:
            messages.warning(request, f'{ja_existente_count} máquina(s) já estavam relacionadas ao manutentor.')
        
        if erro_count > 0 and maquinas_nao_encontradas:
            messages.error(request, f'{erro_count} máquina(s) não foram encontradas.')
        elif erro_count > 0:
            messages.error(request, f'Erro ao adicionar {erro_count} máquina(s).')
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        messages.error(request, f'Erro ao adicionar máquinas: {str(e)}')
        print(f"Erro ao adicionar máquinas: {error_detail}")  # Debug
    
    return redirect('editar_manutentor', matricula=matricula)


def get_maquinas_secundarias(request, maquina_primaria_id):
    """AJAX endpoint para obter máquinas secundárias de uma máquina primária"""
    from app.models import Maquina, MaquinaPrimariaSecundaria, Manutentor, ManutentorMaquina
    from django.http import JsonResponse
    
    try:
        maquina_primaria = Maquina.objects.get(id=maquina_primaria_id)
        
        # Verificar se é realmente uma máquina primária
        if not maquina_primaria.descr_gerenc or 'MÁQUINAS PRINCIPAL' not in maquina_primaria.descr_gerenc.upper():
            return JsonResponse({'error': 'Máquina não é uma máquina primária'}, status=400)
        
        # Buscar máquinas secundárias relacionadas
        relacionamentos = MaquinaPrimariaSecundaria.objects.filter(
            maquina_primaria=maquina_primaria
        ).select_related('maquina_secundaria')
        
        # Se houver matricula na query string, excluir máquinas já relacionadas ao manutentor
        matricula = request.GET.get('matricula')
        maquinas_secundarias_ids_relacionadas = []
        if matricula:
            try:
                manutentor = Manutentor.objects.get(Matricula=matricula)
                maquinas_secundarias_ids_relacionadas = ManutentorMaquina.objects.filter(
                    manutentor=manutentor
                ).values_list('maquina_id', flat=True)
            except Manutentor.DoesNotExist:
                pass
        
        # Montar lista de máquinas secundárias
        maquinas_secundarias = []
        for rel in relacionamentos:
            maquina_sec = rel.maquina_secundaria
            # Excluir se já estiver relacionada ao manutentor
            if maquina_sec.id not in maquinas_secundarias_ids_relacionadas:
                maquinas_secundarias.append({
                    'id': maquina_sec.id,
                    'cd_maquina': maquina_sec.cd_maquina,
                    'descr_maquina': maquina_sec.descr_maquina or '',
                    'descr_setormanut': maquina_sec.descr_setormanut or '',
                    'texto': f"{maquina_sec.cd_maquina} - {maquina_sec.descr_maquina or 'Sem descrição'}{' (' + maquina_sec.descr_setormanut + ')' if maquina_sec.descr_setormanut else ''}"
                })
        
        return JsonResponse({
            'maquinas_secundarias': maquinas_secundarias,
            'total': len(maquinas_secundarias)
        })
        
    except Maquina.DoesNotExist:
        return JsonResponse({'error': 'Máquina primária não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def remover_maquina_manutentor(request, matricula, manutentor_maquina_id):
    """Remover uma máquina de um manutentor"""
    from app.models import Manutentor, ManutentorMaquina
    
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('visualizar_manutentor', matricula=matricula)
    
    try:
        manutentor = Manutentor.objects.get(Matricula=matricula)
    except Manutentor.DoesNotExist:
        messages.error(request, 'Manutentor não encontrado.')
        return redirect('consultar_manutentores')
    
    try:
        manutentor_maquina = ManutentorMaquina.objects.get(id=manutentor_maquina_id, manutentor=manutentor)
        maquina_codigo = manutentor_maquina.maquina.cd_maquina
        manutentor_maquina.delete()
        messages.success(request, f'Máquina "{maquina_codigo}" removida com sucesso do manutentor {manutentor.Matricula}.')
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