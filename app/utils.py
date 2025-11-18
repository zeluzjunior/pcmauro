"""
Utility functions for file uploads and data processing
"""
import csv
import io
from typing import List, Dict, Tuple
from django.core.exceptions import ValidationError
from django.db import transaction
import openpyxl


def read_excel_file(file, sheet_name=None):
    """
    Lê um arquivo Excel (.xlsx, .xls, .xlsm) e retorna os dados
    
    Args:
        file: Arquivo Excel (Django UploadedFile ou path)
        sheet_name: Nome da planilha a ser lida (None para primeira planilha)
    
    Returns:
        Lista de dicionários com os dados
    """
    try:
        # Se for um arquivo Django UploadedFile, garantir que está no início
        if hasattr(file, 'read'):
            file.seek(0)  # Resetar para o início do arquivo
            wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
        else:
            wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
        
        # Selecionar a planilha
        if sheet_name:
            ws = wb[sheet_name]
        else:
            ws = wb.active
        
        # Ler cabeçalhos da primeira linha
        headers = []
        for cell in ws[1]:
            headers.append(cell.value if cell.value else f'col_{len(headers)}')
        
        # Ler dados
        data = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if any(cell is not None for cell in row):  # Ignorar linhas vazias
                row_dict = {}
                for i, value in enumerate(row):
                    if i < len(headers):
                        row_dict[headers[i]] = value
                data.append(row_dict)
        
        wb.close()
        return data
    
    except Exception as e:
        raise ValidationError(f"Erro ao ler arquivo Excel: {str(e)}")


def read_csv_file(file, encoding='utf-8', delimiter=','):
    """
    Lê um arquivo CSV e retorna os dados
    
    Args:
        file: Arquivo CSV (Django UploadedFile)
        encoding: Codificação do arquivo (padrão: utf-8)
        delimiter: Delimitador CSV (padrão: ,)
    
    Returns:
        Lista de dicionários com os dados
    """
    try:
        # Decodificar o arquivo
        if hasattr(file, 'read'):
            file.seek(0)  # Resetar para o início do arquivo
            content = file.read()
            if isinstance(content, bytes):
                content = content.decode(encoding)
        else:
            with open(file, 'r', encoding=encoding) as f:
                content = f.read()
        
        # Ler CSV
        csv_reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        data = []
        for row in csv_reader:
            # Converter valores vazios para None
            cleaned_row = {k: (v if v else None) for k, v in row.items()}
            data.append(cleaned_row)
        
        return data
    
    except UnicodeDecodeError as e:
        # Relançar UnicodeDecodeError para permitir tentar com outra codificação
        raise e
    except Exception as e:
        raise ValidationError(f"Erro ao ler arquivo CSV: {str(e)}")


def normalize_column_name(name):
    """
    Normaliza o nome de uma coluna para facilitar o mapeamento
    
    Args:
        name: Nome da coluna original
    
    Returns:
        Nome normalizado
    """
    # Mapeamento de variações comuns
    # IMPORTANTE: Ordem importa! Mapeamentos mais específicos devem vir primeiro
    mapping = {
        # Mapeamentos para CA (Centro de Atividade) - devem vir primeiro
        'ca': ['ca', 'centro_atividade', 'centro de atividade', 'codigo_ca', 'cod_ca'],
        'sigla': ['sigla', 'abreviatura', 'abrev'],
        'descricao': ['descricao', 'descrição', 'desc', 'descr'],
        'indice': ['indice', 'índice', 'index', 'idx'],
        'encarregado_responsavel': ['encarregado_responsavel', 'encarregado responsável', 'encarregado', 'responsavel', 'responsável', 'encarregado_responsável'],
        'local': ['local', 'loc', 'localizacao', 'localização'],
        # Mapeamentos para Máquinas
        'cd_unid': ['cd_unid', 'codigo_unidade', 'cod_unidade', 'unidade'],
        'nome_unid': ['nome_unid', 'nome_unidade', 'nome da unidade'],
        'cs_tt_maquina': ['cs_tt_maquina', 'codigo_total_maquina', 'cod_total_maq'],
        'descr_maquina': ['descr_maquina', 'descricao_maquina', 'descrição máquina'],
        'cd_maquina': ['cd_maquina', 'codigo_maquina', 'cod_maquina', 'codigo da máquina', 'código máquina'],
        'cd_setormanut': ['cd_setormanut', 'codigo_setor_manutencao', 'setor', 'cod_setor'],
        'descr_setormanut': ['descr_setormanut', 'descricao_setor', 'descrição setor'],
        'cd_priomaqutv': ['cd_priomaqutv', 'codigo_prioridade', 'prioridade', 'cod_prioridade'],
        'nro_patrimonio': ['nro_patrimonio', 'numero_patrimonio', 'patrimônio', 'patrimonio', 'nº patrimônio'],
        'cd_modelo': ['cd_modelo', 'codigo_modelo', 'modelo', 'cod_modelo'],
        'cd_grupo': ['cd_grupo', 'codigo_grupo', 'grupo', 'cod_grupo'],
        'cd_tpcentativ': ['cd_tpcentativ', 'codigo_tipo_centro', 'tipo_centro', 'cod_tipo_centro'],
        'descr_gerenc': ['descr_gerenc', 'descricao_gerencia', 'gerência', 'gerencia', 'descrição gerência'],
    }
    
    # Normalizar nome (lowercase, remover espaços extras)
    normalized = str(name).strip().lower().replace(' ', '_')
    
    # Procurar correspondência exata primeiro
    for key, variations in mapping.items():
        normalized_variations = [str(v).lower().replace(' ', '_') for v in variations]
        if normalized in normalized_variations:
            return key
    
    # Se não encontrar correspondência exata, tentar correspondência parcial
    # (para lidar com problemas de encoding como "descrio" vs "descricao")
    # Verificar se começa com "desc" mas não contém "maquina"
    if normalized.startswith('desc') and 'maquina' not in normalized and 'maq' not in normalized:
        # Pode ser "descricao", "descrio", "descr", etc. - todos devem ser "descricao" para CA
        return 'descricao'
    
    # Verificar se começa com "encarregado" ou "encarregado_responsavel"
    if normalized.startswith('encarregado'):
        return 'encarregado_responsavel'
    
    # Se não encontrar, retornar normalizado
    return normalized


def upload_ordens_corretivas_from_file(file, update_existing=False) -> Tuple[int, int, List[str]]:
    """
    Faz upload de ordens corretivas a partir de um arquivo CSV
    
    Args:
        file: Arquivo Django UploadedFile
        update_existing: Se True, atualiza registros existentes. Se False, ignora duplicados.
    
    Returns:
        Tupla (created_count, updated_count, errors)
    """
    from app.models import OrdemServicoCorretiva, OrdemServicoCorretivaFicha
    
    errors = []
    created_count = 0
    updated_count = 0
    
    # Determinar tipo de arquivo
    file_name = file.name.lower()
    
    try:
        # Ler arquivo baseado na extensão
        if file_name.endswith(('.xlsx', '.xls', '.xlsm')):
            data = read_excel_file(file)
        elif file_name.endswith('.csv'):
            # Tentar diferentes encodings
            try:
                data = read_csv_file(file, encoding='utf-8', delimiter=';')
            except UnicodeDecodeError:
                try:
                    file.seek(0)  # Resetar arquivo
                    data = read_csv_file(file, encoding='latin-1', delimiter=';')
                except Exception as e:
                    raise ValidationError(f"Erro ao ler arquivo CSV: {str(e)}")
        else:
            raise ValidationError("Formato de arquivo não suportado. Use .xlsx, .xls, .xlsm ou .csv")
        
        if not data:
            raise ValidationError("Arquivo vazio ou sem dados válidos")
        
        # Processar dados em transação
        with transaction.atomic():
            for row_num, row_data in enumerate(data, start=2):  # Começar em 2 (linha 1 é cabeçalho)
                try:
                    # Normalizar nomes das colunas
                    normalized_data = {}
                    for key, value in row_data.items():
                        normalized_key = normalize_column_name(key)
                        normalized_data[normalized_key] = value
                    
                    # Validar que cd_ordemserv existe (campo obrigatório)
                    cd_ordemserv = normalized_data.get('cd_ordemserv') or row_data.get('CD_ORDEMSERV') or row_data.get('Código Ordem Serviço')
                    if not cd_ordemserv:
                        errors.append(f"Linha {row_num}: Código da ordem de serviço é obrigatório")
                        continue
                    
                    # Converter cd_ordemserv para int
                    try:
                        if isinstance(cd_ordemserv, str):
                            cd_ordemserv = float(cd_ordemserv.replace(',', '.'))
                        cd_ordemserv = int(float(cd_ordemserv))
                    except (ValueError, TypeError):
                        errors.append(f"Linha {row_num}: Código da ordem de serviço inválido: {cd_ordemserv}")
                        continue
                    
                    # Preparar dados para o modelo OrdemServicoCorretiva
                    ordem_data = {
                        'cd_ordemserv': cd_ordemserv,
                        'cd_unid': _safe_int(normalized_data.get('cd_unid') or row_data.get('CD_UNID')),
                        'nome_unid': _safe_str(normalized_data.get('nome_unid') or row_data.get('NOME_UNID'), max_length=255),
                        'cd_unid_exec': _safe_int(normalized_data.get('cd_unid_exec') or row_data.get('CD_UNID_EXEC')),
                        'nome_unid_exec': _safe_str(normalized_data.get('nome_unid_exec') or row_data.get('NOME_UNID_EXEC'), max_length=255),
                        'cd_setormanut': _safe_str(normalized_data.get('cd_setormanut') or row_data.get('CD_SETORMANUT'), max_length=50),
                        'descr_setormanut': _safe_str(normalized_data.get('descr_setormanut') or row_data.get('DESCR_SETORMANUT'), max_length=255),
                        'cd_tpcentativ': _safe_int(normalized_data.get('cd_tpcentativ') or row_data.get('CD_TPCENTATIV')),
                        'descr_abrev_tpcentativ': _safe_str(normalized_data.get('descr_abrev_tpcentativ') or row_data.get('DESCR_ABREV_TPCENTATIV'), max_length=255),
                        'cd_maquina': _safe_int(normalized_data.get('cd_maquina') or row_data.get('CD_MAQUINA')),
                        'descr_maquina': _safe_str(normalized_data.get('descr_maquina') or row_data.get('DESCR_MAQUINA'), max_length=500),
                        'dt_entrada': _safe_str(normalized_data.get('dt_entrada') or row_data.get('DT_ENTRADA'), max_length=50),
                        'dt_abertura_solicita': _safe_str(normalized_data.get('dt_abertura_solicita') or row_data.get('DT_ABERTURA_SOLICITA'), max_length=50),
                        'cd_func_solic_os': _safe_str(normalized_data.get('cd_func_solic_os') or row_data.get('CD_FUNC_SOLIC_OS'), max_length=100),
                        'nm_func_solic_os': _safe_str(normalized_data.get('nm_func_solic_os') or row_data.get('NM_FUNC_SOLIC_OS'), max_length=255),
                        'descr_queixa': _safe_str(normalized_data.get('descr_queixa') or row_data.get('DESCR_QUEIXA'), max_length=None),
                        'exec_tarefas': _safe_str(normalized_data.get('exec_tarefas') or row_data.get('EXEC_TAREFAS'), max_length=None),
                        'cd_func_exec': _safe_str(normalized_data.get('cd_func_exec') or row_data.get('CD_FUNC_EXEC'), max_length=100),
                        'nm_func_exec': _safe_str(normalized_data.get('nm_func_exec') or row_data.get('NM_FUNC_EXEC'), max_length=255),
                        'descr_obsordserv': _safe_str(normalized_data.get('descr_obsordserv') or row_data.get('DESCR_OBSORDSERV'), max_length=None),
                        'dt_encordmanu': _safe_str(normalized_data.get('dt_encordmanu') or row_data.get('DT_ENCORDMANU'), max_length=50),
                        'dt_aberordser': _safe_str(normalized_data.get('dt_aberordser') or row_data.get('DT_ABERORDSER'), max_length=50),
                        'dt_iniparmanu': _safe_str(normalized_data.get('dt_iniparmanu') or row_data.get('DT_INIPARMANU'), max_length=50),
                        'dt_fimparmanu': _safe_str(normalized_data.get('dt_fimparmanu') or row_data.get('DT_FIMPARMANU'), max_length=50),
                        'dt_prev_exec': _safe_str(normalized_data.get('dt_prev_exec') or row_data.get('DT_PREV_EXEC'), max_length=50),
                        'cd_tpordservtv': _safe_int(normalized_data.get('cd_tpordservtv') or row_data.get('CD_TPORDSERVTV')),
                        'descr_tpordservtv': _safe_str(normalized_data.get('descr_tpordservtv') or row_data.get('DESCR_TPORDSERVTV'), max_length=255),
                        'descr_sitordsetv': _safe_str(normalized_data.get('descr_sitordsetv') or row_data.get('DESCR_SITORDSETV'), max_length=255),
                        'descr_recomenos': _safe_str(normalized_data.get('descr_recomenos') or row_data.get('DESCR_RECOMENOS'), max_length=None),
                        'descr_seqplamanu': _safe_str(normalized_data.get('descr_seqplamanu') or row_data.get('DESCR_SEQPLAMANU'), max_length=255),
                        'cd_tpmanuttv': _safe_int(normalized_data.get('cd_tpmanuttv') or row_data.get('CD_TPMANUTTV')),
                        'descr_tpmanuttv': _safe_str(normalized_data.get('descr_tpmanuttv') or row_data.get('DESCR_TPMANUTTV'), max_length=255),
                        'cd_clasorigos': _safe_int(normalized_data.get('cd_clasorigos') or row_data.get('CD_CLASORIGOS')),
                        'descr_clasorigos': _safe_str(normalized_data.get('descr_clasorigos') or row_data.get('DESCR_CLASORIGOS'), max_length=255),
                    }
                    
                    # Remover None values para não sobrescrever campos existentes com None
                    ordem_data = {k: v for k, v in ordem_data.items() if v is not None}
                    
                    # Criar ou atualizar ordem de serviço
                    if update_existing:
                        ordem, created = OrdemServicoCorretiva.objects.update_or_create(
                            cd_ordemserv=cd_ordemserv,
                            defaults=ordem_data
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    else:
                        # Apenas criar se não existir
                        ordem, created = OrdemServicoCorretiva.objects.get_or_create(
                            cd_ordemserv=cd_ordemserv,
                            defaults=ordem_data
                        )
                        if created:
                            created_count += 1
                    
                    # Preparar dados para Ficha (campos que foram movidos para nova tabela)
                    ficha_data = {
                        'cd_func_exec_os': _safe_str(normalized_data.get('cd_func_exec_os') or row_data.get('CD_FUNC_EXEC_OS'), max_length=100),
                        'nm_func_exec_os': _safe_str(normalized_data.get('nm_func_exec_os') or row_data.get('NM_FUNC_EXEC_OS'), max_length=255),
                        'dt_ficapomanu': _safe_str(normalized_data.get('dt_ficapomanu') or row_data.get('DT_FICAPOMANU'), max_length=50),
                        'dt_inic_iteficmanu': _safe_str(normalized_data.get('dt_inic_iteficmanu') or row_data.get('DT_INIC_ITEFICMANU'), max_length=50),
                        'dt_fim_iteficmanu': _safe_str(normalized_data.get('dt_fim_iteficmanu') or row_data.get('DT_FIM_ITEFICMANU'), max_length=50),
                    }
                    
                    # Remover None values e strings vazias, normalizando para None
                    ficha_data_cleaned = {}
                    for k, v in ficha_data.items():
                        if v is not None and str(v).strip():
                            ficha_data_cleaned[k] = str(v).strip()
                        else:
                            ficha_data_cleaned[k] = None
                    
                    # Criar ficha apenas se houver pelo menos um campo preenchido
                    if any(v is not None for v in ficha_data_cleaned.values()):
                        # Verificar se já existe uma ficha duplicada
                        # Uma ficha é considerada duplicada se todos os campos forem iguais
                        from django.db.models import Q
                        
                        # Construir query para verificar duplicatas
                        # Comparar todos os campos, tratando None e strings vazias como equivalentes
                        query = Q(ordem_servico=ordem)
                        
                        # Para cada campo, adicionar condição de igualdade ou None
                        for field_name, field_value in ficha_data_cleaned.items():
                            if field_value is not None:
                                query &= Q(**{field_name: field_value})
                            else:
                                # Se o valor é None, verificar se o campo no banco também é None ou vazio
                                query &= (Q(**{f'{field_name}__isnull': True}) | Q(**{f'{field_name}': ''}))
                        
                        ficha_exists = OrdemServicoCorretivaFicha.objects.filter(query).exists()
                        
                        if not ficha_exists:
                            ficha_data_cleaned['ordem_servico'] = ordem
                            OrdemServicoCorretivaFicha.objects.create(**ficha_data_cleaned)
                        else:
                            # Adicionar aviso sobre ficha duplicada (mas não é erro crítico)
                            errors.append(f"Linha {row_num}: Ficha duplicada ignorada para OS {cd_ordemserv} (mesmos dados já existem)")
                    
                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    errors.append(f"Linha {row_num}: {str(e)}")
                    print(f"Erro na linha {row_num}: {error_detail}")  # Debug
                    continue
        
        return created_count, updated_count, errors
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        errors.append(f"Erro geral: {str(e)}")
        print(f"Erro geral: {error_detail}")  # Debug
        return 0, 0, errors


def upload_maquinas_from_file(file, update_existing=False) -> Tuple[int, int, List[str]]:
    """
    Faz upload de máquinas a partir de um arquivo CSV ou Excel
    
    Args:
        file: Arquivo Django UploadedFile
        update_existing: Se True, atualiza registros existentes. Se False, ignora duplicados.
    
    Returns:
        Tupla (created_count, updated_count, errors)
    """
    from app.models import Maquina
    
    errors = []
    created_count = 0
    updated_count = 0
    
    # Determinar tipo de arquivo
    file_name = file.name.lower()
    
    try:
        # Ler arquivo baseado na extensão
        if file_name.endswith(('.xlsx', '.xls', '.xlsm')):
            data = read_excel_file(file)
        elif file_name.endswith('.csv'):
            # Tentar diferentes encodings
            try:
                data = read_csv_file(file, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    file.seek(0)  # Resetar arquivo
                    data = read_csv_file(file, encoding='latin-1')
                except Exception as e:
                    raise ValidationError(f"Erro ao ler arquivo CSV: {str(e)}")
        else:
            raise ValidationError("Formato de arquivo não suportado. Use .xlsx, .xls, .xlsm ou .csv")
        
        if not data:
            raise ValidationError("Arquivo vazio ou sem dados válidos")
        
        # Processar dados em transação
        with transaction.atomic():
            for row_num, row_data in enumerate(data, start=2):  # Começar em 2 (linha 1 é cabeçalho)
                try:
                    # Normalizar nomes das colunas
                    normalized_data = {}
                    for key, value in row_data.items():
                        normalized_key = normalize_column_name(key)
                        normalized_data[normalized_key] = value
                    
                    # Validar que cd_maquina existe (campo obrigatório)
                    cd_maquina = normalized_data.get('cd_maquina') or row_data.get('CD_MAQUINA') or row_data.get('Código Máquina')
                    if not cd_maquina:
                        errors.append(f"Linha {row_num}: Código da máquina é obrigatório")
                        continue
                    
                    # Converter cd_maquina para int
                    try:
                        if isinstance(cd_maquina, str):
                            cd_maquina = float(cd_maquina.replace(',', '.'))
                        cd_maquina = int(float(cd_maquina))
                    except (ValueError, TypeError):
                        errors.append(f"Linha {row_num}: Código da máquina inválido: {cd_maquina}")
                        continue
                    
                    # Preparar dados para o modelo
                    maquina_data = {
                        'cd_maquina': cd_maquina,
                        'cd_unid': _safe_int(normalized_data.get('cd_unid') or row_data.get('CD_UNID')),
                        'nome_unid': _safe_str(normalized_data.get('nome_unid') or row_data.get('NOME_UNID'), max_length=255),
                        'cs_tt_maquina': _safe_int(normalized_data.get('cs_tt_maquina') or row_data.get('CS_TT_MAQUINA')),
                        'descr_maquina': _safe_str(normalized_data.get('descr_maquina') or row_data.get('DESCR_MAQUINA'), max_length=500),
                        'cd_setormanut': _safe_int(normalized_data.get('cd_setormanut') or row_data.get('CD_SETORMANUT')),
                        'descr_setormanut': _safe_str(normalized_data.get('descr_setormanut') or row_data.get('DESCR_SETORMANUT'), max_length=255),
                        'cd_priomaqutv': _safe_int(normalized_data.get('cd_priomaqutv') or row_data.get('CD_PRIOMAQUTV')),
                        'nro_patrimonio': _safe_str(normalized_data.get('nro_patrimonio') or row_data.get('NRO_PATRIMONIO'), max_length=100),
                        'cd_modelo': _safe_int(normalized_data.get('cd_modelo') or row_data.get('CD_MODELO')),
                        'cd_grupo': _safe_int(normalized_data.get('cd_grupo') or row_data.get('CD_GRUPO')),
                        'cd_tpcentativ': _safe_int(normalized_data.get('cd_tpcentativ') or row_data.get('CD_TPCENTATIV')),
                        'descr_gerenc': _safe_str(normalized_data.get('descr_gerenc') or row_data.get('DESCR_GERENC'), max_length=255),
                    }
                    
                    # Criar ou atualizar
                    if update_existing:
                        maquina, created = Maquina.objects.update_or_create(
                            cd_maquina=cd_maquina,
                            defaults=maquina_data
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    else:
                        # Apenas criar se não existir
                        maquina, created = Maquina.objects.get_or_create(
                            cd_maquina=cd_maquina,
                            defaults=maquina_data
                        )
                        if created:
                            created_count += 1
                    
                except Exception as e:
                    errors.append(f"Linha {row_num}: {str(e)}")
                    continue
        
        return created_count, updated_count, errors
    
    except Exception as e:
        errors.append(f"Erro geral: {str(e)}")
        return 0, 0, errors


def upload_itens_estoque_from_file(file, update_existing=False) -> Tuple[int, int, List[str]]:
    """
    Faz upload de itens de estoque a partir de um arquivo Excel ou CSV
    
    Args:
        file: Arquivo Django UploadedFile
        update_existing: Se True, atualiza registros existentes. Se False, ignora duplicados.
    
    Returns:
        Tupla (created_count, updated_count, errors)
    """
    from app.models import ItemEstoque
    
    errors = []
    created_count = 0
    updated_count = 0
    
    # Determinar tipo de arquivo
    file_name = file.name.lower()
    
    try:
        # Ler arquivo baseado na extensão
        if file_name.endswith(('.xlsx', '.xls', '.xlsm')):
            data = read_excel_file(file)
        elif file_name.endswith('.csv'):
            # Tentar diferentes encodings
            try:
                data = read_csv_file(file, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    file.seek(0)  # Resetar arquivo
                    data = read_csv_file(file, encoding='latin-1')
                except Exception as e:
                    raise ValidationError(f"Erro ao ler arquivo CSV: {str(e)}")
        else:
            raise ValidationError("Formato de arquivo não suportado. Use .xlsx, .xls, .xlsm ou .csv")
        
        if not data:
            raise ValidationError("Arquivo vazio ou sem dados válidos")
        
        # Processar dados em transação
        with transaction.atomic():
            for row_num, row_data in enumerate(data, start=2):  # Começar em 2 (linha 1 é cabeçalho)
                try:
                    # Normalizar nomes das colunas (case-insensitive)
                    normalized_data = {}
                    for key, value in row_data.items():
                        if value is None:
                            continue
                        # Normalizar chave para uppercase com underscore
                        normalized_key = str(key).strip().upper().replace(' ', '_')
                        normalized_data[normalized_key] = value
                    
                    # Validar que codigo_item existe (campo obrigatório)
                    codigo_item = normalized_data.get('CODIGO_ITEM') or normalized_data.get('CODIGO ITEM') or row_data.get('CODIGO ITEM') or row_data.get('Codigo Item')
                    if not codigo_item:
                        errors.append(f"Linha {row_num}: Código do item é obrigatório")
                        continue
                    
                    # Converter codigo_item para int
                    try:
                        if isinstance(codigo_item, str):
                            codigo_item = float(codigo_item.replace(',', '.'))
                        codigo_item = int(float(codigo_item))
                    except (ValueError, TypeError):
                        errors.append(f"Linha {row_num}: Código do item inválido: {codigo_item}")
                        continue
                    
                    # Preparar dados para o modelo
                    item_data = {
                        'codigo_item': codigo_item,
                        'estante': _safe_int(normalized_data.get('ESTANTE') or row_data.get('ESTANTE')),
                        'prateleira': _safe_int(normalized_data.get('PRATELEIRA') or row_data.get('PRATELEIRA')),
                        'coluna': _safe_int(normalized_data.get('COLUNA') or row_data.get('COLUNA')),
                        'sequencia': _safe_int(normalized_data.get('SEQUENCIA') or row_data.get('SEQUENCIA')),
                        'descricao_dest_uso': _safe_str(normalized_data.get('DESCRICAO_DEST_USO') or row_data.get('DESCRIÇÃO DEST. USO')),
                        'descricao_item': _safe_str(normalized_data.get('DESCRICAO_ITEM') or row_data.get('DESCRIÇÃO ITEM'), max_length=500),
                        'unidade_medida': _safe_str(normalized_data.get('UNIDADE_MEDIDA') or row_data.get('UNIDADE MEDIDA'), max_length=50),
                        'quantidade': _safe_decimal(normalized_data.get('QUANTIDADE') or row_data.get('QUANTIDADE')),
                        'valor': _safe_decimal(normalized_data.get('VALOR') or row_data.get('VALOR')),
                        'controla_estoque_minimo': _safe_str(normalized_data.get('CONTROLA_ESTOQUE_MINIMO') or row_data.get('CONTROLA ESTOQUE MINIMO'), max_length=10),
                        'classificacao_tempo_sem_consumo': _safe_str(normalized_data.get('CLASSIFICACAO_TEMPO_SEM_CONSUMO') or row_data.get('CLASSIFICAÇÃO TEMPO SEM CONSUMO'), max_length=255),
                    }
                    
                    # Criar ou atualizar
                    if update_existing:
                        item, created = ItemEstoque.objects.update_or_create(
                            codigo_item=codigo_item,
                            defaults=item_data
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    else:
                        # Apenas criar se não existir
                        item, created = ItemEstoque.objects.get_or_create(
                            codigo_item=codigo_item,
                            defaults=item_data
                        )
                        if created:
                            created_count += 1
                        
                except Exception as e:
                    errors.append(f"Linha {row_num}: {str(e)}")
                    continue
        
        return created_count, updated_count, errors
    
    except Exception as e:
        errors.append(f"Erro geral: {str(e)}")
        return 0, 0, errors


def upload_cas_from_file(file, update_existing=False) -> Tuple[int, int, List[str]]:
    """
    Faz upload de Centros de Atividade (CA) a partir de um arquivo CSV ou Excel
    
    Args:
        file: Arquivo Django UploadedFile
        update_existing: Se True, atualiza registros existentes. Se False, ignora duplicados.
    
    Returns:
        Tupla (created_count, updated_count, errors)
    """
    from app.models import CentroAtividade
    
    errors = []
    created_count = 0
    updated_count = 0
    
    # Determinar tipo de arquivo
    file_name = file.name.lower()
    
    try:
        # Ler arquivo baseado na extensão
        if file_name.endswith(('.xlsx', '.xls', '.xlsm')):
            data = read_excel_file(file)
        elif file_name.endswith('.csv'):
            # Tentar diferentes encodings
            try:
                data = read_csv_file(file, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    file.seek(0)  # Resetar arquivo
                    data = read_csv_file(file, encoding='latin-1')
                except Exception as e:
                    raise ValidationError(f"Erro ao ler arquivo CSV: {str(e)}")
        else:
            raise ValidationError("Formato de arquivo não suportado. Use .xlsx, .xls, .xlsm ou .csv")
        
        if not data:
            raise ValidationError("Arquivo vazio ou sem dados válidos")
        
        # Processar dados em transação
        with transaction.atomic():
            for row_num, row_data in enumerate(data, start=2):  # Começar em 2 (linha 1 é cabeçalho)
                try:
                    # Normalizar nomes das colunas
                    normalized_data = {}
                    for key, value in row_data.items():
                        normalized_key = normalize_column_name(key)
                        normalized_data[normalized_key] = value
                    
                    # Validar que ca existe (campo obrigatório)
                    ca = normalized_data.get('ca') or row_data.get('CA') or row_data.get('Código CA')
                    if not ca:
                        errors.append(f"Linha {row_num}: CA é obrigatório")
                        continue
                    
                    # Converter ca para int
                    try:
                        if isinstance(ca, str):
                            ca = float(ca.replace(',', '.'))
                        ca = int(float(ca))
                    except (ValueError, TypeError):
                        errors.append(f"Linha {row_num}: CA inválido: {ca}")
                        continue
                    
                    # Preparar dados para o modelo
                    # Tentar diferentes variações de nomes de colunas
                    ca_data = {
                        'ca': ca,
                        'sigla': _safe_str(
                            normalized_data.get('sigla') or 
                            row_data.get('Sigla') or row_data.get('SIGLA') or 
                            row_data.get('sigla') or row_data.get('Sigla'),
                            max_length=50
                        ),
                        'descricao': _safe_str(
                            normalized_data.get('descricao') or 
                            row_data.get('Descrição') or row_data.get('DESCRIÇÃO') or 
                            row_data.get('Descricao') or row_data.get('DESCRICAO') or
                            row_data.get('descricao'),
                            max_length=500
                        ),
                        'indice': _safe_int(
                            normalized_data.get('indice') or 
                            row_data.get('Índice') or row_data.get('INDICE') or 
                            row_data.get('Indice') or row_data.get('indice')
                        ),
                        'encarregado_responsavel': _safe_str(
                            normalized_data.get('encarregado_responsavel') or 
                            row_data.get('Encarregado Responsável') or row_data.get('ENCARREGADO RESPONSÁVEL') or
                            row_data.get('Encarregado Responsavel') or row_data.get('ENCARREGADO_RESPONSAVEL') or
                            row_data.get('encarregado_responsavel'),
                            max_length=255
                        ),
                        'local': _safe_str(
                            normalized_data.get('local') or 
                            row_data.get('Local') or row_data.get('LOCAL') or 
                            row_data.get('local'),
                            max_length=255
                        ),
                    }
                    
                    # Criar ou atualizar
                    if update_existing:
                        centro, created = CentroAtividade.objects.update_or_create(
                            ca=ca,
                            defaults=ca_data
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    else:
                        # Apenas criar se não existir
                        centro, created = CentroAtividade.objects.get_or_create(
                            ca=ca,
                            defaults=ca_data
                        )
                        if created:
                            created_count += 1
                    
                except Exception as e:
                    errors.append(f"Linha {row_num}: {str(e)}")
                    continue
        
        return created_count, updated_count, errors
    
    except Exception as e:
        errors.append(f"Erro geral: {str(e)}")
        return 0, 0, errors


def upload_manutentores_from_file(file, update_existing=False) -> Tuple[int, int, List[str]]:
    """
    Faz upload de manutentores a partir de um arquivo CSV ou Excel
    
    Args:
        file: Arquivo Django UploadedFile
        update_existing: Se True, atualiza registros existentes. Se False, ignora duplicados.
    
    Returns:
        Tupla (created_count, updated_count, errors)
    """
    from app.models import Manutentor
    from datetime import datetime
    import re
    
    errors = []
    created_count = 0
    updated_count = 0
    
    # Determinar tipo de arquivo
    file_name = file.name.lower()
    
    try:
        # Ler arquivo baseado na extensão
        if file_name.endswith(('.xlsx', '.xls', '.xlsm')):
            data = read_excel_file(file)
        elif file_name.endswith('.csv'):
            # Tentar diferentes encodings e delimitadores
            try:
                # Primeiro tentar com delimitador ponto e vírgula (;)
                file.seek(0)
                data = read_csv_file(file, encoding='utf-8', delimiter=';')
            except Exception:
                try:
                    file.seek(0)
                    data = read_csv_file(file, encoding='latin-1', delimiter=';')
                except Exception:
                    try:
                        file.seek(0)
                        data = read_csv_file(file, encoding='utf-8', delimiter=',')
                    except Exception as e:
                        file.seek(0)
                        data = read_csv_file(file, encoding='latin-1', delimiter=',')
        else:
            raise ValidationError("Formato de arquivo não suportado. Use .xlsx, .xls, .xlsm ou .csv")
        
        if not data:
            raise ValidationError("Arquivo vazio ou sem dados válidos")
        
        # Processar dados em transação
        with transaction.atomic():
            for row_num, row_data in enumerate(data, start=2):  # Começar em 2 (linha 1 é cabeçalho)
                try:
                    # Normalizar nomes das colunas (case-insensitive)
                    normalized_data = {}
                    for key, value in row_data.items():
                        if value is None:
                            continue
                        # Normalizar chave
                        normalized_key = str(key).strip().lower().replace(' ', '_')
                        normalized_data[normalized_key] = value
                    
                    # Validar que Cadastro existe (campo obrigatório)
                    cadastro = normalized_data.get('cadastro') or row_data.get('Cadastro') or row_data.get('CADASTRO')
                    if not cadastro:
                        errors.append(f"Linha {row_num}: Cadastro é obrigatório")
                        continue
                    
                    # Converter cadastro para string
                    cadastro = str(cadastro).strip()
                    
                    # Converter Admissao para DateField
                    admissao = None
                    admissao_str = normalized_data.get('admissao') or row_data.get('Admissao') or row_data.get('ADMISSAO')
                    if admissao_str:
                        try:
                            # Tentar diferentes formatos de data
                            if isinstance(admissao_str, str):
                                # Formato DD/MM/YYYY
                                if '/' in admissao_str:
                                    admissao = datetime.strptime(admissao_str.strip(), '%d/%m/%Y').date()
                                # Formato YYYY-MM-DD
                                elif '-' in admissao_str:
                                    admissao = datetime.strptime(admissao_str.strip(), '%Y-%m-%d').date()
                        except (ValueError, TypeError):
                            errors.append(f"Linha {row_num}: Data de admissão inválida: {admissao_str}")
                    
                    # Obter valores dos campos
                    nome = _safe_str(normalized_data.get('nome') or row_data.get('Nome') or row_data.get('NOME'), max_length=1000)
                    cargo = _safe_str(normalized_data.get('cargo') or row_data.get('Cargo') or row_data.get('CARGO'), max_length=1000)
                    posto = _safe_str(normalized_data.get('posto') or row_data.get('Posto') or row_data.get('POSTO'), max_length=1000)
                    
                    # Obter local_trab e validar
                    local_trab_raw = normalized_data.get('local_trab') or row_data.get('local_trab') or row_data.get('LOCAL_TRAB')
                    local_trab = None
                    if local_trab_raw:
                        local_trab_str = str(local_trab_raw).strip()
                        # Mapear valores possíveis
                        local_trab_map = {
                            'industria': 'Industria',
                            'frigorífico': 'Frigorífico',
                            'frigorifico': 'Frigorífico',
                            'civil': 'Civil',
                            'indefinido': 'Indefinido',
                            'ete/eta': 'ETE/ETA',
                            'utilidades': 'Utilidades',
                            'manutenção': 'Manutenção',
                            'manutencao': 'Manutenção',
                        }
                        local_trab_lower = local_trab_str.lower()
                        if local_trab_lower in local_trab_map:
                            local_trab = local_trab_map[local_trab_lower]
                        elif local_trab_str in ['Industria', 'Frigorífico', 'Civil', 'Indefinido', 'ETE/ETA', 'Utilidades', 'Manutenção']:
                            local_trab = local_trab_str
                        else:
                            errors.append(f"Linha {row_num}: Local de trabalho inválido: {local_trab_str}. Usando padrão 'Indefinido'")
                            local_trab = 'Indefinido'
                    
                    if not local_trab:
                        local_trab = 'Indefinido'  # Valor padrão
                    
                    # Obter turno e validar
                    turno_raw = normalized_data.get('turno') or row_data.get('turno') or row_data.get('TURNO')
                    turno = None
                    if turno_raw:
                        turno_str = str(turno_raw).strip()
                        # Mapear valores possíveis
                        turno_map = {
                            'turno a': 'Turno A',
                            'turno b': 'Turno B',
                            'turno c': 'Turno C',
                        }
                        turno_lower = turno_str.lower()
                        if turno_lower in turno_map:
                            turno = turno_map[turno_lower]
                        elif turno_str in ['Turno A', 'Turno B', 'Turno C']:
                            turno = turno_str
                        else:
                            errors.append(f"Linha {row_num}: Turno inválido: {turno_str}. Usando padrão 'Turno A'")
                            turno = 'Turno A'
                    
                    if not turno:
                        turno = 'Turno A'  # Valor padrão
                    
                    # Inferir tipo do Cargo
                    tipo = 'Eletromecânico'  # Valor padrão
                    if cargo:
                        cargo_lower = cargo.lower()
                        if 'eletric' in cargo_lower or 'automa' in cargo_lower:
                            tipo = 'Eletricista'
                        elif 'mecan' in cargo_lower:
                            tipo = 'Mecânico'
                        elif 'operador' in cargo_lower and ('ete' in cargo_lower or 'eta' in cargo_lower):
                            tipo = 'Operador ETE/ETA'
                    
                    # Preparar dados para o modelo
                    manutentor_data = {
                        'Nome': nome,
                        'Admissao': admissao,
                        'Cargo': cargo,
                        'Posto': posto,
                        'tempo_trabalho': '8 horas',  # Valor padrão
                        'tipo': tipo,
                        'turno': turno,
                        'local_trab': local_trab,
                    }
                    
                    # Criar ou atualizar
                    if update_existing:
                        manutentor, created = Manutentor.objects.update_or_create(
                            Cadastro=cadastro,
                            defaults=manutentor_data
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    else:
                        # Apenas criar se não existir
                        manutentor, created = Manutentor.objects.get_or_create(
                            Cadastro=cadastro,
                            defaults=manutentor_data
                        )
                        if created:
                            created_count += 1
                    
                except Exception as e:
                    errors.append(f"Linha {row_num}: {str(e)}")
                    continue
        
        return created_count, updated_count, errors
    
    except Exception as e:
        errors.append(f"Erro geral: {str(e)}")
        return 0, 0, errors


def _safe_int(value):
    """
    Converte um valor para int de forma segura
    
    Args:
        value: Valor a ser convertido
    
    Returns:
        int ou None
    """
    if value is None or value == '':
        return None
    try:
        if isinstance(value, str):
            # Remover vírgulas e espaços
            value = value.replace(',', '').replace(' ', '')
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _safe_str(value, max_length=None):
    """
    Converte um valor para string de forma segura
    
    Args:
        value: Valor a ser convertido
        max_length: Tamanho máximo da string (opcional)
    
    Returns:
        str ou None
    """
    if value is None or value == '':
        return None
    try:
        result = str(value).strip()
        if max_length and len(result) > max_length:
            result = result[:max_length]
        return result if result else None
    except (ValueError, TypeError):
        return None


def _safe_decimal(value):
    """
    Converte um valor para Decimal de forma segura
    
    Args:
        value: Valor a ser convertido
    
    Returns:
        Decimal ou 0
    """
    from decimal import Decimal
    if value is None or value == '':
        return Decimal('0')
    try:
        if isinstance(value, str):
            # Substituir vírgula por ponto
            value = value.replace(',', '.')
        return Decimal(str(value))
    except (ValueError, TypeError):
        return Decimal('0')


def _safe_date(value):
    """
    Converte um valor para date de forma segura
    
    Args:
        value: Valor a ser convertido (pode ser string ou date)
    
    Returns:
        date ou None
    """
    from datetime import datetime
    if value is None or value == '':
        return None
    try:
        if isinstance(value, str):
            # Tentar diferentes formatos
            if '/' in value:
                return datetime.strptime(value.strip(), '%d/%m/%Y').date()
            elif '-' in value:
                return datetime.strptime(value.strip(), '%Y-%m-%d').date()
        elif hasattr(value, 'date'):
            return value.date()
        return value
    except (ValueError, TypeError):
        return None


def _fix_funcionario_columns(row_data):
    """
    Corrige deslocamento das colunas Funcionário e Nome Funcionário
    
    Lógica:
    1. Se a coluna "Funcionário" está vazia, assumir que os dados corretos estão nas próximas colunas
    2. Se "Nome Funcionário" contém apenas números, assumir que o nome correto está na próxima coluna
    
    Args:
        row_data: Dicionário com os dados da linha do CSV
    
    Returns:
        Dicionário corrigido
    """
    import re
    
    # Função auxiliar para encontrar chave por padrão
    def find_key_by_pattern(patterns):
        """Encontra uma chave no dicionário que corresponde a um dos padrões"""
        for key in row_data.keys():
            key_lower = str(key).lower().strip()
            for pattern in patterns:
                if pattern in key_lower:
                    return key
        return None
    
    # Função auxiliar para verificar se é apenas número
    def is_only_number(value):
        """Verifica se o valor contém apenas números (com ou sem espaços)"""
        if not value:
            return False
        value_str = str(value).strip()
        return bool(re.match(r'^\s*\d+\s*$', value_str))
    
    # Encontrar as chaves corretas
    funcionario_key = find_key_by_pattern(['funcionário', 'funcionario'])
    nome_funcionario_key = find_key_by_pattern(['nome funcionário', 'nome funcionario'])
    
    if not funcionario_key or not nome_funcionario_key:
        return row_data  # Não encontrou as colunas, retornar sem alteração
    
    # Obter valores originais (convertendo None para string vazia)
    funcionario_value = str(row_data.get(funcionario_key, '') or '').strip()
    nome_funcionario_value = str(row_data.get(nome_funcionario_key, '') or '').strip()
    
    # Obter todas as chaves em ordem (para manter a ordem do CSV)
    all_keys = list(row_data.keys())
    
    # Encontrar índices das colunas
    funcionario_idx = None
    nome_funcionario_idx = None
    for idx, key in enumerate(all_keys):
        if key == funcionario_key:
            funcionario_idx = idx
        if key == nome_funcionario_key:
            nome_funcionario_idx = idx
    
    if funcionario_idx is None or nome_funcionario_idx is None:
        return row_data
    
    # LÓGICA 1: Se Funcionário está vazio, assumir que os dados estão nas próximas colunas
    if not funcionario_value:
        # Procurar nas colunas após "Funcionário"
        # A primeira coluna não vazia após "Funcionário" = número do funcionário
        # A segunda coluna não vazia após "Funcionário" = nome do funcionário
        
        numero_encontrado = None
        nome_encontrado = None
        numero_key = None
        nome_key = None
        
        # Começar a procurar a partir da coluna após "Funcionário"
        for idx in range(funcionario_idx + 1, len(all_keys)):
            next_key = all_keys[idx]
            next_value = str(row_data.get(next_key, '') or '').strip()
            
            if next_value:
                if numero_encontrado is None:
                    # Primeiro valor não vazio encontrado = número do funcionário
                    numero_encontrado = next_value
                    numero_key = next_key
                elif nome_encontrado is None:
                    # Segundo valor não vazio encontrado = nome do funcionário
                    nome_encontrado = next_value
                    nome_key = next_key
                    break
        
        # Se encontramos os dados, corrigir
        if numero_encontrado:
            row_data[funcionario_key] = numero_encontrado
            # Limpar a coluna original que tinha o número (se não for "Nome Funcionário")
            if numero_key and numero_key != nome_funcionario_key:
                row_data[numero_key] = ''
            
            if nome_encontrado:
                row_data[nome_funcionario_key] = nome_encontrado
                # Limpar a coluna original que tinha o nome (se não for "Nome Funcionário")
                if nome_key and nome_key != nome_funcionario_key:
                    row_data[nome_key] = ''
            else:
                # Se não encontramos o nome, limpar "Nome Funcionário" se ela tinha o número
                if numero_key == nome_funcionario_key:
                    row_data[nome_funcionario_key] = ''
    
    # LÓGICA 2: Se "Nome Funcionário" contém apenas números, assumir que o nome correto está na próxima coluna
    if nome_funcionario_value and is_only_number(nome_funcionario_value):
        # O número está na coluna errada, procurar o nome na próxima coluna
        nome_encontrado = None
        nome_key = None
        
        # Procurar nas colunas após "Nome Funcionário"
        for idx in range(nome_funcionario_idx + 1, len(all_keys)):
            next_key = all_keys[idx]
            next_value = str(row_data.get(next_key, '') or '').strip()
            
            if next_value:
                # Primeiro valor não vazio encontrado = nome do funcionário
                nome_encontrado = next_value
                nome_key = next_key
                break
        
        # Se encontramos o nome, corrigir
        if nome_encontrado:
            # Mover o número de "Nome Funcionário" para "Funcionário" (se "Funcionário" estiver vazio)
            if not funcionario_value:
                row_data[funcionario_key] = nome_funcionario_value
            # Mover o nome para "Nome Funcionário"
            row_data[nome_funcionario_key] = nome_encontrado
            # Limpar a coluna original que tinha o nome
            if nome_key:
                row_data[nome_key] = ''
    
    return row_data


def upload_plano_preventiva_from_file(file, update_existing=False) -> Tuple[int, int, List[str]]:
    """
    Faz upload de planos de manutenção preventiva a partir de um arquivo CSV ou Excel
    
    Args:
        file: Arquivo Django UploadedFile
        update_existing: Se True, atualiza registros existentes. Se False, ignora duplicados.
    
    Returns:
        Tupla (created_count, updated_count, errors)
    """
    from app.models import PlanoPreventiva, Maquina
    
    errors = []
    created_count = 0
    updated_count = 0
    
    # Determinar tipo de arquivo
    file_name = file.name.lower()
    
    try:
        # Ler arquivo baseado na extensão
        if file_name.endswith(('.xlsx', '.xls', '.xlsm')):
            data = read_excel_file(file)
        elif file_name.endswith('.csv'):
            # Tentar diferentes encodings e delimitadores (o arquivo usa ponto e vírgula)
            try:
                # Primeiro tentar com delimitador ponto e vírgula (;) e encoding latin-1
                file.seek(0)
                data = read_csv_file(file, encoding='latin-1', delimiter=';')
            except Exception:
                try:
                    file.seek(0)
                    data = read_csv_file(file, encoding='utf-8', delimiter=';')
                except Exception:
                    try:
                        file.seek(0)
                        data = read_csv_file(file, encoding='latin-1', delimiter=',')
                    except Exception as e:
                        file.seek(0)
                        data = read_csv_file(file, encoding='utf-8', delimiter=',')
        else:
            raise ValidationError("Formato de arquivo não suportado. Use .xlsx, .xls, .xlsm ou .csv")
        
        if not data:
            raise ValidationError("Arquivo vazio ou sem dados válidos")
        
        # Cache de máquinas para melhorar performance
        maquinas_cache = {}
        
        # Processar dados em transação
        with transaction.atomic():
            for row_num, row_data in enumerate(data, start=2):  # Começar em 2 (linha 1 é cabeçalho)
                try:
                    # Verificar se a linha está vazia ou tem apenas valores vazios
                    if not any(str(v).strip() if v else '' for v in row_data.values()):
                        continue
                    
                    # CORRIGIR DESLOCAMENTO DAS COLUNAS FUNCIONÁRIO E NOME FUNCIONÁRIO
                    row_data = _fix_funcionario_columns(row_data)
                    
                    # Mapear colunas do CSV para campos do modelo
                    # O CSV tem: Unidade;Nome Unidade;Setor;Descrição Setor;Atividade;Máquina;Descrição Máquina;Nº Patrimônio;Plano;Descrição Plano;Sequência Manutenção;Data Execução;Quantidade Período;Sequência Tarefa;Descrição Tarefa;Funcionário;Nome Funcionário
                    
                    cd_unid = _safe_int(row_data.get('Unidade') or row_data.get('unidade') or row_data.get('UNIDADE'))
                    nome_unid = _safe_str(row_data.get('Nome Unidade') or row_data.get('nome unidade') or row_data.get('NOME UNIDADE'), max_length=255)
                    cd_setor = _safe_str(row_data.get('Setor') or row_data.get('setor') or row_data.get('SETOR'), max_length=50)
                    descr_setor = _safe_str(row_data.get('Descrição Setor') or row_data.get('descrição setor') or row_data.get('DESCRIÇÃO SETOR'), max_length=255)
                    cd_atividade = _safe_int(row_data.get('Atividade') or row_data.get('atividade') or row_data.get('ATIVIDADE'))
                    cd_maquina = _safe_int(row_data.get('Máquina') or row_data.get('máquina') or row_data.get('MÁQUINA'))
                    descr_maquina = _safe_str(row_data.get('Descrição Máquina') or row_data.get('descrição máquina') or row_data.get('DESCRIÇÃO MÁQUINA'), max_length=500)
                    nro_patrimonio = _safe_str(row_data.get('Nº Patrimônio') or row_data.get('nº patrimônio') or row_data.get('Nº PATRIMÔNIO'), max_length=100)
                    numero_plano = _safe_int(row_data.get('Plano') or row_data.get('plano') or row_data.get('PLANO'))
                    descr_plano = _safe_str(row_data.get('Descrição Plano') or row_data.get('descrição plano') or row_data.get('DESCRIÇÃO PLANO'), max_length=255)
                    sequencia_manutencao = _safe_int(row_data.get('Sequência Manutenção') or row_data.get('sequência manutenção') or row_data.get('SEQUÊNCIA MANUTENÇÃO'))
                    dt_execucao = _safe_str(row_data.get('Data Execução') or row_data.get('data execução') or row_data.get('DATA EXECUÇÃO'), max_length=50)
                    quantidade_periodo = _safe_int(row_data.get('Quantidade Período') or row_data.get('quantidade período') or row_data.get('QUANTIDADE PERÍODO'))
                    sequencia_tarefa = _safe_int(row_data.get('Sequência Tarefa') or row_data.get('sequência tarefa') or row_data.get('SEQUÊNCIA TAREFA'))
                    descr_tarefa = _safe_str(row_data.get('Descrição Tarefa') or row_data.get('descrição tarefa') or row_data.get('DESCRIÇÃO TAREFA'))
                    
                    # Obter Funcionário e Nome Funcionário (já corrigidos pela função _fix_funcionario_columns)
                    cd_funcionario = _safe_str(row_data.get('Funcionário') or row_data.get('funcionário') or row_data.get('FUNCIONÁRIO'), max_length=100)
                    nome_funcionario = _safe_str(row_data.get('Nome Funcionário') or row_data.get('nome funcionário') or row_data.get('NOME FUNCIONÁRIO'), max_length=255)
                    
                    # Validar que temos pelo menos código da máquina ou descrição
                    if not cd_maquina and not descr_maquina:
                        errors.append(f"Linha {row_num}: Código da máquina ou descrição é obrigatório")
                        continue
                    
                    # Tentar encontrar máquina relacionada
                    maquina = None
                    if cd_maquina:
                        # Verificar cache primeiro
                        if cd_maquina in maquinas_cache:
                            maquina = maquinas_cache[cd_maquina]
                        else:
                            try:
                                maquina = Maquina.objects.get(cd_maquina=cd_maquina)
                                maquinas_cache[cd_maquina] = maquina
                            except Maquina.DoesNotExist:
                                maquina = None
                    
                    # Preparar dados para o modelo
                    plano_data = {
                        'cd_unid': cd_unid,
                        'nome_unid': nome_unid,
                        'cd_setor': cd_setor,
                        'descr_setor': descr_setor,
                        'cd_atividade': cd_atividade,
                        'cd_maquina': cd_maquina,
                        'descr_maquina': descr_maquina,
                        'nro_patrimonio': nro_patrimonio,
                        'numero_plano': numero_plano,
                        'descr_plano': descr_plano,
                        'sequencia_manutencao': sequencia_manutencao,
                        'dt_execucao': dt_execucao,
                        'quantidade_periodo': quantidade_periodo,
                        'sequencia_tarefa': sequencia_tarefa,
                        'descr_tarefa': descr_tarefa,
                        'cd_funcionario': cd_funcionario,
                        'nome_funcionario': nome_funcionario,
                        'maquina': maquina,
                    }
                    
                    # Criar ou atualizar
                    # Usar uma combinação única: cd_maquina + numero_plano + sequencia_manutencao + sequencia_tarefa
                    if update_existing:
                        plano, created = PlanoPreventiva.objects.update_or_create(
                            cd_maquina=cd_maquina,
                            numero_plano=numero_plano,
                            sequencia_manutencao=sequencia_manutencao,
                            sequencia_tarefa=sequencia_tarefa,
                            defaults=plano_data
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    else:
                        # Apenas criar se não existir
                        plano, created = PlanoPreventiva.objects.get_or_create(
                            cd_maquina=cd_maquina,
                            numero_plano=numero_plano,
                            sequencia_manutencao=sequencia_manutencao,
                            sequencia_tarefa=sequencia_tarefa,
                            defaults=plano_data
                        )
                        if created:
                            created_count += 1
                    
                except Exception as e:
                    errors.append(f"Linha {row_num}: {str(e)}")
                    continue
        
        return created_count, updated_count, errors
    
    except Exception as e:
        errors.append(f"Erro geral: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0, 0, errors


def upload_roteiro_preventiva_from_file(file, update_existing=False) -> Tuple[int, int, List[str]]:
    """
    Faz upload de roteiro de manutenção preventiva a partir de um arquivo CSV
    O arquivo deve ter colunas no formato: CD_UNID;NOME_UNID;CD_FUNCIOMANU;...
    
    Args:
        file: Arquivo Django UploadedFile
        update_existing: Se True, atualiza registros existentes. Se False, ignora duplicados.
    
    Returns:
        Tupla (created_count, updated_count, errors)
    """
    from app.models import RoteiroPreventiva, Maquina
    
    errors = []
    created_count = 0
    updated_count = 0
    
    # Determinar tipo de arquivo
    file_name = file.name.lower()
    
    try:
        # Ler arquivo baseado na extensão
        if file_name.endswith(('.xlsx', '.xls', '.xlsm')):
            data = read_excel_file(file)
        elif file_name.endswith('.csv'):
            # Tentar diferentes encodings e delimitadores (o arquivo usa ponto e vírgula)
            try:
                # Primeiro tentar com delimitador ponto e vírgula (;) e encoding latin-1
                file.seek(0)
                data = read_csv_file(file, encoding='latin-1', delimiter=';')
            except Exception:
                try:
                    file.seek(0)
                    data = read_csv_file(file, encoding='utf-8', delimiter=';')
                except Exception:
                    try:
                        file.seek(0)
                        data = read_csv_file(file, encoding='latin-1', delimiter=',')
                    except Exception as e:
                        file.seek(0)
                        data = read_csv_file(file, encoding='utf-8', delimiter=',')
        else:
            raise ValidationError("Formato de arquivo não suportado. Use .xlsx, .xls, .xlsm ou .csv")
        
        if not data:
            raise ValidationError("Arquivo vazio ou sem dados válidos")
        
        # Cache de máquinas para melhorar performance
        maquinas_cache = {}
        
        # Processar dados em transação
        with transaction.atomic():
            for row_num, row_data in enumerate(data, start=2):  # Começar em 2 (linha 1 é cabeçalho)
                try:
                    # Verificar se a linha está vazia ou tem apenas valores vazios
                    if not any(str(v).strip() if v else '' for v in row_data.values()):
                        continue
                    
                    # Mapear colunas do CSV para campos do modelo
                    # O CSV tem: CD_UNID;NOME_UNID;CD_FUNCIOMANU;NOME_FUNCIOMANU;FUNCIOMANU_ID;CD_SETORMANUT;DESCR_SETORMANUT;...
                    
                    # Unidade
                    cd_unid = _safe_int(row_data.get('CD_UNID') or row_data.get('cd_unid') or row_data.get('Cd_Unid'))
                    nome_unid = _safe_str(row_data.get('NOME_UNID') or row_data.get('nome_unid') or row_data.get('Nome_Unid'), max_length=255)
                    
                    # Funcionário
                    cd_funciomanu = _safe_str(row_data.get('CD_FUNCIOMANU') or row_data.get('cd_funciomanu') or row_data.get('Cd_Funciomanu'), max_length=100)
                    nome_funciomanu = _safe_str(row_data.get('NOME_FUNCIOMANU') or row_data.get('nome_funciomanu') or row_data.get('Nome_Funciomanu'), max_length=255)
                    funciomanu_id = _safe_int(row_data.get('FUNCIOMANU_ID') or row_data.get('funciomanu_id') or row_data.get('Funciomanu_Id'))
                    
                    # Setor
                    cd_setormanut = _safe_str(row_data.get('CD_SETORMANUT') or row_data.get('cd_setormanut') or row_data.get('Cd_Setormanut'), max_length=50)
                    descr_setormanut = _safe_str(row_data.get('DESCR_SETORMANUT') or row_data.get('descr_setormanut') or row_data.get('Descr_Setormanut'), max_length=255)
                    
                    # Tipo Centro de Atividade
                    cd_tpcentativ = _safe_int(row_data.get('CD_TPCENTATIV') or row_data.get('cd_tpcentativ') or row_data.get('Cd_Tpcentativ'))
                    descr_abrev_tpcentativ = _safe_str(row_data.get('DESCR_ABREV_TPCENTATIV') or row_data.get('descr_abrev_tpcentativ') or row_data.get('Descr_Abrev_Tpcentativ'), max_length=255)
                    
                    # Ordem de Serviço
                    dt_abertura = _safe_str(row_data.get('DT_ABERTURA') or row_data.get('dt_abertura') or row_data.get('Dt_Abertura'), max_length=50)
                    cd_ordemserv = _safe_int(row_data.get('CD_ORDEMSERV') or row_data.get('cd_ordemserv') or row_data.get('Cd_Ordemserv'))
                    ordemserv_id = _safe_int(row_data.get('ORDEMSERV_ID') or row_data.get('ordemserv_id') or row_data.get('Ordemserv_Id'))
                    
                    # Máquina
                    cd_maquina = _safe_int(row_data.get('CD_MAQUINA') or row_data.get('cd_maquina') or row_data.get('Cd_Maquina'))
                    descr_maquina = _safe_str(row_data.get('DESCR_MAQUINA') or row_data.get('descr_maquina') or row_data.get('Descr_Maquina'), max_length=500)
                    
                    # Plano de Manutenção
                    cd_planmanut = _safe_int(row_data.get('CD_PLANMANUT') or row_data.get('cd_planmanut') or row_data.get('Cd_Planmanut'))
                    descr_planmanut = _safe_str(row_data.get('DESCR_PLANMANUT') or row_data.get('descr_planmanut') or row_data.get('Descr_Planmanut'), max_length=255)
                    descr_recomenos = _safe_str(row_data.get('DESCR_RECOMENOS') or row_data.get('descr_recomenos') or row_data.get('Descr_Recomenos'))
                    cf_dt_final_execucao = _safe_str(row_data.get('CF_DT_FINAL_EXECUCAO') or row_data.get('cf_dt_final_execucao') or row_data.get('Cf_Dt_Final_Execucao'), max_length=50)
                    cs_qtde_periodo_max = _safe_int(row_data.get('CS_QTDE_PERIODO_MAX') or row_data.get('cs_qtde_periodo_max') or row_data.get('Cs_Qtde_Periodo_Max'))
                    cs_tot_temp = _safe_str(row_data.get('CS_TOT_TEMP') or row_data.get('cs_tot_temp') or row_data.get('Cs_Tot_Temp'), max_length=50)
                    cf_tot_temp = _safe_str(row_data.get('CF_TOT_TEMP') or row_data.get('cf_tot_temp') or row_data.get('Cf_Tot_Temp'), max_length=50)
                    
                    # Sequência Plano Manutenção
                    seq_seqplamanu = _safe_int(row_data.get('SEQ_SEQPLAMANU') or row_data.get('seq_seqplamanu') or row_data.get('Seq_Seqplamanu'))
                    
                    # Tarefa Manutenção
                    cd_tarefamanu = _safe_int(row_data.get('CD_TAREFAMANU') or row_data.get('cd_tarefamanu') or row_data.get('Cd_Tarefamanu'))
                    descr_tarefamanu = _safe_str(row_data.get('DESCR_TAREFAMANU') or row_data.get('descr_tarefamanu') or row_data.get('Descr_Tarefamanu'))
                    descr_periodo = _safe_str(row_data.get('DESCR_PERIODO') or row_data.get('descr_periodo') or row_data.get('Descr_Periodo'), max_length=255)
                    
                    # Execução
                    dt_primexec = _safe_str(row_data.get('DT_PRIMEXEC') or row_data.get('dt_primexec') or row_data.get('Dt_Primexec'), max_length=50)
                    tempo_prev = _safe_str(row_data.get('TEMPO_PREV') or row_data.get('tempo_prev') or row_data.get('Tempo_Prev'), max_length=50)
                    qtde_periodo = _safe_int(row_data.get('QTDE_PERIODO') or row_data.get('qtde_periodo') or row_data.get('Qtde_Periodo'))
                    descr_seqplamanu = _safe_str(row_data.get('DESCR_SEQPLAMANU') or row_data.get('descr_seqplamanu') or row_data.get('Descr_Seqplamanu'), max_length=255)
                    cf_temp_prev = _safe_str(row_data.get('CF_TEMP_PREV') or row_data.get('cf_temp_prev') or row_data.get('Cf_Temp_Prev'), max_length=50)
                    
                    # Item do Plano
                    itemplanma_id = _safe_int(row_data.get('ITEMPLANMA_ID') or row_data.get('itemplanma_id') or row_data.get('Itemplanma_Id'))
                    cd_item = _safe_int(row_data.get('CD_ITEM') or row_data.get('cd_item') or row_data.get('Cd_Item'))
                    descr_item = _safe_str(row_data.get('DESCR_ITEM') or row_data.get('descr_item') or row_data.get('Descr_Item'), max_length=500)
                    item_id = _safe_int(row_data.get('ITEM_ID') or row_data.get('item_id') or row_data.get('Item_Id'))
                    qtde = _safe_int(row_data.get('QTDE') or row_data.get('qtde') or row_data.get('Qtde'))
                    qtde_saldo = _safe_int(row_data.get('QTDE_SALDO') or row_data.get('qtde_saldo') or row_data.get('Qtde_Saldo'))
                    qtde_reserva = _safe_int(row_data.get('QTDE_RESERVA') or row_data.get('qtde_reserva') or row_data.get('Qtde_Reserva'))
                    
                    # Validar que temos pelo menos código da máquina ou descrição
                    if not cd_maquina and not descr_maquina:
                        errors.append(f"Linha {row_num}: Código da máquina ou descrição é obrigatório")
                        continue
                    
                    # Tentar encontrar máquina relacionada
                    maquina = None
                    if cd_maquina:
                        # Verificar cache primeiro
                        if cd_maquina in maquinas_cache:
                            maquina = maquinas_cache[cd_maquina]
                        else:
                            try:
                                maquina = Maquina.objects.get(cd_maquina=cd_maquina)
                                maquinas_cache[cd_maquina] = maquina
                            except Maquina.DoesNotExist:
                                maquina = None
                    
                    # Preparar dados para o modelo
                    roteiro_data = {
                        'cd_unid': cd_unid,
                        'nome_unid': nome_unid,
                        'cd_funciomanu': cd_funciomanu,
                        'nome_funciomanu': nome_funciomanu,
                        'funciomanu_id': funciomanu_id,
                        'cd_setormanut': cd_setormanut,
                        'descr_setormanut': descr_setormanut,
                        'cd_tpcentativ': cd_tpcentativ,
                        'descr_abrev_tpcentativ': descr_abrev_tpcentativ,
                        'dt_abertura': dt_abertura,
                        'cd_ordemserv': cd_ordemserv,
                        'ordemserv_id': ordemserv_id,
                        'cd_maquina': cd_maquina,
                        'descr_maquina': descr_maquina,
                        'cd_planmanut': cd_planmanut,
                        'descr_planmanut': descr_planmanut,
                        'descr_recomenos': descr_recomenos,
                        'cf_dt_final_execucao': cf_dt_final_execucao,
                        'cs_qtde_periodo_max': cs_qtde_periodo_max,
                        'cs_tot_temp': cs_tot_temp,
                        'cf_tot_temp': cf_tot_temp,
                        'seq_seqplamanu': seq_seqplamanu,
                        'cd_tarefamanu': cd_tarefamanu,
                        'descr_tarefamanu': descr_tarefamanu,
                        'descr_periodo': descr_periodo,
                        'dt_primexec': dt_primexec,
                        'tempo_prev': tempo_prev,
                        'qtde_periodo': qtde_periodo,
                        'descr_seqplamanu': descr_seqplamanu,
                        'cf_temp_prev': cf_temp_prev,
                        'itemplanma_id': itemplanma_id,
                        'cd_item': cd_item,
                        'descr_item': descr_item,
                        'item_id': item_id,
                        'qtde': qtde,
                        'qtde_saldo': qtde_saldo,
                        'qtde_reserva': qtde_reserva,
                        'maquina': maquina,
                    }
                    
                    # Criar ou atualizar
                    # Usar uma combinação única: cd_maquina + cd_planmanut + seq_seqplamanu + cd_tarefamanu
                    if update_existing:
                        roteiro, created = RoteiroPreventiva.objects.update_or_create(
                            cd_maquina=cd_maquina,
                            cd_planmanut=cd_planmanut,
                            seq_seqplamanu=seq_seqplamanu,
                            cd_tarefamanu=cd_tarefamanu,
                            defaults=roteiro_data
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    else:
                        # Apenas criar se não existir
                        roteiro, created = RoteiroPreventiva.objects.get_or_create(
                            cd_maquina=cd_maquina,
                            cd_planmanut=cd_planmanut,
                            seq_seqplamanu=seq_seqplamanu,
                            cd_tarefamanu=cd_tarefamanu,
                            defaults=roteiro_data
                        )
                        if created:
                            created_count += 1
                    
                except Exception as e:
                    errors.append(f"Linha {row_num}: {str(e)}")
                    continue
        
        return created_count, updated_count, errors
    
    except Exception as e:
        errors.append(f"Erro geral: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0, 0, errors
