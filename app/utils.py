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
            header_value = cell.value if cell.value else f'col_{len(headers)}'
            # Normalizar encoding e espaços
            if isinstance(header_value, str):
                # Tentar corrigir problemas de encoding comuns
                header_value = header_value.strip().replace('\xa0', ' ').replace('\u00a0', ' ')
                # Normalizar espaços múltiplos
                import re
                header_value = re.sub(r'\s+', ' ', header_value).strip()
            headers.append(header_value)
        
        # Ler dados
        data = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if any(cell is not None for cell in row):  # Ignorar linhas vazias
                row_dict = {}
                for idx, cell_value in enumerate(row):
                    header = headers[idx] if idx < len(headers) else f'col_{idx}'
                    # Limpar valores de células também
                    if isinstance(cell_value, str):
                        cell_value = cell_value.strip().replace('\xa0', ' ').replace('\u00a0', ' ')
                        import re
                        cell_value = re.sub(r'\s+', ' ', cell_value).strip()
                    row_dict[header] = cell_value
                data.append(row_dict)
        
        return data
    
    except Exception as e:
        raise ValidationError(f"Erro ao ler arquivo Excel: {str(e)}")


def read_csv_file(file, encoding='utf-8', delimiter=','):
    """
    Lê um arquivo CSV e retorna os dados
    
    Args:
        file: Arquivo CSV (Django UploadedFile ou path)
        encoding: Encoding do arquivo (padrão: utf-8)
        delimiter: Delimitador do CSV (padrão: vírgula)
    
    Returns:
        Lista de dicionários com os dados
    """
    try:
        # Se for um arquivo Django UploadedFile, garantir que está no início
        if hasattr(file, 'read'):
            file.seek(0)
            content = file.read().decode(encoding)
        else:
            with open(file, 'r', encoding=encoding) as f:
                content = f.read()
        
        # Ler CSV
        csv_reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        data = []
        for row in csv_reader:
            # Remover valores vazios e normalizar
            row_dict = {}
            for key, value in row.items():
                if value:
                    row_dict[key.strip()] = value.strip()
            if row_dict:  # Adicionar apenas se não estiver vazio
                data.append(row_dict)
        
        return data
    
    except Exception as e:
        raise ValidationError(f"Erro ao ler arquivo CSV: {str(e)}")


def upload_ordens_corretivas_from_file(file, update_existing=False) -> Tuple[int, int, List[str]]:
    """
    Faz upload de ordens de serviço corretivas a partir de um arquivo CSV ou Excel
    
    Args:
        file: Arquivo Django UploadedFile
        update_existing: Se True, atualiza registros existentes. Se False, ignora duplicados.
    
    Returns:
        Tupla (created_count, updated_count, errors)
    """
    from app.models import OrdemServicoCorretiva
    
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
            # Tentar diferentes encodings - começar com latin-1 (mais comum para arquivos brasileiros)
            # O arquivo usa delimitador ponto e vírgula (;) conforme instruções na página
            data = None
            encodings_to_try = ['latin-1', 'iso-8859-1', 'utf-8', 'cp1252']
            
            for encoding in encodings_to_try:
                try:
                    file.seek(0)  # Resetar arquivo para o início
                    data = read_csv_file(file, encoding=encoding, delimiter=';')
                    break  # Se conseguir ler, sair do loop
                except (UnicodeDecodeError, ValidationError) as e:
                    if encoding == encodings_to_try[-1]:  # Se for o último encoding
                        raise ValidationError(f"Erro ao ler arquivo CSV: Não foi possível decodificar o arquivo com nenhum encoding testado (latin-1, iso-8859-1, utf-8, cp1252). Erro original: {str(e)}")
                    continue  # Tentar próximo encoding
                except Exception as e:
                    # Outros erros (não relacionados a encoding)
                    raise ValidationError(f"Erro ao ler arquivo CSV: {str(e)}")
            
            if data is None:
                raise ValidationError("Erro ao ler arquivo CSV: Não foi possível processar o arquivo.")
        else:
            raise ValidationError("Formato de arquivo não suportado. Use .xlsx, .xls, .xlsm ou .csv")
        
        if not data:
            raise ValidationError("Arquivo vazio ou sem dados válidos")
        
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
                    
                    # Validar que temos pelo menos código da ordem de serviço
                    if not cd_ordemserv:
                        errors.append(f"Linha {row_num}: Código da ordem de serviço (CD_ORDEMSERV) é obrigatório")
                        continue
                    
                    # Preparar dados para criação/atualização
                    # Remover campos que não existem no modelo
                    ordem_data = {
                        'cd_unid': cd_unid,
                        'nome_unid': nome_unid,
                        'cd_setormanut': cd_setormanut,
                        'descr_setormanut': descr_setormanut,
                        'cd_tpcentativ': cd_tpcentativ,
                        'descr_abrev_tpcentativ': descr_abrev_tpcentativ,
                        'cd_ordemserv': cd_ordemserv,
                        'cd_maquina': cd_maquina,
                        'descr_maquina': descr_maquina,
                    }
                    
                    # Mapear campos de funcionário e data se existirem no CSV
                    # Funcionário solicitante (se disponível no CSV)
                    if cd_funciomanu or nome_funciomanu:
                        ordem_data['cd_func_solic_os'] = cd_funciomanu
                        ordem_data['nm_func_solic_os'] = nome_funciomanu
                    
                    # Data de abertura (mapear para dt_aberordser se disponível)
                    if dt_abertura:
                        ordem_data['dt_aberordser'] = dt_abertura
                    
                    # Adicionar outros campos do CSV se existirem
                    # Data Entrada
                    dt_entrada = _safe_str(row_data.get('DT_ENTRADA') or row_data.get('dt_entrada') or row_data.get('Dt_Entrada'), max_length=50)
                    if dt_entrada:
                        ordem_data['dt_entrada'] = dt_entrada
                    
                    # Funcionário Executor
                    cd_func_exec = _safe_str(row_data.get('CD_FUNC_EXEC') or row_data.get('cd_func_exec') or row_data.get('NM_FUNC_EXEC') or row_data.get('nm_func_exec'), max_length=100)
                    nm_func_exec = _safe_str(row_data.get('NM_FUNC_EXEC') or row_data.get('nm_func_exec') or row_data.get('NOME_FUNC_EXEC') or row_data.get('nome_func_exec'), max_length=255)
                    if cd_func_exec:
                        ordem_data['cd_func_exec'] = cd_func_exec
                    if nm_func_exec:
                        ordem_data['nm_func_exec'] = nm_func_exec
                    
                    # Funcionário Solicitante (se não foi mapeado acima)
                    cd_func_solic = _safe_str(row_data.get('CD_FUNC_SOLIC_OS') or row_data.get('cd_func_solic_os') or row_data.get('NM_FUNC_SOLIC_OS') or row_data.get('nm_func_solic_os'), max_length=100)
                    nm_func_solic = _safe_str(row_data.get('NM_FUNC_SOLIC_OS') or row_data.get('nm_func_solic_os') or row_data.get('NOME_FUNC_SOLIC_OS') or row_data.get('nome_func_solic_os'), max_length=255)
                    if cd_func_solic and not ordem_data.get('cd_func_solic_os'):
                        ordem_data['cd_func_solic_os'] = cd_func_solic
                    if nm_func_solic and not ordem_data.get('nm_func_solic_os'):
                        ordem_data['nm_func_solic_os'] = nm_func_solic
                    
                    # Data Encerramento
                    dt_encordmanu = _safe_str(row_data.get('DT_ENCORDMANU') or row_data.get('dt_encordmanu') or row_data.get('Dt_Encordmanu'), max_length=50)
                    if dt_encordmanu:
                        ordem_data['dt_encordmanu'] = dt_encordmanu
                    
                    # Descrição Queixa
                    descr_queixa = _safe_str(row_data.get('DESCR_QUEIXA') or row_data.get('descr_queixa') or row_data.get('Descr_Queixa'))
                    if descr_queixa:
                        ordem_data['descr_queixa'] = descr_queixa
                    
                    # Execução Tarefas
                    exec_tarefas = _safe_str(row_data.get('EXEC_TAREFAS') or row_data.get('exec_tarefas') or row_data.get('Exec_Tarefas'))
                    if exec_tarefas:
                        ordem_data['exec_tarefas'] = exec_tarefas
                    
                    # Criar ou atualizar registro
                    if update_existing:
                        ordem_obj, created = OrdemServicoCorretiva.objects.update_or_create(
                            cd_ordemserv=cd_ordemserv,
                            defaults=ordem_data
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    else:
                        ordem_obj, created = OrdemServicoCorretiva.objects.get_or_create(
                            cd_ordemserv=cd_ordemserv,
                            defaults=ordem_data
                        )
                        if created:
                            created_count += 1
                    
                except Exception as e:
                    error_msg = f"Linha {row_num}: Erro ao processar registro - {str(e)}"
                    errors.append(error_msg)
                    print(f"Erro na linha {row_num}: {e}")
                    import traceback
                    traceback.print_exc()
        
        return created_count, updated_count, errors
    
    except ValidationError as e:
        errors.append(str(e))
        return 0, 0, errors
    except Exception as e:
        error_detail = f"Erro geral ao processar arquivo: {str(e)}"
        errors.append(error_detail)
        print(f"Erro geral: {error_detail}")  # Debug
        return 0, 0, errors


def upload_maquinas_from_file(file, update_existing=False, update_fields=None) -> Tuple[int, int, List[str]]:
    """
    Faz upload de máquinas a partir de um arquivo CSV ou Excel
    
    Args:
        file: Arquivo Django UploadedFile
        update_existing: Se True, atualiza registros existentes. Se False, ignora duplicados.
        update_fields: Lista de campos a serem atualizados. Se None, atualiza todos os campos.
                      Se update_existing=False, este parâmetro é ignorado.
    
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
                    # Verificar se a linha está vazia ou tem apenas valores vazios
                    if not any(str(v).strip() if v else '' for v in row_data.values()):
                        continue
                    
                    # Mapear colunas do CSV para campos do modelo
                    # O CSV tem: CD_UNID;NOME_UNID;CS_TT_MAQUINA;DESCR_MAQUINA;CD_MAQUINA;...
                    
                    # Unidade
                    cd_unid = _safe_int(row_data.get('CD_UNID') or row_data.get('cd_unid') or row_data.get('Cd_Unid'))
                    nome_unid = _safe_str(row_data.get('NOME_UNID') or row_data.get('nome_unid') or row_data.get('Nome_Unid'), max_length=255)
                    
                    # Máquina
                    cs_tt_maquina = _safe_int(row_data.get('CS_TT_MAQUINA') or row_data.get('cs_tt_maquina') or row_data.get('Cs_Tt_Maquina'))
                    descr_maquina = _safe_str(row_data.get('DESCR_MAQUINA') or row_data.get('descr_maquina') or row_data.get('Descr_Maquina'), max_length=500)
                    cd_maquina = _safe_int(row_data.get('CD_MAQUINA') or row_data.get('cd_maquina') or row_data.get('Cd_Maquina'))
                    
                    # Setor Manutenção
                    cd_setormanut = _safe_str(row_data.get('CD_SETORMANUT') or row_data.get('cd_setormanut') or row_data.get('Cd_Setormanut'), max_length=50)
                    descr_setormanut = _safe_str(row_data.get('DESCR_SETORMANUT') or row_data.get('descr_setormanut') or row_data.get('Descr_Setormanut'), max_length=255)
                    
                    # Prioridade
                    cd_priomaqutv = _safe_int(row_data.get('CD_PRIOMAQUTV') or row_data.get('cd_priomaqutv') or row_data.get('Cd_Priomaqutv'))
                    
                    # Patrimônio
                    nro_patrimonio = _safe_str(row_data.get('NRO_PATRIMONIO') or row_data.get('nro_patrimonio') or row_data.get('Nro_Patrimonio'), max_length=100)
                    
                    # Modelo e Grupo
                    cd_modelo = _safe_int(row_data.get('CD_MODELO') or row_data.get('cd_modelo') or row_data.get('Cd_Modelo'))
                    cd_grupo = _safe_int(row_data.get('CD_GRUPO') or row_data.get('cd_grupo') or row_data.get('Cd_Grupo'))
                    
                    # Tipo Centro de Atividade
                    cd_tpcentativ = _safe_int(row_data.get('CD_TPCENTATIV') or row_data.get('cd_tpcentativ') or row_data.get('Cd_Tpcentativ'))
                    
                    # Gerência
                    descr_gerenc = _safe_str(row_data.get('DESCR_GERENC') or row_data.get('descr_gerenc') or row_data.get('Descr_Gerenc'), max_length=255)
                    
                    # Validar que temos pelo menos código da máquina
                    if not cd_maquina:
                        errors.append(f"Linha {row_num}: Código da máquina (CD_MAQUINA) é obrigatório")
                        continue
                    
                    # Preparar dados para criação/atualização
                    maquina_data = {
                        'cd_unid': cd_unid,
                        'nome_unid': nome_unid,
                        'cs_tt_maquina': cs_tt_maquina,
                        'descr_maquina': descr_maquina,
                        'cd_setormanut': cd_setormanut,
                        'descr_setormanut': descr_setormanut,
                        'cd_priomaqutv': cd_priomaqutv,
                        'nro_patrimonio': nro_patrimonio,
                        'cd_modelo': cd_modelo,
                        'cd_grupo': cd_grupo,
                        'cd_tpcentativ': cd_tpcentativ,
                        'descr_gerenc': descr_gerenc,
                    }
                    
                    # Criar ou atualizar registro
                    if update_existing:
                        # Se update_fields foi especificado, filtrar apenas os campos selecionados
                        if update_fields:
                            # Buscar máquina existente primeiro
                            try:
                                maquina_obj = Maquina.objects.get(cd_maquina=cd_maquina)
                                # Atualizar apenas campos selecionados
                                for field in update_fields:
                                    if field in maquina_data:
                                        setattr(maquina_obj, field, maquina_data[field])
                                maquina_obj.save()
                                updated_count += 1
                            except Maquina.DoesNotExist:
                                # Se não existe, criar novo registro com todos os campos
                                maquina_obj = Maquina.objects.create(
                                    cd_maquina=cd_maquina,
                                    **maquina_data
                                )
                                created_count += 1
                        else:
                            # Comportamento padrão: atualizar todos os campos
                            maquina_obj, created = Maquina.objects.update_or_create(
                            cd_maquina=cd_maquina,
                            defaults=maquina_data
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    else:
                        maquina_obj, created = Maquina.objects.get_or_create(
                            cd_maquina=cd_maquina,
                            defaults=maquina_data
                        )
                        if created:
                            created_count += 1
                    
                except Exception as e:
                    error_msg = f"Linha {row_num}: Erro ao processar registro - {str(e)}"
                    errors.append(error_msg)
                    print(f"Erro na linha {row_num}: {e}")
                    import traceback
                    traceback.print_exc()
        
        return created_count, updated_count, errors
    
    except ValidationError as e:
        errors.append(str(e))
        return 0, 0, errors
    except Exception as e:
        error_detail = f"Erro geral ao processar arquivo: {str(e)}"
        errors.append(error_detail)
        print(f"Erro geral: {error_detail}")  # Debug
        import traceback
        traceback.print_exc()
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
                    # Verificar se a linha está vazia ou tem apenas valores vazios
                    if not any(str(v).strip() if v else '' for v in row_data.values()):
                            continue
                    
                    # Mapear colunas do CSV para campos do modelo
                    # O CSV tem: CD_UNID;NOME_UNID;CD_ITEM;DESCR_ITEM;...
                    
                    # Unidade
                    cd_unid = _safe_int(row_data.get('CD_UNID') or row_data.get('cd_unid') or row_data.get('Cd_Unid'))
                    nome_unid = _safe_str(row_data.get('NOME_UNID') or row_data.get('nome_unid') or row_data.get('Nome_Unid'), max_length=255)
                    
                    # Item
                    cd_item = _safe_int(row_data.get('CD_ITEM') or row_data.get('cd_item') or row_data.get('Cd_Item'))
                    descr_item = _safe_str(row_data.get('DESCR_ITEM') or row_data.get('descr_item') or row_data.get('Descr_Item'), max_length=500)
                    
                    # Unidade de Medida
                    unidade_medida = _safe_str(row_data.get('UNIDADE_MEDIDA') or row_data.get('unidade_medida') or row_data.get('Unidade_Medida'), max_length=50)
                    
                    # Quantidade
                    qtde = _safe_decimal(row_data.get('QTDE') or row_data.get('qtde') or row_data.get('Qtde'))
                    
                    # Validar que temos pelo menos código do item
                    if not cd_item:
                        errors.append(f"Linha {row_num}: Código do item (CD_ITEM) é obrigatório")
                        continue
                    
                    # Preparar dados para criação/atualização
                    item_data = {
                        'cd_unid': cd_unid,
                        'nome_unid': nome_unid,
                        'descr_item': descr_item,
                        'unidade_medida': unidade_medida,
                        'qtde': qtde,
                    }
                    
                    # Criar ou atualizar registro
                    if update_existing:
                        item_obj, created = ItemEstoque.objects.update_or_create(
                            codigo_item=cd_item,
                            defaults=item_data
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    else:
                        item_obj, created = ItemEstoque.objects.get_or_create(
                            codigo_item=cd_item,
                            defaults=item_data
                        )
                        if created:
                            created_count += 1
                        
                except Exception as e:
                    error_msg = f"Linha {row_num}: Erro ao processar registro - {str(e)}"
                    errors.append(error_msg)
                    print(f"Erro na linha {row_num}: {e}")
                    import traceback
                    traceback.print_exc()
        
        return created_count, updated_count, errors
    
    except ValidationError as e:
        errors.append(str(e))
        return 0, 0, errors
    except Exception as e:
        error_detail = f"Erro geral ao processar arquivo: {str(e)}"
        errors.append(error_detail)
        print(f"Erro geral: {error_detail}")  # Debug
        import traceback
        traceback.print_exc()
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
    from app.models import CentroAtividade, LocalCentroAtividade
    
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
                    # Verificar se a linha está vazia ou tem apenas valores vazios
                    if not any(str(v).strip() if v else '' for v in row_data.values()):
                        continue
                    
                    # Normalizar nomes de colunas (lidar com problemas de encoding)
                    ca_value = _find_column_by_partial_match(row_data, ['ca', 'centro', 'atividade'])
                    sigla_value = _find_column_by_partial_match(row_data, ['sigla'])
                    descricao_value = _find_column_by_partial_match(row_data, ['descricao', 'descrio'])
                    indice_value = _find_column_by_partial_match(row_data, ['indice', 'ndice'])
                    encarregado_value = _find_column_by_partial_match(row_data, ['encarregado', 'responsavel', 'responsvel'])
                    local_value = _find_column_by_partial_match(row_data, ['local'])
                    
                    # Se não encontrou pelo método parcial, tentar nomes diretos
                    if not ca_value:
                        ca_value = row_data.get('CA') or row_data.get('ca') or row_data.get('Ca')
                    if not sigla_value:
                        sigla_value = row_data.get('SIGLA') or row_data.get('sigla') or row_data.get('Sigla')
                    if not descricao_value:
                        descricao_value = row_data.get('DESCRIÇÃO') or row_data.get('DESCRIO') or row_data.get('Descrição') or row_data.get('Descrio') or row_data.get('descrição') or row_data.get('descrio')
                    if not indice_value:
                        indice_value = row_data.get('ÍNDICE') or row_data.get('INDICE') or row_data.get('Índice') or row_data.get('Indice') or row_data.get('índice') or row_data.get('indice')
                    if not encarregado_value:
                        encarregado_value = row_data.get('ENCARREGADO RESPONSÁVEL') or row_data.get('ENCARREGADO RESPONSVEL') or row_data.get('Encarregado Responsável') or row_data.get('Encarregado Responsavel') or row_data.get('encarregado responsável') or row_data.get('encarregado responsavel')
                    if not local_value:
                        local_value = row_data.get('LOCAL') or row_data.get('local') or row_data.get('Local')
                    
                    # Validar que temos pelo menos o código CA
                    if not ca_value:
                        errors.append(f"Linha {row_num}: Campo 'CA' é obrigatório")
                        continue
                    
                    # Converter CA para inteiro
                    try:
                        ca_int = int(float(str(ca_value)))
                    except (ValueError, TypeError):
                        errors.append(f"Linha {row_num}: Valor de CA inválido: {ca_value}")
                        continue
                    
                    # Converter índice para inteiro se existir
                    indice_int = None
                    if indice_value:
                        try:
                            indice_int = int(float(str(indice_value)))
                        except (ValueError, TypeError):
                            pass  # Índice é opcional
                    
                    # Preparar dados para criação/atualização do CA
                    ca_data = {
                        'sigla': _safe_str(sigla_value, max_length=50),
                        'descricao': _safe_str(descricao_value, max_length=500),
                        'indice': indice_int,
                        'encarregado_responsavel': _safe_str(encarregado_value, max_length=255),
                    }
                    
                    # Criar ou atualizar CA
                    if update_existing:
                        ca_obj, ca_created = CentroAtividade.objects.update_or_create(
                            ca=ca_int,
                            defaults=ca_data
                        )
                        if ca_created:
                            created_count += 1
                        else:
                            updated_count += 1
                    else:
                        ca_obj, ca_created = CentroAtividade.objects.get_or_create(
                            ca=ca_int,
                            defaults=ca_data
                        )
                        if ca_created:
                            created_count += 1
                    
                    # Criar LocalCentroAtividade se houver valor de local
                    if local_value:
                        local_str = _safe_str(local_value, max_length=255)
                        if local_str:
                            if update_existing:
                                local_obj, local_created = LocalCentroAtividade.objects.update_or_create(
                                    centro_atividade=ca_obj,
                                    local=local_str,
                                    defaults={}
                                )
                                if local_created:
                                    created_count += 1
                                else:
                                    updated_count += 1
                            else:
                                local_obj, local_created = LocalCentroAtividade.objects.get_or_create(
                                    centro_atividade=ca_obj,
                                    local=local_str,
                                    defaults={}
                                )
                                if local_created:
                                    created_count += 1
                    
                except Exception as e:
                    error_msg = f"Linha {row_num}: Erro ao processar registro - {str(e)}"
                    errors.append(error_msg)
                    print(f"Erro na linha {row_num}: {e}")
                    import traceback
                    traceback.print_exc()
        
        return created_count, updated_count, errors
    
    except ValidationError as e:
        errors.append(str(e))
        return 0, 0, errors
    except Exception as e:
        error_detail = f"Erro geral ao processar arquivo: {str(e)}"
        errors.append(error_detail)
        print(f"Erro geral: {error_detail}")  # Debug
        import traceback
        traceback.print_exc()
        return 0, 0, errors


def _find_column_by_partial_match(row_data, keywords):
    """
    Tenta encontrar uma coluna em row_data que contenha qualquer uma das palavras-chave.
    Útil para lidar com problemas de encoding ou pequenas variações.
    """
    for key, value in row_data.items():
        normalized_key = str(key).strip().lower().replace(' ', '_')
        for keyword in keywords:
            if keyword in normalized_key:
                return value
    return None


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
                    # Verificar se a linha está vazia ou tem apenas valores vazios
                    if not any(str(v).strip() if v else '' for v in row_data.values()):
                            continue
                    
                    # Mapear colunas do CSV para campos do modelo
                    cadastro = _safe_str(row_data.get('CADASTRO') or row_data.get('cadastro') or row_data.get('Cadastro'), max_length=1000)
                    nome = _safe_str(row_data.get('NOME') or row_data.get('nome') or row_data.get('Nome'), max_length=1000)
                    admissao_str = row_data.get('ADMISSAO') or row_data.get('admissao') or row_data.get('Admissao')
                    cargo = _safe_str(row_data.get('CARGO') or row_data.get('cargo') or row_data.get('Cargo'), max_length=1000)
                    posto = _safe_str(row_data.get('POSTO') or row_data.get('posto') or row_data.get('Posto'), max_length=1000)
                    horario_inicio_str = row_data.get('HORARIO_INICIO') or row_data.get('horario_inicio') or row_data.get('Horario_Inicio')
                    horario_fim_str = row_data.get('HORARIO_FIM') or row_data.get('horario_fim') or row_data.get('Horario_Fim')
                    tempo_trabalho = _safe_str(row_data.get('TEMPO_TRABALHO') or row_data.get('tempo_trabalho') or row_data.get('Tempo_Trabalho'), max_length=250)
                    tipo = _safe_str(row_data.get('TIPO') or row_data.get('tipo') or row_data.get('Tipo'), max_length=25)
                    
                    # Validar que temos pelo menos o cadastro
                    if not cadastro:
                        errors.append(f"Linha {row_num}: Campo 'CADASTRO' é obrigatório")
                        continue
                    
                    # Converter data de admissão
                    admissao_date = None
                    if admissao_str:
                        try:
                            # Tentar diferentes formatos de data
                            admissao_date = datetime.strptime(str(admissao_str).strip(), '%d/%m/%Y').date()
                        except ValueError:
                            try:
                                admissao_date = datetime.strptime(str(admissao_str).strip(), '%Y-%m-%d').date()
                            except ValueError:
                                errors.append(f"Linha {row_num}: Data de admissão inválida: {admissao_str}")
                    
                    # Converter horários
                    horario_inicio_time = None
                    horario_fim_time = None
                    if horario_inicio_str:
                        try:
                            horario_inicio_time = datetime.strptime(str(horario_inicio_str).strip(), '%H:%M:%S').time()
                        except ValueError:
                            try:
                                horario_inicio_time = datetime.strptime(str(horario_inicio_str).strip(), '%H:%M').time()
                            except ValueError:
                                pass  # Horário é opcional
                    
                    if horario_fim_str:
                        try:
                            horario_fim_time = datetime.strptime(str(horario_fim_str).strip(), '%H:%M:%S').time()
                        except ValueError:
                            try:
                                horario_fim_time = datetime.strptime(str(horario_fim_str).strip(), '%H:%M').time()
                            except ValueError:
                                pass  # Horário é opcional
                    
                    # Preparar dados para criação/atualização
                    manutentor_data = {
                        'Nome': nome,
                        'Admissao': admissao_date,
                        'Cargo': cargo,
                        'Posto': posto,
                        'horario_inicio': horario_inicio_time,
                        'horario_fim': horario_fim_time,
                        'tempo_trabalho': tempo_trabalho,
                        'tipo': tipo,
                    }
                    
                    # Criar ou atualizar registro
                    if update_existing:
                        manutentor_obj, created = Manutentor.objects.update_or_create(
                            Cadastro=cadastro,
                            defaults=manutentor_data
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    else:
                        manutentor_obj, created = Manutentor.objects.get_or_create(
                            Cadastro=cadastro,
                            defaults=manutentor_data
                        )
                        if created:
                            created_count += 1
                    
                except Exception as e:
                    error_msg = f"Linha {row_num}: Erro ao processar registro - {str(e)}"
                    errors.append(error_msg)
                    print(f"Erro na linha {row_num}: {e}")
                    import traceback
                    traceback.print_exc()
        
        return created_count, updated_count, errors
    
    except ValidationError as e:
        errors.append(str(e))
        return 0, 0, errors
    except Exception as e:
        error_detail = f"Erro geral ao processar arquivo: {str(e)}"
        errors.append(error_detail)
        print(f"Erro geral: {error_detail}")  # Debug
        import traceback
        traceback.print_exc()
        return 0, 0, errors


def _safe_int(value, default=None):
    """Converte valor para inteiro de forma segura"""
    if value is None or value == '':
        return default
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default


def _safe_str(value, max_length=None, default=''):
    """Converte valor para string de forma segura"""
    if value is None:
        return default
    str_value = str(value).strip()
    if max_length and len(str_value) > max_length:
        str_value = str_value[:max_length]
    return str_value


def _safe_decimal(value, default=None):
    """Converte valor para Decimal de forma segura"""
    from decimal import Decimal, InvalidOperation
    if value is None or value == '':
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _fix_funcionario_columns(row_data):
    """
    Corrige deslocamento de colunas para 'Funcionário' e 'Nome Funcionário'
    Se 'Funcionário' estiver vazio, assume que os dados corretos estão na próxima coluna
    """
    funcionario_key = None
    nome_funcionario_key = None
    
    # Encontrar as chaves corretas
    for key in row_data.keys():
        key_lower = str(key).lower().strip()
        if 'funcionário' in key_lower or 'funcionario' in key_lower:
            if 'nome' in key_lower:
                nome_funcionario_key = key
            else:
                funcionario_key = key
    
    if not funcionario_key or not nome_funcionario_key:
        return row_data
    
    funcionario_value = row_data.get(funcionario_key, '').strip() if row_data.get(funcionario_key) else ''
    nome_funcionario_value = row_data.get(nome_funcionario_key, '').strip() if row_data.get(nome_funcionario_key) else ''
    
    # Se "Funcionário" está vazio, procurar dados nas próximas colunas
    if not funcionario_value:
        # Encontrar todas as chaves após "Funcionário"
        keys_list = list(row_data.keys())
        funcionario_idx = keys_list.index(funcionario_key) if funcionario_key in keys_list else -1
        
        if funcionario_idx >= 0:
            # Procurar primeira coluna não vazia após "Funcionário"
            for i in range(funcionario_idx + 1, len(keys_list)):
                next_key = keys_list[i]
                next_value = row_data.get(next_key, '').strip() if row_data.get(next_key) else ''
                
                if next_value:
                    # Se o valor contém apenas números, é provavelmente o código do funcionário
                    if next_value.isdigit():
                        row_data[funcionario_key] = next_value
                        # Procurar próxima coluna não vazia para o nome
                        for j in range(i + 1, len(keys_list)):
                            next_name_key = keys_list[j]
                            next_name_value = row_data.get(next_name_key, '').strip() if row_data.get(next_name_key) else ''
                            if next_name_value and not next_name_value.isdigit():
                                row_data[nome_funcionario_key] = next_name_value
                                # Limpar colunas deslocadas
                                row_data[next_key] = ''
                                if j < len(keys_list):
                                    row_data[next_name_key] = ''
                                break
                        break
    
    # Se "Nome Funcionário" contém apenas números, assumir que o nome correto está na próxima coluna
    if nome_funcionario_value and nome_funcionario_value.isdigit():
        # Mover número para "Funcionário" se estiver vazio
        if not funcionario_value:
            row_data[funcionario_key] = nome_funcionario_value
        
        # Encontrar próxima coluna não vazia para o nome
        keys_list = list(row_data.keys())
        nome_funcionario_idx = keys_list.index(nome_funcionario_key) if nome_funcionario_key in keys_list else -1
        
        if nome_funcionario_idx >= 0:
            for i in range(nome_funcionario_idx + 1, len(keys_list)):
                next_key = keys_list[i]
                next_value = row_data.get(next_key, '').strip() if row_data.get(next_key) else ''
                if next_value and not next_value.isdigit():
                    row_data[nome_funcionario_key] = next_value
                    # Limpar coluna deslocada
                    row_data[next_key] = ''
                    break
    
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
                    
                    # Corrigir deslocamento de colunas para Funcionário
                    row_data = _fix_funcionario_columns(row_data)
                    
                    # Mapear colunas do CSV para campos do modelo
                    # O CSV tem: CD_UNID;NOME_UNID;NUMERO_PLANO;DESCR_PLANO;CD_MAQUINA;DESCR_MAQUINA;...
                    
                    # Unidade
                    cd_unid = _safe_int(row_data.get('CD_UNID') or row_data.get('cd_unid') or row_data.get('Cd_Unid'))
                    nome_unid = _safe_str(row_data.get('NOME_UNID') or row_data.get('nome_unid') or row_data.get('Nome_Unid'), max_length=255)
                    
                    # Plano
                    numero_plano = _safe_int(row_data.get('NUMERO_PLANO') or row_data.get('numero_plano') or row_data.get('Numero_Plano'))
                    descr_plano = _safe_str(row_data.get('DESCR_PLANO') or row_data.get('descr_plano') or row_data.get('Descr_Plano'), max_length=255)
                    
                    # Máquina
                    cd_maquina = _safe_int(row_data.get('CD_MAQUINA') or row_data.get('cd_maquina') or row_data.get('Cd_Maquina'))
                    descr_maquina = _safe_str(row_data.get('DESCR_MAQUINA') or row_data.get('descr_maquina') or row_data.get('Descr_Maquina'), max_length=500)
                    
                    # Sequências
                    sequencia_tarefa = _safe_int(row_data.get('SEQUENCIA_TAREFA') or row_data.get('sequencia_tarefa') or row_data.get('Sequencia_Tarefa'))
                    sequencia_manutencao = _safe_int(row_data.get('SEQUENCIA_MANUTENCAO') or row_data.get('sequencia_manutencao') or row_data.get('Sequencia_Manutencao'))
                    
                    # Tarefa
                    descr_tarefa = _safe_str(row_data.get('DESCR_TAREFA') or row_data.get('descr_tarefa') or row_data.get('Descr_Tarefa'))
                    
                    # Funcionário
                    funcionario = _safe_str(row_data.get('FUNCIONÁRIO') or row_data.get('FUNCIONARIO') or row_data.get('Funcionário') or row_data.get('Funcionario') or row_data.get('funcionário') or row_data.get('funcionario'), max_length=100)
                    nome_funcionario = _safe_str(row_data.get('NOME_FUNCIONÁRIO') or row_data.get('NOME_FUNCIONARIO') or row_data.get('Nome_Funcionário') or row_data.get('Nome_Funcionario') or row_data.get('nome_funcionário') or row_data.get('nome_funcionario'), max_length=255)
                    
                    # Data Execução
                    data_execucao_str = row_data.get('DATA_EXECUCAO') or row_data.get('data_execucao') or row_data.get('Data_Execucao')
                    data_execucao = None
                    if data_execucao_str:
                        try:
                            from datetime import datetime
                            # Tentar diferentes formatos de data
                            data_execucao = datetime.strptime(str(data_execucao_str).strip(), '%d/%m/%Y').date()
                        except ValueError:
                            try:
                                data_execucao = datetime.strptime(str(data_execucao_str).strip(), '%Y-%m-%d').date()
                            except ValueError:
                                pass  # Data é opcional
                    
                    # Validar campos obrigatórios
                    if not numero_plano:
                        errors.append(f"Linha {row_num}: Campo 'NUMERO_PLANO' é obrigatório")
                        continue
                    
                    if not cd_maquina:
                        errors.append(f"Linha {row_num}: Campo 'CD_MAQUINA' é obrigatório")
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
                                errors.append(f"Linha {row_num}: Máquina com código {cd_maquina} não encontrada")
                                continue
                    
                    # Preparar dados para criação/atualização
                    plano_data = {
                        'cd_unid': cd_unid,
                        'nome_unid': nome_unid,
                        'descr_plano': descr_plano,
                        'maquina': maquina,
                        'cd_maquina': cd_maquina,
                        'descr_maquina': descr_maquina,
                        'sequencia_tarefa': sequencia_tarefa,
                        'sequencia_manutencao': sequencia_manutencao,
                        'descr_tarefa': descr_tarefa,
                        'funcionario': funcionario,
                        'nome_funcionario': nome_funcionario,
                        'data_execucao': data_execucao,
                    }
                    
                    # Criar ou atualizar registro
                    if update_existing:
                        plano_obj, created = PlanoPreventiva.objects.update_or_create(
                            numero_plano=numero_plano,
                            cd_maquina=cd_maquina,
                            sequencia_tarefa=sequencia_tarefa,
                            sequencia_manutencao=sequencia_manutencao,
                            defaults=plano_data
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    else:
                        plano_obj, created = PlanoPreventiva.objects.get_or_create(
                            numero_plano=numero_plano,
                            cd_maquina=cd_maquina,
                            sequencia_tarefa=sequencia_tarefa,
                            sequencia_manutencao=sequencia_manutencao,
                            defaults=plano_data
                        )
                        if created:
                            created_count += 1
                    
                except Exception as e:
                    error_msg = f"Linha {row_num}: Erro ao processar registro - {str(e)}"
                    errors.append(error_msg)
                    print(f"Erro na linha {row_num}: {e}")
                    import traceback
                    traceback.print_exc()
        
        return created_count, updated_count, errors
        
    except ValidationError as e:
        errors.append(str(e))
        return 0, 0, errors
    except Exception as e:
        error_detail = f"Erro geral ao processar arquivo: {str(e)}"
        errors.append(error_detail)
        print(f"Erro geral: {error_detail}")  # Debug
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
                                # Criar máquina básica se não existir
                                maquina = Maquina.objects.create(
                                    cd_maquina=cd_maquina,
                                    descr_maquina=descr_maquina or f'Máquina {cd_maquina}',
                                    cd_unid=cd_unid,
                                    nome_unid=nome_unid,
                                    cd_setormanut=cd_setormanut,
                                    descr_setormanut=descr_setormanut,
                                    cd_tpcentativ=cd_tpcentativ,
                                )
                                maquinas_cache[cd_maquina] = maquina
                    
                    # Preparar dados para criação/atualização
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
                        'maquina': maquina,
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
                    }
                    
                    # Criar ou atualizar registro
                    if update_existing:
                        roteiro_obj, created = RoteiroPreventiva.objects.update_or_create(
                            cd_ordemserv=cd_ordemserv,
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
                        roteiro_obj, created = RoteiroPreventiva.objects.get_or_create(
                            cd_ordemserv=cd_ordemserv,
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


def upload_52_semanas_from_file(file, update_existing=False) -> Tuple[int, int, List[str]]:
    """
    Faz upload de semanas (52 semanas) a partir de um arquivo Excel
    
    Args:
        file: Arquivo Django UploadedFile
        update_existing: Se True, atualiza registros existentes. Se False, ignora duplicados.
    
    Returns:
        Tupla (created_count, updated_count, errors)
    """
    from app.models import Semana52
    from datetime import datetime
    import re
    
    errors = []
    created_count = 0
    updated_count = 0
    
    # Mapeamento de meses em português para inglês
    meses_pt_para_en = {
        'janeiro': 'January', 'fevereiro': 'February', 'março': 'March', 'marco': 'March',
        'abril': 'April', 'maio': 'May', 'junho': 'June',
        'julho': 'July', 'agosto': 'August', 'setembro': 'September',
        'outubro': 'October', 'novembro': 'November', 'dezembro': 'December'
    }
    
    def limpar_texto(texto):
        """Remove caracteres especiais e normaliza espaços"""
        if not texto:
            return None
        texto = str(texto).strip()
        # Remover \xa0 (non-breaking space) e outros caracteres especiais
        texto = texto.replace('\xa0', ' ').replace('\u00a0', ' ')
        # Normalizar espaços múltiplos
        texto = re.sub(r'\s+', ' ', texto)
        return texto.strip()
    
    def converter_data_pt_para_en(data_str):
        """Converte data em português para formato que datetime.strptime entende"""
        if not data_str:
            return None
        
        data_str = limpar_texto(data_str)
        if not data_str:
            return None
        
        # Tentar substituir meses em português por inglês
        data_str_lower = data_str.lower()
        for mes_pt, mes_en in meses_pt_para_en.items():
            if mes_pt in data_str_lower:
                # Substituir mantendo o case original
                pattern = re.compile(re.escape(mes_pt), re.IGNORECASE)
                data_str = pattern.sub(mes_en, data_str)
                break
        
        return data_str
    
    # Determinar tipo de arquivo
    file_name = file.name.lower()
    
    try:
        # Ler arquivo Excel
        if file_name.endswith(('.xlsx', '.xls', '.xlsm')):
            data = read_excel_file(file)
            print(f"DEBUG: Arquivo lido com sucesso. Total de linhas: {len(data)}")
            if data:
                print(f"DEBUG: Primeira linha de dados: {data[0]}")
        else:
            raise ValidationError("Formato de arquivo não suportado. Use .xlsx, .xls ou .xlsm")
        
        if not data:
            raise ValidationError("Arquivo vazio ou sem dados válidos")
        
        # Processar dados em transação
        with transaction.atomic():
            for row_idx, row_data in enumerate(data, start=2):  # Começar em 2 porque linha 1 é cabeçalho
                try:
                    # Verificar se a linha está vazia
                    if not any(str(v).strip() if v else '' for v in row_data.values()):
                        continue
                    
                    # Normalizar nomes de colunas (case-insensitive)
                    semana_value = None
                    inicio_value = None
                    fim_value = None
                    
                    for key, value in row_data.items():
                        key_lower = str(key).lower().strip()
                        if 'semana' in key_lower:
                            semana_value = value
                        elif 'inicio' in key_lower or 'início' in key_lower:
                            inicio_value = value
                        elif 'fim' in key_lower:
                            fim_value = value
                    
                    # Debug: mostrar o que foi encontrado
                    if row_idx == 2:  # Apenas para primeira linha de dados
                        print(f"DEBUG Linha {row_idx}: semana_value={semana_value}, inicio_value={inicio_value}, fim_value={fim_value}")
                        print(f"DEBUG Linha {row_idx}: row_data keys={list(row_data.keys())}")
                    
                    if not semana_value:
                        errors.append(f"Linha {row_idx}: Campo 'semana' está vazio. Colunas encontradas: {', '.join(str(k) for k in row_data.keys())}")
                        continue
                    
                    # Limpar valores de semana
                    semana_value = limpar_texto(semana_value)
                    if not semana_value:
                        errors.append(f"Linha {row_idx}: Campo 'semana' está vazio após limpeza")
                        continue
                    
                    # Converter datas
                    inicio_date = None
                    fim_date = None
                    
                    if inicio_value:
                        try:
                            inicio_str = converter_data_pt_para_en(inicio_value)
                            if inicio_str:
                                # Tentar diferentes formatos de data
                                try:
                                    # Formato: "DD Month YYYY" (ex: "22 December 2025")
                                    inicio_date = datetime.strptime(inicio_str, '%d %B %Y').date()
                                except ValueError:
                                    try:
                                        # Formato: "DD/MM/YYYY"
                                        inicio_date = datetime.strptime(inicio_str, '%d/%m/%Y').date()
                                    except ValueError:
                                        try:
                                            # Formato: "YYYY-MM-DD"
                                            inicio_date = datetime.strptime(inicio_str, '%Y-%m-%d').date()
                                        except ValueError:
                                            errors.append(f"Linha {row_idx}: Data de início inválida: {inicio_value}")
                        except Exception as e:
                            errors.append(f"Linha {row_idx}: Erro ao processar data de início '{inicio_value}': {str(e)}")
                    
                    if fim_value:
                        try:
                            fim_str = converter_data_pt_para_en(fim_value)
                            if fim_str:
                                # Tentar diferentes formatos de data
                                try:
                                    # Formato: "DD Month YYYY" (ex: "28 December 2025")
                                    fim_date = datetime.strptime(fim_str, '%d %B %Y').date()
                                except ValueError:
                                    try:
                                        # Formato: "DD/MM/YYYY"
                                        fim_date = datetime.strptime(fim_str, '%d/%m/%Y').date()
                                    except ValueError:
                                        try:
                                            # Formato: "YYYY-MM-DD"
                                            fim_date = datetime.strptime(fim_str, '%Y-%m-%d').date()
                                        except ValueError:
                                            errors.append(f"Linha {row_idx}: Data de fim inválida: {fim_value}")
                        except Exception as e:
                            errors.append(f"Linha {row_idx}: Erro ao processar data de fim '{fim_value}': {str(e)}")
                    
                    # Criar ou atualizar registro
                    if update_existing:
                        semana_obj, created = Semana52.objects.update_or_create(
                            semana=semana_value,
                            defaults={
                                'inicio': inicio_date,
                                'fim': fim_date
                            }
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    else:
                        semana_obj, created = Semana52.objects.get_or_create(
                            semana=semana_value,
                            defaults={
                                'inicio': inicio_date,
                                'fim': fim_date
                            }
                        )
                        if created:
                            created_count += 1
                        else:
                            # Registro já existe, ignorar
                            pass
                            
                except Exception as e:
                    error_msg = f"Linha {row_idx}: Erro ao processar registro - {str(e)}"
                    errors.append(error_msg)
                    print(f"Erro na linha {row_idx}: {e}")
                    import traceback
                    traceback.print_exc()
        
        return created_count, updated_count, errors
        
    except ValidationError as e:
        errors.append(str(e))
        return 0, 0, errors
    except Exception as e:
        error_msg = f"Erro geral ao processar arquivo: {str(e)}"
        errors.append(error_msg)
        print(f"Erro geral: {error_msg}")
        import traceback
        traceback.print_exc()
        return 0, 0, errors
