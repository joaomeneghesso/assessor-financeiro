---
tipo: modulo
grupo: Camada de negócio e interpretação
linhas: 144
tags: [modulo, camada-de-negocio-e-interpretacao]
---
# consulta_cache.py

> Cache efêmero compartilhado por uma única consulta/renderização.

**Grupo:** [[Camada de negócio e interpretação]] · **Linhas:** 144 · **Funções:** 8 · **Classes:** 0

## Usa

- (nenhum módulo do projeto)

## Usado por

- [[compromissos.py]] — `cache_atual`, `chave_no_escopo`, `copia_defensiva`, `copia_rapida`, `namespace`, `obter_ou_calcular`
- [[conciliacao.py]] — `escopo`, `obter_ou_calcular`
- [[consultas_pagar.py]] — `contexto_consulta`
- [[efeito_baixa.py]] — `contexto_consulta`
- [[fatura_conferencia.py]] — `obter_ou_calcular`
- [[fixos_variaveis_acoes.py]] — `cache_atual`
- [[services.py]] — `chave_no_escopo`, `contexto_consulta`, `namespace`, `obter_ou_calcular`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `obter_ou_calcular` | 128 | 4 | 2 | Obtém uma leitura do cache e sempre devolve uma cópia defensiva. |
| `contexto_consulta` | 18 | 3 | 3 |  |
| `cache_atual` | 31 | 2 | 1 |  |
| `namespace` | 139 | 2 | 1 | Retorna um espaço mutável privado para memos internos de um algoritmo. |
| `chave_no_escopo` | 123 | 2 | 0 |  |
| `escopo` | 115 | 1 | 1 |  |
| `copia_defensiva` | 40 | 1 | 0 | Copia estruturas de leitura, normalizando ``sqlite3.Row`` para dict. |
| `copia_rapida` | 67 | 1 | 0 | Equivale a ``deepcopy`` para estruturas de leitura (dict/list/tuple/set). |

## Tudo que define

- `contexto_consulta` (L18, 11 linhas)
- `cache_atual` (L31, 2 linhas)
- `copia_defensiva` (L40, 21 linhas) — Copia estruturas de leitura, normalizando ``sqlite3.Row`` para dict.
- `copia_rapida` (L67, 38 linhas) — Equivale a ``deepcopy`` para estruturas de leitura (dict/list/tuple/set).
- `escopo` (L115, 6 linhas)
- `chave_no_escopo` (L123, 3 linhas)
- `obter_ou_calcular` (L128, 9 linhas) — Obtém uma leitura do cache e sempre devolve uma cópia defensiva.
- `namespace` (L139, 6 linhas) — Retorna um espaço mutável privado para memos internos de um algoritmo.

## Testes que usam (4)

- `tests/test_desempenho_compromissos_deepcopy.py`
- `tests/test_desempenho_heranca_onda2.py`
- `tests/test_equivalencia_calculos_onda2.py`
- `tests/test_performance_cache_fase1.py`

## No mapa de rotas

- **Módulo (1):** [[mod_consulta_cache.py-c7d10|consulta_cache.py]]
- **Estado da sessão (1):** [[state_CONTEXTO_CONSULTA-83d77|CONTEXTO_CONSULTA]]
- **Funções no mapa (2):** [[fn_consulta_cache.contexto_consulta-9f519|consulta_cache.contexto_consulta]], [[fn_consulta_cache.obter_ou_calcular-f179b|consulta_cache.obter_ou_calcular]]

## Documentos que citam

- [[reavaliacao/01_arquitetura]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
