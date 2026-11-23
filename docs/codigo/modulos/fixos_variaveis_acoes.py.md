---
tipo: modulo
grupo: Núcleo financeiro
linhas: 71
tags: [modulo, nucleo-financeiro]
---
# fixos_variaveis_acoes.py

> Ativar/desligar "valor variável" num fixo e sugerir o histórico (camada de ações).

**Grupo:** [[Núcleo financeiro]] · **Linhas:** 71 · **Funções:** 8 · **Classes:** 0

## Usa

- [[conciliacao.py]]
- [[consulta_cache.py]] *(importação tardia, dentro de função)*
- [[database.py]]
- [[fixos_variaveis.py]]

## Usado por

- [[fixos_interface.py]] — `assinatura`, `ativar`, `candidatos`, `desativar`, `eh_variavel`, `estado`, `previsao`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `ativar` | 39 | 1 | 1 |  |
| `candidatos` | 30 | 1 | 1 |  |
| `eh_variavel` | 21 | 1 | 1 |  |
| `assinatura` | 34 | 1 | 0 |  |
| `desativar` | 53 | 1 | 0 |  |
| `estado` | 25 | 1 | 0 |  |
| `previsao` | 62 | 1 | 0 | (valor, meses) da estimativa para ``mes``; ``historico`` (lançamentos) simula antes de gravar. |

## Tudo que define

- `_limpar_cache_da_consulta` (L14, 5 linhas)
- `eh_variavel` (L21, 2 linhas)
- `estado` (L25, 3 linhas)
- `candidatos` (L30, 2 linhas)
- `assinatura` (L34, 3 linhas)
- `ativar` (L39, 12 linhas)
- `desativar` (L53, 7 linhas)
- `previsao` (L62, 10 linhas) — (valor, meses) da estimativa para ``mes``; ``historico`` (lançamentos) simula antes de gravar.

## Testes que usam (2)

- `tests/test_fixo_variavel.py`
- `tests/test_pagar_categoria.py`

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
