---
tipo: modulo
grupo: Núcleo financeiro
linhas: 165
tags: [modulo, nucleo-financeiro]
---
# fixos_edicao.py

> Edição de fixos: correção do cadastro ou nova condição mensal, com auditoria.

**Grupo:** [[Núcleo financeiro]] · **Linhas:** 165 · **Funções:** 11 · **Classes:** 0

## Usa

- [[categorias.py]]
- [[compromissos.py]] *(importação tardia, dentro de função)*
- [[conciliacao.py]] *(importação tardia, dentro de função)*
- [[database.py]]
- [[fixos_vigencia.py]]
- [[money.py]]
- [[relogio.py]]

## Usado por

- [[fixos_interface.py]] — `buscar`, `data_br`, `dinheiro`, `exibir`, `norm`, `preparar`, `salvar`, `validar`
- [[services.py]] — `exibir`, `parse`, `preparar`, `salvar`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `preparar` | 75 | 2 | 5 |  |
| `salvar` | 92 | 2 | 5 |  |
| `exibir` | 152 | 2 | 1 |  |
| `buscar` | 69 | 1 | 0 |  |
| `data_br` | 143 | 1 | 0 | '2026-06-01' -> '01/06/2026' (só exibição). |
| `dinheiro` | 149 | 1 | 0 |  |
| `norm` | 23 | 1 | 0 |  |
| `parse` | 159 | 1 | 0 |  |
| `validar` | 35 | 1 | 0 |  |
| `mes_extenso` | 137 | 0 | 1 | '2026-11' -> 'Novembro 2026' (só exibição). |

## Tudo que define

- `norm` (L23, 2 linhas)
- `data` (L26, 8 linhas)
- `validar` (L35, 33 linhas)
- `buscar` (L69, 5 linhas)
- `preparar` (L75, 16 linhas)
- `salvar` (L92, 42 linhas)
- `mes_extenso` (L137, 5 linhas) — '2026-11' -> 'Novembro 2026' (só exibição).
- `data_br` (L143, 5 linhas) — '2026-06-01' -> '01/06/2026' (só exibição).
- `dinheiro` (L149, 2 linhas)
- `exibir` (L152, 6 linhas)
- `parse` (L159, 7 linhas)

## Testes que usam (6)

- `tests/test_bloco_c_ciclo_vida.py`
- `tests/test_equivalencia_calculos_onda2.py`
- `tests/test_fixos_identidade_visual.py`
- `tests/test_fixos_vigencia_integridade.py`
- `tests/test_matriz_release_oficial.py`
- `tests/test_revisao_saldo_integridade.py`

## No mapa de rotas

- **Funções no mapa (3):** [[fn_fixos_edicao.parse-661bd|fixos_edicao.parse]], [[fn_fixos_edicao.preparar-e4d98|fixos_edicao.preparar]], [[fn_fixos_edicao.salvar-0f79e|fixos_edicao.salvar]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
