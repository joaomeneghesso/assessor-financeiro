---
tipo: modulo
grupo: Núcleo financeiro
linhas: 57
tags: [modulo, nucleo-financeiro]
---
# money.py

**Grupo:** [[Núcleo financeiro]] · **Linhas:** 57 · **Funções:** 3 · **Classes:** 0

## Usa

- (nenhum módulo do projeto)

## Usado por

- [[assessor_orientacao.py]] — `parse_money`
- [[compromissos.py]] — `formatar_brl`, `parse_money_float`
- [[conciliacao.py]] — `parse_money`
- [[dashboard_metricas.py]] — `parse_money`
- [[database.py]] — `parse_money`
- [[fatura_conferencia.py]] — `parse_money`
- [[fixos_edicao.py]] — `formatar_brl`, `parse_money`
- [[parser_financeiro.py]] — `parse_money`, `parse_money_float`
- [[registro_conversa.py]] — `parse_money`
- [[saldos_edicao.py]] — `parse_money`
- [[services.py]] — `formatar_brl`, `parse_money`, `parse_money_float`
- [[telegram_experiencia.py]] — `parse_money`
- [[telegram_midia.py]] — `parse_money`
- [[telegram_registros.py]] — `parse_money`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `parse_money` | 7 | 13 | 1 | Aceita decimal simples e agrupamento pt-BR, sem corrigir separadores por conta própria. |
| `formatar_brl` | 41 | 3 | 1 | Regra única de exibição: 2 casas HALF_UP em Decimal, sem "R$ -0,00". |
| `parse_money_float` | 37 | 3 | 1 |  |

## Tudo que define

- `parse_money` (L7, 28 linhas) — Aceita decimal simples e agrupamento pt-BR, sem corrigir separadores por conta própria.
- `parse_money_float` (L37, 2 linhas)
- `formatar_brl` (L41, 17 linhas) — Regra única de exibição: 2 casas HALF_UP em Decimal, sem "R$ -0,00".

## Testes que usam (3)

- `tests/test_formatador_moeda_unico.py`
- `tests/test_mutantes_rede_seguranca.py`
- `tests/test_phase2_foundation.py`

## Documentos que citam

- [[reavaliacao/01_arquitetura]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
