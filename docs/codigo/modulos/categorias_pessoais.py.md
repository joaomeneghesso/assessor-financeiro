---
tipo: modulo
grupo: Núcleo financeiro
linhas: 128
tags: [modulo, nucleo-financeiro]
---
# categorias_pessoais.py

> Regras pessoais e explícitas de categorização.

**Grupo:** [[Núcleo financeiro]] · **Linhas:** 128 · **Funções:** 8 · **Classes:** 0

## Usa

- [[config.py]]

## Usado por

- [[app.py]] — `salvar_regra`
- [[busca_lancamentos.py]] — `salvar_regra`
- [[categorias.py]] — `sugerir_categoria_pessoal`
- [[services.py]] — `listar_regras`
- [[telegram_experiencia.py]] — `listar_regras`, `remover_regra`, `salvar_regra`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `salvar_regra` | 82 | 3 | 1 |  |
| `listar_regras` | 52 | 2 | 2 |  |
| `sugerir_categoria_pessoal` | 117 | 1 | 2 |  |
| `remover_regra` | 106 | 1 | 1 |  |

## Tudo que define

- `_path` (L29, 3 linhas)
- `normalizar_expressao` (L34, 4 linhas)
- `_document` (L40, 10 linhas)
- `listar_regras` (L52, 13 linhas)
- `_write` (L67, 13 linhas)
- `salvar_regra` (L82, 22 linhas)
- `remover_regra` (L106, 9 linhas)
- `sugerir_categoria_pessoal` (L117, 12 linhas)

## Testes que usam (3)

- `tests/test_busca_lancamentos.py`
- `tests/test_confiabilidade_413.py`
- `tests/test_pos_salvar_fase2.py`

## No mapa de rotas

- **Chamadas de serviço (3):** [[fn_categorias_pessoais.listar_regras-ed6bb|listar_regras]], [[fn_categorias_pessoais.remover_regra-1eb50|remover_regra]], [[fn_categorias_pessoais.salvar_regra-8272c|categorias_pessoais.salvar_regra]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
