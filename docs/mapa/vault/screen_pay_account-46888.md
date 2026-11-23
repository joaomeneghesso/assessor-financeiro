---
tipo: screen
arquivo: telegram_experiencia.py
linha: 3622
---
# pay_account

Resumo "Quanto vou pagar no <conta>" (ou detalhe).

`screen:pay_account`

## Vai para
- (chama) [[fn_compromissos.calcular_resumo_pagamento_conta-dc584|compromissos.calcular_resumo_pagamento_conta]] 
- (chama) [[fn_compromissos.detalhar_pagamento_por_conta-62748|compromissos.detalhar_pagamento_por_conta]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.3625
- (navega) [[act_pay_account-299dd|pay_account]] ‹ Mês anterior / Próximo mês ›
- (navega) [[act_pay_account_detail-6c538|pay_account_detail]] Ver detalhes
- (navega) [[act_pay_account_filter-642f0|pay_account_filter]] A pagar filtrado
- (navega) [[screen_pay-ee2a3|pay]] Abrir A pagar
- (navega) [[screen_home-111fe|home]] 🏠 Início

## Vem de
- (navega) [[act_pay_account-299dd|pay_account]] 
- (navega) [[act_pay_account_detail-6c538|pay_account_detail]] 
