---
tipo: modulo
grupo: Núcleo financeiro
linhas: 101
tags: [modulo, nucleo-financeiro]
---
# pagamentos_canonicos.py

> Leitura canônica, pura e não inferencial dos dados de pagamento.

**Grupo:** [[Núcleo financeiro]] · **Linhas:** 101 · **Funções:** 6 · **Classes:** 0

## Usa

- (nenhum módulo do projeto)

## Usado por

- [[compromissos.py]] — `obter_conta_pagamento_efetiva`, `obter_destino_pagamento_efetivo`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `obter_conta_pagamento_efetiva` | 91 | 1 | 1 | Retorna a conta real canônica, com fallback compatível ao legado. |
| `obter_destino_pagamento_efetivo` | 99 | 1 | 0 | Retorna o destino canônico sem usar a conta legada como inferência. |
| `comparar_dados_pagamento_em_sombra` | 74 | 0 | 1 | Compara a visão canônica com o legado sem substituir nenhuma delas. |
| `obter_dados_pagamento_canonicos` | 36 | 0 | 1 | Retorna uma visão padronizada sem modificar ou inferir a entrada. |

## Tudo que define

- `_ler_campo` (L20, 7 linhas)
- `_texto_opcional` (L29, 5 linhas)
- `obter_dados_pagamento_canonicos` (L36, 36 linhas) — Retorna uma visão padronizada sem modificar ou inferir a entrada.
- `comparar_dados_pagamento_em_sombra` (L74, 15 linhas) — Compara a visão canônica com o legado sem substituir nenhuma delas.
- `obter_conta_pagamento_efetiva` (L91, 6 linhas) — Retorna a conta real canônica, com fallback compatível ao legado.
- `obter_destino_pagamento_efetivo` (L99, 3 linhas) — Retorna o destino canônico sem usar a conta legada como inferência.

## Testes que usam (2)

- `tests/test_rc155_pagamentos_canonicos.py`
- `tests/test_rc156_normalizacao_pagamentos.py`

## Documentos que citam

- [[reavaliacao/01_arquitetura]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
