---
tipo: screen
arquivo: telegram_experiencia.py
linha: 3335
---
# cash_account_detail

Detalhe da conta (base, entradas, saídas) no mês; grava s.month (l.3336).

`screen:cash_account_detail`

## Vai para
- (chama) [[fn_services.calcular_caixa_por_conta_mes-3f8f8|services.calcular_caixa_por_conta_mes]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.3336
- (navega) [[act_copy_text-219aa|copy_text]] 📋 Copiar resumo
- (navega) [[act_cash_account_detail-c0e6b|cash_account_detail]] ‹ Mês anterior / Próximo mês ›
- (navega) [[act_legacy_raw-2e265|legacy_raw]] 📋 Ver movimentos
- (navega) [[act_cash_setup_account-7864b|cash_setup_account]] ✏️ Ajustar saldo
- (navega) [[act_cash_accounts-a48cb|cash_accounts]] ← Voltar aos saldos
- (navega) [[screen_home-111fe|home]] 🏠 Início

## Vem de
- (navega) [[act_cash_account_detail-c0e6b|cash_account_detail]] 
