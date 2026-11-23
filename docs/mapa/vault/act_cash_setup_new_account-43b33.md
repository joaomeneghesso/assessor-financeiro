---
tipo: action
arquivo: telegram_experiencia.py
linha: 2989
---
# cash_setup_new_account

Ajuste de saldo de conta nova.

`act:cash_setup_new_account`

## Vai para
- (grava_estado) [[state_Session.settings_draft-703dd|Session.settings_draft]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] 
- (navega) [[act_cancel-c6497|cancel]] botão da resposta

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_cash_accounts-cc984|cash_accounts]] ➕ Outra conta
- (chama) [[fn_ux._cash_accounts_screen-0bdea|_cash_accounts_screen]] 
- (chama) [[fn_ux._cash_setup_start-b8255|_cash_setup_start]] 
