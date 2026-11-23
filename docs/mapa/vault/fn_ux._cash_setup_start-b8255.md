---
tipo: handler
arquivo: telegram_experiencia.py
linha: 4237
---
# _cash_setup_start

Ajuste de saldos: força Session.month = mês corrente (l.3363).

`fn:ux._cash_setup_start`

## Vai para
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.3363 mês corrente
- (chama) [[fn_ux._cash_setup_accounts-636f3|ux._cash_setup_accounts]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (grava_estado) [[state_Session.settings_draft-703dd|Session.settings_draft]] 
- (chama) [[act_cash_setup_new_account-43b33|cash_setup_new_account]] 
- (chama) [[fn_services.calcular_caixa_por_conta_mes-3f8f8|services.calcular_caixa_por_conta_mes]] 
- (chama) [[act_cash_setup_account-7864b|cash_setup_account]] 
- (chama) [[act_cash_setup_pick-8c6e7|cash_setup_pick]] 
- (chama) [[act_cash_setup_all-33a5e|cash_setup_all]] 
- (chama) [[act_cash_accounts-a48cb|cash_accounts]] 
- (chama) [[act_view-1d8b8|view]] 

## Vem de
- (chama) [[act_cash_setup_start-c6f73|cash_setup_start]] 
- (chama) [[act_cash_setup_pick-8c6e7|cash_setup_pick]] 
