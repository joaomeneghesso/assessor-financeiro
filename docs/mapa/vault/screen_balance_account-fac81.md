---
tipo: screen
arquivo: telegram_experiencia.py
linha: 3403
---
# balance_account

Caixa de uma conta no mês; grava s.month (l.3407). Texto "saldo <conta>" cai aqui.

`screen:balance_account`

## Vai para
- (chama) [[fn_services.calcular_caixa_por_conta_mes-3f8f8|services.calcular_caixa_por_conta_mes]] 
- (chama) [[fn_services.obter_metricas_resultado_mes-ecfb1|services.obter_metricas_resultado_mes]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.3407
- (navega) [[act_balance_account-4ec4f|balance_account]] ‹ Mês anterior / Próximo mês ›
- (navega) [[act_cash_account_detail-c0e6b|cash_account_detail]] Ver composição
- (navega) [[act_cash_setup_account-7864b|cash_setup_account]] ✏️ Ajustar saldo
- (navega) [[act_legacy_raw-2e265|legacy_raw]] Ver extrato
- (navega) [[act_cash_accounts-a48cb|cash_accounts]] Todas as contas
- (navega) [[screen_home-111fe|home]] 🏠 Início

## Vem de
- (navega) [[act_balance_account-4ec4f|balance_account]] 
