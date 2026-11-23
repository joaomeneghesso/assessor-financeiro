---
tipo: button
arquivo: telegram_experiencia.py
linha: 
---
# ‹ Mês anterior

Setas de mês: ("month",-1,view), ("dashboard_month",-1,view), ("cash_accounts",prev,0), ("pay_month",prev,0), ("pay_account",acc,prev), ("balance_account",acc,prev), ("cash_account_detail",acc,prev), ("target_month",-1).

`btn:‹ Mês anterior`

## Vai para
- (chama) [[act_month-43f36|month]] 
- (chama) [[act_pay_month-b80f8|pay_month]] pay_month prev
- (grava_estado) [[state_Session.month-7f614|Session.month]] month_shift(-1)

## Vem de
- (navega) [[screen_month_actions-bedf6|month_actions]] ‹ Mês anterior
- (navega) [[screen_pay_month-39a6a|pay_month]] ‹ Mês anterior
- (navega) [[screen_period_tools-35de3|period_tools]] ‹ Mês anterior
- (navega) [[act_period_tools-9b2d7|period_tools]] 
