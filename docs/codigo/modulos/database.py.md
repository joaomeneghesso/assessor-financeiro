---
tipo: modulo
grupo: Dados, backup e segurança
linhas: 1960
tags: [modulo, dados-backup-e-seguranca]
---
# database.py

**Grupo:** [[Dados, backup e segurança]] · **Linhas:** 1960 · **Funções:** 88 · **Classes:** 3

> [!warning] Linha de base
> Limite de 1961 linhas (hoje 1960). Este arquivo não pode crescer: código novo vai em módulo próprio.

## Usa

- [[categorias.py]]
- [[conciliacao.py]] *(importação tardia, dentro de função)*
- [[config.py]]
- [[faturas_competencia.py]] *(importação tardia, dentro de função)*
- [[fixos_vigencia.py]] *(importação tardia, dentro de função)*
- [[money.py]] *(importação tardia, dentro de função)*
- [[relogio.py]]

## Usado por

- [[app.py]] — `buscar_transacao_por_id`, `init_db`, `registrar_auditoria`, `verificar_banco_para_iniciar`
- [[assessor_orientacao.py]] — `get_connection`, `listar_metas`, `read_only_mode`, `registrar_auditoria`
- [[busca_lancamentos.py]] — `atualizar_categoria_em_lote`, `buscar_todas_transacoes`, `read_only_mode`, `registrar_auditoria`
- [[compromissos.py]] — `ExclusaoCompromissoBloqueadaError`, `apagar_compromisso_por_id`, `apagar_compromissos_por_origem`, `atualizar_campo_compromisso`, `atualizar_valor_compromisso`, `atualizar_vencimento_compromisso`, `buscar_compromisso_por_id`, `buscar_transacoes_por_competencia` +7
- [[conciliacao.py]] — `buscar_checklist_status_mes`, `buscar_compromisso_por_id`, `buscar_transacao_por_id`, `buscar_transacoes_por_mes`, `fatura_write_transaction`, `get_connection`, `listar_auditoria`, `registrar_auditoria`
- [[consultas_pagar.py]] — `buscar_compromisso_por_id`, `listar_compromissos`, `read_only_mode`
- [[contas_inativas.py]] — `get_connection`, `registrar_auditoria`
- [[dashboard_metricas.py]] — `read_only_mode`
- [[efeito_baixa.py]] — `read_only_mode`
- [[fatura_conferencia.py]] — `fatura_write_transaction`, `get_connection`, `registrar_auditoria`
- [[fixos_edicao.py]] — `buscar_compromisso_por_id`, `get_connection`, `registrar_auditoria`
- [[fixos_interface.py]] — `listar_compromissos`
- [[fixos_variaveis_acoes.py]] — `buscar_compromisso_por_id`, `buscar_todas_transacoes`, `listar_auditoria`, `registrar_auditoria`
- [[saldos_edicao.py]] — `buscar_saldo_mensal`, `buscar_saldos_contas_mes`, `fatura_write_transaction`, `registrar_auditoria`
- [[services.py]] — `ExclusaoParcialParcelamentoError`, `apagar_checklist_data_pagamento`, `apagar_checklist_data_pagamento_padrao`, `apagar_fatura_movimento`, `apagar_meta_por_categoria`, `apagar_transacao_por_id`, `apagar_transacoes_por_ids`, `apagar_transacoes_por_intervalo_ids` +55
- [[sugestoes_lancamento.py]] — `get_connection`, `read_only_mode`
- [[telegram_alertas.py]] — `get_connection`, `read_only_mode`, `registrar_auditoria`
- [[telegram_experiencia.py]] — `buscar_checklist_status_mes`, `buscar_saldo_mensal`, `buscar_saldos_contas_mes`, `buscar_transacao_por_id`, `buscar_transacoes_por_competencia`, `buscar_transacoes_por_mes`, `buscar_transferencias_caixa_por_mes`, `buscar_ultimas_transacoes` +6
- [[telegram_midia.py]] — `inserir_transferencia_caixa`
- [[telegram_recursos.py]] — `read_only_mode`
- [[telegram_registros.py]] — `fatura_write_transaction`, `get_connection`, `inserir_fatura_movimento_conn`, `registrar_auditoria`
- [[tools__medir_desempenho.py|tools/medir_desempenho.py]] — `init_db`, `inserir_compromisso`, `inserir_parcelamento_atomico`, `inserir_transacao`
- [[tools__medir_rotina.py|tools/medir_rotina.py]] — `listar_compromissos`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `registrar_auditoria` | 1864 | 13 | 1 | Registra alteração financeira sem armazenar objetos não serializáveis. |
| `get_connection` | 218 | 10 | 40 |  |
| `read_only_mode` | 158 | 10 | 5 | Restringe e compartilha uma conexão de leitura nesta requisição. |
| `buscar_compromisso_por_id` | 1510 | 6 | 8 |  |
| `listar_compromissos` | 1492 | 6 | 5 |  |
| `fatura_write_transaction` | 228 | 5 | 2 | Serializa alterações de fatura entre processos usando BEGIN IMMEDIATE. |
| `buscar_transacoes_por_mes` | 940 | 4 | 7 |  |
| `buscar_transacao_por_id` | 1131 | 4 | 6 |  |
| `inserir_compromisso` | 1446 | 3 | 45 |  |
| `listar_auditoria` | 1892 | 3 | 5 |  |
| `buscar_checklist_status_mes` | 1908 | 3 | 3 |  |
| `buscar_saldo_mensal` | 503 | 3 | 2 |  |
| `buscar_saldos_contas_mes` | 564 | 3 | 2 |  |
| `listar_metas` | 1410 | 3 | 2 |  |
| `buscar_transacoes_por_competencia` | 951 | 3 | 1 | Mes financeiro; credito usa a fatura, demais registros usam sua data. |
| `buscar_todas_transacoes` | 962 | 3 | 0 |  |
| `init_db` | 332 | 2 | 81 |  |
| `inserir_transacao` | 829 | 2 | 55 |  |
| `definir_meta` | 1374 | 2 | 7 |  |
| `inserir_transferencia_caixa` | 632 | 2 | 6 |  |
| `inserir_parcelamento_atomico` | 836 | 2 | 4 | Grava todas as parcelas e o vínculo do parcelamento numa única transação. |
| `listar_fatura_movimentos` | 1802 | 2 | 4 |  |
| `buscar_ultimas_transacoes` | 929 | 2 | 1 |  |
| `buscar_transferencias_caixa_por_mes` | 664 | 2 | 0 |  |
| `inserir_fatura_movimento_conn` | 242 | 2 | 0 |  |

## Tudo que define

91 definições; as 40 maiores:

- `init_db` (L332, 169 linhas)
- `_inserir_transacao_conn` (L863, 48 linhas) — INSERT de uma transação na conexão recebida; o commit fica com quem chama.
- `atualizar_valor_por_id` (L1327, 45 linhas)
- `_normalizar_categorias_legadas` (L286, 44 linhas) — Consolida aliases conhecidos sem alterar valores financeiros.
- `inserir_compromisso` (L1446, 44 linhas)
- `atualizar_campo_compromisso` (L1558, 44 linhas)
- `definir_saldo_inicial_conta_mes` (L586, 43 linhas)
- `definir_checklist_data_pagamento` (L761, 42 linhas)
- `bloqueio_exclusao_fixo_serie_conn` (L1639, 42 linhas) — Mensagem de recusa ao apagar uma versão de fixo (série de 'nova condição')
- `definir_saldo_inicial_mes` (L513, 39 linhas)
- `definir_checklist_data_pagamento_padrao` (L698, 39 linhas)
- `verificar_banco_para_iniciar` (L178, 38 linhas) — Recusa iniciar o bot em situações que dividiriam ou corromperiam os dados.
- `definir_meta` (L1374, 34 linhas)
- `marcar_checklist_pagamento` (L1920, 34 linhas)
- `apagar_compromisso_por_id` (L1683, 32 linhas)
- `inserir_transferencia_caixa` (L632, 30 linhas)
- `substituir_compromissos_por_origem` (L1735, 29 linhas) — Substitui uma importação inteira de forma atômica.
- `_open_connection` (L127, 28 linhas)
- `_validar_valor_monetario` (L20, 27 linhas) — Valida valor monetário na camada de banco e devolve float com 2 casas.
- `atualizar_forma_por_id` (L1298, 27 linhas)
- `apagar_transacoes_por_ids` (L1169, 26 linhas) — Apaga um conjunto de transações de forma atômica (tudo ou nada).
- `definir_status_compromisso` (L1604, 26 linhas)
- `registrar_auditoria` (L1864, 26 linhas) — Registra alteração financeira sem armazenar objetos não serializáveis.
- `inserir_parcelamento_atomico` (L836, 25 linhas) — Grava todas as parcelas e o vínculo do parcelamento numa única transação.
- `parcelamentos_incompletos_conn` (L976, 25 linhas) — Parcelamentos (parcelamento_id) dos quais o conjunto alvo leva só PARTE.
- `apagar_transacoes_por_intervalo_ids` (L1197, 25 linhas)
- `atualizar_fatura_movimento` (L1826, 25 linhas)
- classe `ClosingConnection` (L57, 23 linhas) — SQLite connection whose context manager also releases the file handle.
- `atualizar_conta_por_id` (L1273, 23 linhas)
- `mensagem_exclusao_parcial_parcelamento` (L1003, 21 linhas)
- `atualizar_valor_compromisso` (L1516, 21 linhas)
- `apagar_ultima_transacao` (L1032, 20 linhas)
- `resumo_mes` (L1054, 20 linhas)
- `read_only_mode` (L158, 18 linhas) — Restringe e compartilha uma conexão de leitura nesta requisição.
- `inserir_fatura_movimento_conn` (L242, 17 linhas)
- `apagar_meta_por_categoria` (L1427, 17 linhas)
- `atualizar_vencimento_compromisso` (L1539, 17 linhas)
- `_validar_fatura_movimento` (L1775, 17 linhas)
- `atualizar_categoria_ultima_transacao` (L1113, 16 linhas)
- `apagar_transacao_por_id` (L1151, 16 linhas)

## Testes que usam (87)

- `tests/__init__.py`
- `tests/conftest.py`
- `tests/helpers_rc155.py`
- `tests/test_ajustar_saldo_seletor.py`
- `tests/test_alertas_fase1.py`
- `tests/test_auditoria_resultado_mes_rc152.py`
- `tests/test_backup_externo.py`
- `tests/test_baixa_fixo_conta.py`
- `tests/test_bloco_a_protecao_dados.py`
- `tests/test_bloco_b_complementos.py`
- `tests/test_bloco_b_datas_comandos.py`
- `tests/test_bloco_b_fatura_telas.py`
- `tests/test_bloco_b_saldos_pagamentos.py`
- `tests/test_bloco_c_auditoria.py`
- `tests/test_bloco_c_ciclo_vida.py`
- `tests/test_bloco_d_usabilidade.py`
- `tests/test_botoes_confirmacao.py`
- `tests/test_botoes_finais_regressao.py`
- `tests/test_busca_lancamentos.py`
- `tests/test_checklist_fatura_movimentos_rc151.py`
- … +67

## No mapa de rotas

- **Estado da sessão (2):** [[state_db_auditoria_eventos-e3dd2|db:auditoria_eventos]], [[state_db_transacoes-fbd85|db:transacoes]]
- **Funções no mapa (4):** [[fn_database.fatura_write_transaction-95ff7|database.fatura_write_transaction]], [[fn_database.inserir_fatura_movimento_conn-457bd|database.inserir_fatura_movimento_conn]], [[fn_database.inserir_transferencia_caixa-d62ec|database.inserir_transferencia_caixa]], [[fn_database.read_only_mode-0854f|database.read_only_mode]]
- **Chamadas de serviço (11):** [[fn_db.atualizar_categoria_em_lote-efa49|db.atualizar_categoria_em_lote]], [[fn_db.buscar_saldo_mensal-82b9a|db.buscar_saldo_mensal]], [[fn_db.buscar_saldos_contas_mes-d2278|db.buscar_saldos_contas_mes]], [[fn_db.buscar_transacao_por_id-d0e04|buscar_transacao_por_id]], [[fn_db.buscar_transacoes_por_competencia-4f076|buscar_transacoes_por_competencia]], [[fn_db.buscar_transacoes_por_mes-9d185|buscar_transacoes_por_mes]], [[fn_db.definir_meta-f8581|definir_meta]], [[fn_db.listar_compromissos-77786|listar_compromissos]], [[fn_db.listar_metas-42a00|listar_metas]], [[fn_db.read_only_mode-088bd|db.read_only_mode]], [[fn_db.registrar_auditoria-1ae3c|registrar_auditoria]]

## Documentos que citam

- [[reavaliacao/01_arquitetura]]
- [[reavaliacao/03_seguranca_privacidade]]
- [[reavaliacao/08_onda3_etapa1]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
