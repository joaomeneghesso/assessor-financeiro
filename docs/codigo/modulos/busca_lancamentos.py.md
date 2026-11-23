---
tipo: modulo
grupo: Telegram (telas e conversa)
linhas: 251
tags: [modulo, telegram-telas-e-conversa]
---
# busca_lancamentos.py

> Busca de lançamentos em todos os meses e troca de categoria em lote (Telegram).

**Grupo:** [[Telegram (telas e conversa)]] · **Linhas:** 251 · **Funções:** 14 · **Classes:** 0

## Usa

- [[categorias.py]]
- [[categorias_pessoais.py]] *(importação tardia, dentro de função)*
- [[consultas_rapidas.py]]
- [[database.py]]
- [[services.py]]

## Usado por

- [[telegram_experiencia.py]] — `dispatch`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `dispatch` | 234 | 1 | 0 | Ponto único chamado por ``Experience`` (texto "buscar ..." e botões ``busca*``). |
| `interpretar_busca` | 33 | 0 | 1 | 'bruno nos últimos 3 meses' -> ('bruno', '2026-09:2026-11'); sem período -> ('bruno', ''). |

## Tudo que define

- `interpretar_busca` (L33, 21 linhas) — 'bruno nos últimos 3 meses' -> ('bruno', '2026-09:2026-11'); sem período -> ('bruno', '').
- `_meses_do_periodo` (L56, 5 linhas)
- `buscar` (L63, 9 linhas) — Lançamentos que contêm o termo (descrição, categoria, conta, valor...), do mais recente ao mais antigo.
- `candidatos_categoria` (L74, 13 linhas) — Despesas encontradas (parcelamentos sempre inteiros) que ainda não estão na nova categoria.
- `assinatura` (L89, 3 linhas)
- `categorias_disponiveis` (L94, 9 linhas)
- `_data_br` (L106, 3 linhas)
- `_rotulo` (L111, 9 linhas)
- `_tela_resultado` (L122, 42 linhas)
- `_tela_escolher_categoria` (L166, 7 linhas)
- `_tela_previa` (L175, 19 linhas)
- `_gravar` (L196, 18 linhas)
- `_aprender` (L216, 16 linhas)
- `dispatch` (L234, 18 linhas) — Ponto único chamado por ``Experience`` (texto "buscar ..." e botões ``busca*``).

## Testes que usam (1)

- `tests/test_busca_lancamentos.py`

## No mapa de rotas

- **Funções no mapa (1):** [[fn_busca_lancamentos.dispatch-39750|busca_lancamentos.dispatch]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
