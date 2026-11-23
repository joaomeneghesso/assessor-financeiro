---
tipo: action
arquivo: telegram_experiencia.py
linha: 2986
---
# cash_setup_start

Ajustar saldos atuais (todas as contas); força mês corrente.

`act:cash_setup_start`

## Vai para
- (chama) [[fn_ux._cash_setup_start-b8255|_cash_setup_start]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.3363 força mês corrente
- (grava_estado) [[state_Session.settings_draft-703dd|Session.settings_draft]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_home-111fe|home]] ✏️ Ajustar saldo
- (navega) [[screen_month_actions-bedf6|month_actions]] ✏️ Ajustar saldos
- (navega) [[screen_attention-ebc03|attention]] Resolver/conferir
- (navega) [[screen_balance-64c54|balance]] ✏️ Ajustar saldo
- (navega) [[screen_setup-2cfa0|setup]] Informar saldo atual
- (navega) [[screen_cash_accounts-cc984|cash_accounts]] ✏️ Ajustar saldos atuais
- (navega) [[act_balance_start-167b7|balance_start]] 
- (navega) [[act_balance_initial-82e49|balance_initial]] botão da resposta
- (chama) [[fn_ux._cash_accounts_screen-0bdea|_cash_accounts_screen]] 
