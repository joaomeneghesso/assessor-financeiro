---
tipo: modulo
grupo: Camada de negócio e interpretação
linhas: 205
tags: [modulo, camada-de-negocio-e-interpretacao]
---
# assessor_ia_local.py

> Interpretação financeira local via Ollama.

**Grupo:** [[Camada de negócio e interpretação]] · **Linhas:** 205 · **Funções:** 10 · **Classes:** 1

## Usa

- [[config.py]]

## Usado por

- [[telegram_experiencia.py]] — `LocalUnavailable`, `interpretar`, `interpretar_contexto`, `modelo_local`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `LocalUnavailable` | 25 | 1 | 1 |  |
| `modelo_local` | 88 | 1 | 1 |  |
| `interpretar` | 203 | 1 | 0 | Compatibilidade: devolve apenas a rota antiga. |
| `interpretar_contexto` | 122 | 1 | 0 | Retorna intenção + entidades sem executar ações financeiras. |
| `_request` | 62 | 0 | 1 |  |
| `reset_runtime_state_for_tests` | 111 | 0 | 1 |  |

## Tudo que define

- classe `LocalUnavailable` (L25, 2 linhas)
- `_number_env` (L35, 4 linhas)
- `_circuit_check` (L41, 4 linhas)
- `_request_ok` (L47, 4 linhas)
- `_request_failed` (L53, 7 linhas)
- `_request` (L62, 24 linhas)
- `modelo_local` (L88, 21 linhas)
- `reset_runtime_state_for_tests` (L111, 4 linhas)
- `_clean_text` (L117, 3 linhas)
- `interpretar_contexto` (L122, 79 linhas) — Retorna intenção + entidades sem executar ações financeiras.
- `interpretar` (L203, 3 linhas) — Compatibilidade: devolve apenas a rota antiga.

## Testes que usam (2)

- `tests/test_consultas_periodo.py`
- `tests/test_performance_ia_streaming_fase4.py`

## No mapa de rotas

- **Chamadas de serviço (3):** [[fn_assessor_ia_local.interpretar-f2af7|interpretar]], [[fn_assessor_ia_local.interpretar_contexto-e0413|interpretar_contexto]], [[fn_assessor_ia_local.modelo_local-fb164|modelo_local]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
