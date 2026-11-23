---
tipo: modulo
grupo: Núcleo financeiro
linhas: 2175
tags: [modulo, nucleo-financeiro]
---
# compromissos.py

**Grupo:** [[Núcleo financeiro]] · **Linhas:** 2175 · **Funções:** 96 · **Classes:** 0

> [!warning] Linha de base
> Limite de 2175 linhas (hoje 2175). Este arquivo não pode crescer: código novo vai em módulo próprio.

## Usa

- [[categorias.py]]
- [[conciliacao.py]] *(importação tardia, dentro de função)*
- [[config.py]]
- [[consulta_cache.py]]
- [[database.py]] *(importação tardia, dentro de função)*
- [[fatura_conferencia.py]] *(importação tardia, dentro de função)*
- [[faturas_competencia.py]]
- [[money.py]] *(importação tardia, dentro de função)*
- [[pagamentos_canonicos.py]]
- [[relogio.py]]

## Usado por

- [[conciliacao.py]] — `compromisso_ocorre_no_mes`, `projetar_compromissos_mes`, `projetar_entradas_programadas_mes`
- [[fatura_conferencia.py]] — `calcular_fatura_unificada`, `normalizar_conta_fatura`
- [[fixos_edicao.py]] — `normalizar_conta_pagamento_usuario`
- [[fixos_interface.py]] — `compromisso_ocorre_no_mes`
- [[reservas_faturas.py]] — `calcular_fatura_unificada`, `item_eh_fatura_cartao`, `normalizar_conta_fatura`
- [[services.py]] — `alterar_compromisso_categoria`, `alterar_compromisso_conta`, `alterar_compromisso_forma`, `alterar_entrada_valor`, `alterar_fixo_valor`, `alterar_fixo_vencimento`, `apagar_compromisso_formatado`, `apagar_entrada_formatado` +28
- [[telegram_experiencia.py]] — `calcular_resumo_pagamento_conta`, `detalhar_pagamento_por_conta`, `item_eh_fatura_cartao`, `obter_itens_base_pagamentos_mes`, `projetar_entradas_programadas_mes`
- [[telegram_registros.py]] — `normalizar_conta_fatura`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `normalizar_conta_fatura` | 617 | 4 | 1 |  |
| `calcular_fatura_unificada` | 913 | 3 | 14 | Consolida a fatura sem duplicar o mesmo item previsto e realizado. |
| `item_eh_fatura_cartao` | 654 | 3 | 2 | Classifica faturas sem depender apenas de uma whitelist fechada. |
| `compromisso_ocorre_no_mes` | 514 | 3 | 1 |  |
| `detalhar_pagamento_por_conta` | 1677 | 2 | 2 | Detalha exatamente os valores usados no resumo de pagamento da conta. |
| `projetar_entradas_programadas_mes` | 1159 | 2 | 0 |  |
| `calcular_resumo_pagamento_conta` | 1575 | 1 | 5 | Calcula os componentes pendentes sem deixar crédito de cartão abater Pix/fixos. |
| `projetar_compromissos_mes` | 575 | 1 | 5 |  |
| `resumo_pagamento_por_conta` | 1761 | 1 | 4 | Retorna um resumo objetivo do valor necessário por conta. |
| `resumo_pagamento_mes_consolidado` | 1795 | 1 | 3 | Consolida as obrigações pendentes do mês em todas as contas. |
| `alterar_compromisso_conta` | 2071 | 1 | 2 |  |
| `listar_fixos_formatado` | 1885 | 1 | 2 |  |
| `projetar_pagamentos_mes` | 1049 | 1 | 2 |  |
| `classificar_csv` | 355 | 1 | 1 |  |
| `item_eh_liquidacao_fatura` | 1059 | 1 | 1 | Pagamento de fatura projetado como item negativo (``fatura_movimento``). |
| `obter_itens_base_pagamentos_mes` | 798 | 1 | 1 |  |
| `remover_liquidacoes_fatura` | 1072 | 1 | 1 | Remove pagamentos de fatura de visões de gasto (categorias/fechamento). |
| `resumir_previa_importacao` | 437 | 1 | 1 |  |
| `alterar_compromisso_categoria` | 2126 | 1 | 0 |  |
| `alterar_compromisso_forma` | 2105 | 1 | 0 |  |
| `alterar_entrada_valor` | 1401 | 1 | 0 |  |
| `alterar_fixo_valor` | 1974 | 1 | 0 |  |
| `alterar_fixo_vencimento` | 1995 | 1 | 0 |  |
| `apagar_compromisso_formatado` | 2161 | 1 | 0 |  |
| `apagar_entrada_formatado` | 1442 | 1 | 0 |  |

## Tudo que define

96 definições; as 40 maiores:

- `calcular_resumo_pagamento_conta` (L1575, 101 linhas) — Calcula os componentes pendentes sem deixar crédito de cartão abater Pix/fixos.
- `calcular_fatura_unificada` (L913, 87 linhas) — Consolida a fatura sem duplicar o mesmo item previsto e realizado.
- `resumo_pagamento_mes_consolidado` (L1795, 84 linhas) — Consolida as obrigações pendentes do mês em todas as contas.
- `detalhar_pagamento_por_conta` (L1677, 82 linhas) — Detalha exatamente os valores usados no resumo de pagamento da conta.
- `classificar_csv` (L355, 80 linhas)
- `item_eh_fatura_cartao` (L654, 71 linhas) — Classifica faturas sem depender apenas de uma whitelist fechada.
- `criar_fixo_manual` (L1458, 61 linhas)
- `listar_fixos_formatado` (L1885, 60 linhas)
- `resumir_previa_importacao` (L437, 53 linhas)
- `resumo_contas_mes_quebrado` (L1085, 47 linhas)
- `listar_entradas_mes_formatado` (L1354, 45 linhas)
- `_projetar_compromissos_mes` (L531, 42 linhas)
- `criar_entrada_fixa_manual` (L1203, 36 linhas)
- `listar_entradas_formatado` (L1316, 36 linhas)
- `projetar_entradas_programadas_mes` (L1159, 33 linhas)
- `classificar_natureza_pagamento` (L727, 32 linhas) — Retorna uma natureza visual sem alterar valor ou elegibilidade.
- `resumo_pagamento_por_conta` (L1761, 32 linhas) — Retorna um resumo objetivo do valor necessário por conta.
- `alterar_compromisso_conta` (L2071, 32 linhas)
- `aplicar_movimentos_fatura_na_projecao` (L1002, 29 linhas)
- `criar_entrada_avulsa_manual` (L1241, 29 linhas)
- `formatar_item_card` (L180, 26 linhas)
- `_incluir_transacoes_mes_na_projecao` (L582, 25 linhas)
- `listar_compromissos_formatado` (L1947, 25 linhas)
- `normalizar_conta_pagamento_usuario` (L2019, 25 linhas)
- `ler_csv_transacoes` (L311, 24 linhas)
- `_previsto_corresponde_realizado` (L835, 24 linhas) — Detecta apenas duplicidade do MESMO item, nunca do cartão inteiro.
- `incluir_receitas_mes_na_projecao` (L1134, 23 linhas)
- `cadastrar_entrada_avulsa_formatado` (L1291, 23 linhas)
- `normalizar_forma_pagamento_usuario` (L2046, 23 linhas)
- `alterar_fixo_vencimento` (L1995, 22 linhas)
- `total_movimentos_fatura` (L761, 20 linhas)
- `item_entra_no_quanto_vou_pagar` (L1552, 20 linhas) — Para "quanto vou pagar no banco/conta", considerar tudo o que ainda
- `_separar_fonte_cartao` (L861, 19 linhas) — Mantém previsões independentes e remove somente duplicidades reais.
- `alterar_entrada_valor` (L1401, 19 linhas)
- `cadastrar_fixo_manual_formatado` (L1521, 19 linhas)
- `alterar_fixo_valor` (L1974, 19 linhas)
- `alterar_compromisso_forma` (L2105, 19 linhas)
- `alterar_compromisso_categoria` (L2126, 19 linhas)
- `_itens_base_da_conta` (L893, 18 linhas) — Itens-base do mes que pertencem a ``conta_norm``, ja copiados.
- `cadastrar_entrada_fixa_formatado` (L1272, 17 linhas)

## Testes que usam (37)

- `test_rc307_deduplicacao.py`
- `tests/test_bloco_b_complementos.py`
- `tests/test_bloco_b_fatura_telas.py`
- `tests/test_bloco_b_saldos_pagamentos.py`
- `tests/test_bloco_c_ciclo_vida.py`
- `tests/test_categorizacao_unificada.py`
- `tests/test_checklist_compatibilidade_legada.py`
- `tests/test_classificacao_natureza_pagamento.py`
- `tests/test_compromissos_correcoes_p0.py`
- `tests/test_confiabilidade_bloco2.py`
- `tests/test_config_unica.py`
- `tests/test_conta_forma_separadas.py`
- `tests/test_contas_gerenciar.py`
- `tests/test_desempenho_compromissos_deepcopy.py`
- `tests/test_detalhar_quanto_vou_pagar.py`
- `tests/test_equivalencia_calculos_onda2.py`
- `tests/test_experiencia_identidade_onda2c.py`
- `tests/test_fatura_conferencia.py`
- `tests/test_fixo_variavel.py`
- `tests/test_fixos_identidade_visual.py`
- … +17

## No mapa de rotas

- **Funções no mapa (30):** [[fn_compromissos.alterar_compromisso_categoria-42019|compromissos.alterar_compromisso_categoria]], [[fn_compromissos.alterar_compromisso_conta-64748|compromissos.alterar_compromisso_conta]], [[fn_compromissos.alterar_compromisso_forma-7411c|compromissos.alterar_compromisso_forma]], [[fn_compromissos.alterar_entrada_valor-4b01e|compromissos.alterar_entrada_valor]], [[fn_compromissos.alterar_fixo_valor-4eb0f|compromissos.alterar_fixo_valor]], [[fn_compromissos.alterar_fixo_vencimento-063d8|compromissos.alterar_fixo_vencimento]], [[fn_compromissos.apagar_compromisso_formatado-7fb15|compromissos.apagar_compromisso_formatado]], [[fn_compromissos.apagar_entrada_formatado-398b1|compromissos.apagar_entrada_formatado]], [[fn_compromissos.cadastrar_entrada_avulsa_formatado-87f07|compromissos.cadastrar_entrada_avulsa_formatado]], [[fn_compromissos.cadastrar_entrada_fixa_formatado-c714f|compromissos.cadastrar_entrada_fixa_formatado]], [[fn_compromissos.cadastrar_fixo_manual_formatado-4c26d|compromissos.cadastrar_fixo_manual_formatado]], [[fn_compromissos.calcular_fatura_unificada-1dca9|compromissos.calcular_fatura_unificada]], [[fn_compromissos.calcular_resumo_pagamento_conta-dc584|compromissos.calcular_resumo_pagamento_conta]], [[fn_compromissos.compromisso_ocorre_no_mes-30a12|compromissos.compromisso_ocorre_no_mes]], [[fn_compromissos.detalhar_pagamento_por_conta-62748|compromissos.detalhar_pagamento_por_conta]], [[fn_compromissos.item_eh_liquidacao_fatura-47d1e|compromissos.item_eh_liquidacao_fatura]], [[fn_compromissos.item_entra_no_quanto_vou_pagar-0abd6|compromissos.item_entra_no_quanto_vou_pagar]], [[fn_compromissos.listar_compromissos_formatado-0e2fc|compromissos.listar_compromissos_formatado]], [[fn_compromissos.listar_entradas_formatado-5dd53|compromissos.listar_entradas_formatado]], [[fn_compromissos.listar_entradas_mes_formatado-d2180|compromissos.listar_entradas_mes_formatado]], [[fn_compromissos.listar_fixos_formatado-cef5c|compromissos.listar_fixos_formatado]], [[fn_compromissos.obter_itens_base_pagamentos_mes-4d0ba|compromissos.obter_itens_base_pagamentos_mes]], [[fn_compromissos.pausar_compromisso-34770|compromissos.pausar_compromisso]], [[fn_compromissos.pausar_entrada-3a606|compromissos.pausar_entrada]], [[fn_compromissos.projetar_pagamentos_mes-74d69|compromissos.projetar_pagamentos_mes]], [[fn_compromissos.reativar_compromisso-38042|compromissos.reativar_compromisso]], [[fn_compromissos.reativar_entrada-5bcce|compromissos.reativar_entrada]], [[fn_compromissos.resumo_contas_mes-7e95c|compromissos.resumo_contas_mes]], [[fn_compromissos.resumo_pagamento_mes_consolidado-9efcf|compromissos.resumo_pagamento_mes_consolidado]], [[fn_compromissos.resumo_pagamento_por_conta-04e09|compromissos.resumo_pagamento_por_conta]]
- **Chamadas de serviço (2):** [[fn_compromissos.item_eh_fatura_cartao-05eac|compromissos.item_eh_fatura_cartao]], [[fn_compromissos.projetar_entradas_programadas_mes-f92d7|projetar_entradas_programadas_mes]]

## Documentos que citam

- [[reavaliacao/00_veredito]]
- [[reavaliacao/01_arquitetura]]
- [[reavaliacao/03_seguranca_privacidade]]
- [[reavaliacao/08_onda3_etapa1]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
