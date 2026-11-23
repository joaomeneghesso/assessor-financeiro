---
tipo: modulo
grupo: Telegram (telas e conversa)
linhas: 148
tags: [modulo, telegram-telas-e-conversa]
---
# dashboard_metricas.py

> Indicadores descritivos do dashboard; leitura, sem alterar o motor financeiro.

**Grupo:** [[Telegram (telas e conversa)]] · **Linhas:** 148 · **Funções:** 3 · **Classes:** 0

## Usa

- [[assessor_orientacao.py]] *(importação tardia, dentro de função)*
- [[database.py]]
- [[money.py]] *(importação tardia, dentro de função)*
- [[saldo_resumo.py]]
- [[services.py]]
- [[telegram_experiencia.py]] *(importação tardia, dentro de função)*

## Usado por

- [[telegram_experiencia.py]] — `enriquecer`, `variacao_categorias`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `variacao_categorias` | 15 | 1 | 1 | B4: variação de despesas POR CATEGORIA na mesma janela do mês anterior (mesmos dias, como enriquecer). |
| `enriquecer` | 60 | 1 | 0 | Valores de caixa seguem resumir_saldo; estatísticas usam registros por competência. |

## Tudo que define

- `registros` (L9, 5 linhas)
- `variacao_categorias` (L15, 44 linhas) — B4: variação de despesas POR CATEGORIA na mesma janela do mês anterior (mesmos dias, como enriquecer).
- `enriquecer` (L60, 89 linhas) — Valores de caixa seguem resumir_saldo; estatísticas usam registros por competência.

## Testes que usam (2)

- `tests/test_dashboard_metricas_412.py`
- `tests/test_limites_comprar_fase2.py`

## No mapa de rotas

- **Módulo (1):** [[mod_dashboard_metricas.py-87582|dashboard_metricas.py]]
- **Funções no mapa (2):** [[fn_dashboard_metricas.enriquecer-42163|dashboard_metricas.enriquecer]], [[fn_dashboard_metricas.registros-637cc|dashboard_metricas.registros]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
