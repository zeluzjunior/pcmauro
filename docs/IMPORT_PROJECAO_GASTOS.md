# Importação de Projeção de Gastos

## Visão Geral

O processo de importação em `/importar/projecao-gastos/` lê o arquivo Excel e grava na tabela `ProjecaoGasto`.

- **Planilha obrigatória:** `GASTOS`
- **Função:** `app.utils.upload_projecao_gastos_from_file`
- **Chave única:** `id_excel` + `setor` (mesmo ID pode existir para setores diferentes)

---

## Colunas do Excel → Campos do Modelo

| Coluna Excel (variações) | Campo ProjecaoGasto | Observação |
|--------------------------|---------------------|------------|
| ID | id_excel | Obrigatório, chave de identificação |
| SETOR, SETOR  | setor | Obrigatório para chave composta |
| SOLICITANTE | solicitante | |
| FORNECEDOR NOME FANTASIA / FORNECEDOR | fornecedor_nome_fantasia | |
| FORNECEDOR CNPJ | fornecedor_cnpj | |
| DESCRIÇÃO DO SERVIÇO | descricao | |
| VALOR TOTAL | valor_total | |
| PREVISÃO P/ EXECUÇÃO | previsao_execucao | Também gera mes_referencia e ano_referencia |
| USO CONTÁBIL | uso_contabil | |
| NÚMERO DA NOTA FISCAL | numero_nf | |
| TIPO DE SOLICITAÇÃO | tipo_solicitacao | |
| ORDEM DE SERVIÇO | numero_ordem_servico | |
| DATA DE ABERTURA DA REQUISIÇÃO | data_abertura_requisicao | |
| NÚMERO DA REQUISIÇÃO DE COMPRA | numero_requisicao_compra | |
| NÚMERO DO PEDIDO DE COMPRA | numero_pedido_compra | |
| SERVIÇO CONCLUÍDO | servico_concluido | |
| NF DE SERVIÇO RECEBIDA | nf_servico_recebida | |
| NF ENVIADA PARA LANÇAMENTO | nf_enviada_lancamento | |
| OBSERVAÇÕES | observacoes | |

---

## Colunas Extras no Excel (não mapeadas)

Se o arquivo possui **mais colunas** do que as listadas acima, elas são armazenadas em **`dados_adicionais`** (campo JSON do modelo). Nenhum dado é perdido na importação.

---

## Campos do Modelo sem Fonte Direta no Excel

- `valor_planejado`, `valor_realizado`, `valor_projetado` (compatibilidade)
- `data_planejada`, `data_realizada` (compatibilidade)
- `nome_centro_atividade`, `status` (compatibilidade)

---

## Como Analisar o Arquivo

Execute o script de análise passando o caminho do Excel:

```bash
python analise_import_projecao.py "caminho/para/9. PCM - Previsão de Gastos 2025 e 2026.xlsx"
```

O script lista:
1. Todas as colunas do Excel
2. Quais colunas estão mapeadas e quais não estão
3. Campos do modelo sem fonte no Excel

---

## Adicionando Novas Colunas ao Mapeamento

Para mapear uma nova coluna do Excel para um campo do modelo:

1. Adicione as variações de nome em `find_column_value` em `app.utils.upload_projecao_gastos_from_file`
2. Adicione a extração do valor (ex: `nova_col = _safe_str(find_column_value(row_data, ['NOVA COLUNA']), max_length=100)`)
3. Inclua em `projecao_data`: `'campo_modelo': nova_col`
4. Adicione o nome normalizado em `mapped_column_names` para não ir em dados_adicionais
