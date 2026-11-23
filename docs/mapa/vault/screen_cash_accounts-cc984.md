---
tipo: screen
arquivo: telegram_experiencia.py
linha: 3263
---
# cash_accounts

Saldos por conta no mês; grava s.month=month (l.3268).

`screen:cash_accounts`

## Vai para
- (chama) [[fn_services.calcular_caixa_por_conta_mes-3f8f8|services.calcular_caixa_por_conta_mes]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.3268
- (grava_estado) [[state_Session.cash_page-7ddbf|Session.cash_page]] 
- (navega) [[act_cash_account_detail-c0e6b|cash_account_detail]] <conta>
- (navega) [[act_cash_accounts-a48cb|cash_accounts]] ‹ Contas / Mais contas ›
- (navega) [[act_cash_setup_start-c6f73|cash_setup_start]] ✏️ Ajustar saldos atuais
- (navega) [[act_cash_setup_new_account-43b33|cash_setup_new_account]] ➕ Outra conta
- (navega) [[screen_home-111fe|home]] 🏠 Início

## Vem de
- (navega) [[act_cash_accounts-a48cb|cash_accounts]] 
