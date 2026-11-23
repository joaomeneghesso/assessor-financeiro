---
tipo: action
arquivo: telegram_experiencia.py
linha: 2846
---
# dashboard_month

Mês anterior/próximo do dashboard: Session.month±1 e re-executa chart.

`act:dashboard_month`

## Vai para
- (chama) [[act_chart-efa97|chart]] após s.month±1
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.2363 month_shift(s.month)

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_dashboard-6ba51|dashboard]] ‹ Mês anterior
- (navega) [[act_chart-efa97|chart]] botão da resposta
