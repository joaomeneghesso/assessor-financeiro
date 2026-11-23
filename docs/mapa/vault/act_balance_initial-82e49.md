---
tipo: action
arquivo: telegram_experiencia.py
linha: 3174
---
# balance_initial

Saldo inicial do mês.

`act:balance_initial`

## Vai para
- (grava_estado) [[state_Session.settings_draft-703dd|Session.settings_draft]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] initial_balance
- (le_estado) [[state_Session.month-7f614|Session.month]] 
- (chama) [[fn_db.buscar_saldos_contas_mes-d2278|db.buscar_saldos_contas_mes]] 
- (chama) [[fn_db.buscar_saldo_mensal-82b9a|db.buscar_saldo_mensal]] 
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] 
- (navega) [[act_cancel-c6497|cancel]] botão da resposta
- (navega) [[act_topic-518da|topic]] botão da resposta
- (navega) [[act_cash_setup_start-c6f73|cash_setup_start]] botão da resposta
- (navega) [[act_cash_accounts-a48cb|cash_accounts]] botão da resposta

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_balance_details-02072|balance_details]] Saldo na abertura
- (navega) [[act_balance_start-167b7|balance_start]] 
