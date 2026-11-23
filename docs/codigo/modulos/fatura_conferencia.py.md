---
tipo: modulo
grupo: Núcleo financeiro
linhas: 114
tags: [modulo, nucleo-financeiro]
---
# fatura_conferencia.py

> Conferência explícita com o banco; diferença de composição não é estorno.

**Grupo:** [[Núcleo financeiro]] · **Linhas:** 114 · **Funções:** 7 · **Classes:** 0

## Usa

- [[compromissos.py]] *(importação tardia, dentro de função)*
- [[consulta_cache.py]]
- [[database.py]]
- [[money.py]]
- [[relogio.py]]
- [[services.py]] *(importação tardia, dentro de função)*

## Usado por

- [[compromissos.py]] — `ajustes_mes`, `item_projecao`, `obter`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `obter` | 20 | 1 | 1 |  |
| `ajustes_mes` | 45 | 1 | 0 |  |
| `item_projecao` | 51 | 1 | 0 |  |
| `confirmar` | 58 | 0 | 2 | Corrige UM pagamento já realizado e confere a composição da mesma fatura. |

## Tudo que define

- `chave` (L15, 4 linhas)
- `obter` (L20, 8 linhas)
- `_obter_sem_conexao` (L30, 3 linhas)
- `_ajustes_mes` (L35, 8 linhas)
- `ajustes_mes` (L45, 5 linhas)
- `item_projecao` (L51, 6 linhas)
- `confirmar` (L58, 57 linhas) — Corrige UM pagamento já realizado e confere a composição da mesma fatura.

## Testes que usam (2)

- `tests/test_fatura_conferencia.py`
- `tests/test_infinitepay_credito_artificial.py`

## Documentos que citam

- [[reavaliacao/01_arquitetura]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
