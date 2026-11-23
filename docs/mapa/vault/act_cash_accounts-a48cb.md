---
tipo: action
arquivo: telegram_experiencia.py
linha: 2984
---
# cash_accounts

Saldos por conta (mês opcional).

`act:cash_accounts`

## Vai para
- (chama) [[fn_ux._cash_accounts_screen-0bdea|_cash_accounts_screen]] 
- (navega) [[screen_cash_accounts-cc984|cash_accounts]] 
- (le_estado) [[state_Session.month-7f614|Session.month]] 

## Vem de
- (chama) [[cmd_atalhos_abrir_atalho_ux-b0368|/pagar /historico /saldos /fechamento /atencao /recursos]] 
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_balance-64c54|balance]] 🏦 Por conta
- (navega) [[screen_resources-d1f70|resources]] 🏦 Contas e saldos
- (navega) [[screen_data_tools-d1767|data_tools]] 🏦 Contas e saldos
- (navega) [[screen_lesson-90d28|lesson]] 🧭 Abrir ferramenta
- (navega) [[screen_cash_accounts-cc984|cash_accounts]] ‹ Contas / Mais contas ›
- (navega) [[screen_cash_account_detail-b41d6|cash_account_detail]] ← Voltar aos saldos
- (navega) [[screen_balance_account-fac81|balance_account]] Todas as contas
- (navega) [[fn_ux.expired_callback_screen-327bb|expired_callback_screen]] 🏦 Ver saldos por conta
- (navega) [[act_balance_initial-82e49|balance_initial]] botão da resposta
- (navega) [[act_cancel-c6497|cancel]] botão da resposta
- (chama) [[fn_ux._cash_accounts_screen-0bdea|_cash_accounts_screen]] 
- (chama) [[fn_ux._cash_account_detail_screen-2f392|_cash_account_detail_screen]] 
- (chama) [[fn_ux._balance_account_screen-85ed8|_balance_account_screen]] 
- (chama) [[fn_ux._cash_setup_start-b8255|_cash_setup_start]] 
