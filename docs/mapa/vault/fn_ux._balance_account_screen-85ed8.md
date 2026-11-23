---
tipo: handler
arquivo: telegram_experiencia.py
linha: 4303
---
# _balance_account_screen

Caixa de uma conta; grava Session.month (l.3407).

`fn:ux._balance_account_screen`

## Vai para
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.3407
- (chama) [[fn_services.calcular_caixa_por_conta_mes-3f8f8|services.calcular_caixa_por_conta_mes]] 
- (chama) [[fn_services.normalizar_conta_caixa-773c5|services.normalizar_conta_caixa]] 
- (chama) [[fn_services.conta_centraliza_fluxo_mensal-c7415|services.conta_centraliza_fluxo_mensal]] 
- (chama) [[fn_services.obter_metricas_resultado_mes-ecfb1|services.obter_metricas_resultado_mes]] 
- (chama) [[act_balance_account-4ec4f|balance_account]] 
- (chama) [[act_cash_account_detail-c0e6b|cash_account_detail]] 
- (chama) [[act_cash_setup_account-7864b|cash_setup_account]] 
- (chama) [[act_legacy_raw-2e265|legacy_raw]] 
- (chama) [[act_cash_accounts-a48cb|cash_accounts]] 
- (chama) [[act_view-1d8b8|view]] 

## Vem de
- (chama) [[fn_ux.fast_deterministic_query-fb2df|fast_deterministic_query]] saldo <conta>
- (chama) [[act_balance_account-4ec4f|balance_account]] 
