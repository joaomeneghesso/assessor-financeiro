---
tipo: action
arquivo: telegram_experiencia.py
linha: 2993
---
# cash_setup_account

Ajuste de saldo de uma conta.

`act:cash_setup_account`

## Vai para
- (chama) [[fn_ux._cash_setup_account-e2e3c|_cash_setup_account]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.3371 força mês corrente

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_cash_account_detail-b41d6|cash_account_detail]] ✏️ Ajustar saldo
- (navega) [[screen_balance_account-fac81|balance_account]] ✏️ Ajustar saldo
- (chama) [[fn_ux._cash_account_detail_screen-2f392|_cash_account_detail_screen]] 
- (chama) [[fn_ux._balance_account_screen-85ed8|_balance_account_screen]] 
- (chama) [[fn_ux._cash_setup_start-b8255|_cash_setup_start]] 
