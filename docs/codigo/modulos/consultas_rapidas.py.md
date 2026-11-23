---
tipo: modulo
grupo: Telegram (telas e conversa)
linhas: 228
tags: [modulo, telegram-telas-e-conversa]
---
# consultas_rapidas.py

> Consultas comuns sem rede; apenas intenção, nunca cálculo ou gravação.

**Grupo:** [[Telegram (telas e conversa)]] · **Linhas:** 228 · **Funções:** 11 · **Classes:** 0

## Usa

- (nenhum módulo do projeto)

## Usado por

- [[busca_lancamentos.py]] — `_extrair_periodo`, `resolver_meses`, `rotulo_periodo`
- [[telegram_experiencia.py]] — `interpretar_consulta`, `linhas_por_mes`, `resolver_meses`, `rotulo_periodo`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `resolver_meses` | 203 | 2 | 2 | Meses AAAA-MM de um período próprio desta camada; ``None`` se o período for inválido. |
| `rotulo_periodo` | 183 | 2 | 0 | 'Julho 2026' ou 'Julho 2026 a Novembro 2026 (até 13/11/2026)' quando o intervalo inclui o mês atual. |
| `interpretar_consulta` | 127 | 1 | 2 |  |
| `_extrair_periodo` | 50 | 1 | 0 | Acha UMA expressão de período, remove-a do texto e devolve (texto, período). |
| `linhas_por_mes` | 192 | 1 | 0 | Intervalo: total de cada mês já começado (itens marcados com '_mes'); um mês só: nada. |

## Tudo que define

- `_normalizar` (L36, 3 linhas)
- `_ler_token` (L41, 7 linhas) — 'julho' -> (7, None); 'julho de 2025' -> (7, 2025); '2026-07' -> (7, 2026).
- `_extrair_periodo` (L50, 38 linhas) — Acha UMA expressão de período, remove-a do texto e devolve (texto, período).
- `_sobrou_periodo` (L90, 4 linhas) — Segunda referência de tempo no texto: ambígua, fica para a IA/fallback.
- `interpretar_pagar` (L100, 25 linhas) — 'quanto vou pagar de moradia em dezembro' -> previsão a pagar por categoria (ou faturas).
- `interpretar_consulta` (L127, 33 linhas)
- `_somar_meses` (L162, 3 linhas)
- `_lista` (L167, 9 linhas)
- `rotulo_periodo` (L183, 7 linhas) — 'Julho 2026' ou 'Julho 2026 a Novembro 2026 (até 13/11/2026)' quando o intervalo inclui o mês atual.
- `linhas_por_mes` (L192, 9 linhas) — Intervalo: total de cada mês já começado (itens marcados com '_mes'); um mês só: nada.
- `resolver_meses` (L203, 26 linhas) — Meses AAAA-MM de um período próprio desta camada; ``None`` se o período for inválido.

## Testes que usam (2)

- `tests/test_consultas_periodo.py`
- `tests/test_pagar_categoria.py`

## No mapa de rotas

- **Módulo (1):** [[mod_consultas_rapidas.py-7e976|consultas_rapidas.py]]
- **Funções no mapa (1):** [[fn_consultas_rapidas.interpretar_consulta-9e67b|consultas_rapidas.interpretar_consulta]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
