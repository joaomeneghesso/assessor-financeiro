---
tipo: handler
arquivo: telegram_experiencia.py
linha: 4132
---
# _cash_accounts_screen

Saldos por conta (mês arbitrário). Grava Session.month=month (l.3268).

`fn:ux._cash_accounts_screen`

## Vai para
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.3268
- (chama) [[fn_services.calcular_caixa_por_conta_mes-3f8f8|services.calcular_caixa_por_conta_mes]] 
- (grava_estado) [[state_Session.cash_page-7ddbf|Session.cash_page]] 
- (chama) [[act_cash_account_detail-c0e6b|cash_account_detail]] 
- (chama) [[act_cash_accounts-a48cb|cash_accounts]] 
- (chama) [[act_cash_setup_start-c6f73|cash_setup_start]] 
- (chama) [[act_cash_setup_new_account-43b33|cash_setup_new_account]] 
- (chama) [[act_view-1d8b8|view]] 

## Vem de
- (chama) [[act_cash_accounts-a48cb|cash_accounts]] 
