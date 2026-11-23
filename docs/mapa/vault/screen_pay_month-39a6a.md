---
tipo: screen
arquivo: telegram_experiencia.py
linha: 3491
---
# pay_month

"Quanto vou pagar · <mês>" por conta (resposta ao texto "quanto vou pagar em <mês>"); grava s.month=month (l.3497).

`screen:pay_month`

## Vai para
- (chama) [[fn_compromissos.obter_itens_base_pagamentos_mes-4d0ba|compromissos.obter_itens_base_pagamentos_mes]] 
- (chama) [[fn_compromissos.calcular_resumo_pagamento_conta-dc584|compromissos.calcular_resumo_pagamento_conta]] 
- (chama) [[fn_services.aplicar_status_checklist-8e28a|services.aplicar_status_checklist]] 
- (chama) [[fn_services.montar_itens_checklist_mes-586cd|services.montar_itens_checklist_mes]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.3497
- (grava_estado) [[state_Session.pay_month_page-6ad4e|Session.pay_month_page]] 
- (navega) [[act_pay_month_expand-8623d|pay_month_expand]] ▶/▲ <conta>
- (navega) [[act_pay_month_account_detail-c0214|pay_month_account_detail]] 🔎 Ver lançamentos · conta
- (navega) [[act_pay_month_page-dc8ea|pay_month_page]] ‹ Contas / Mais contas ›
- (navega) [[btn_Mês_anterior-c7670|‹ Mês anterior]] ‹ Mês anterior
- (navega) [[btn_Próximo_mês-62aa3|Próximo mês ›]] Próximo mês ›
- (navega) [[screen_pay-ee2a3|pay]] 🧾 Abrir A pagar
- (navega) [[btn_Início-1bd0b|🏠 Início]] 🏠 Início

## Vem de
- (navega) [[act_pay_month-b80f8|pay_month]] 
- (navega) [[act_pay_month_expand-8623d|pay_month_expand]] 
- (navega) [[act_pay_month_page-dc8ea|pay_month_page]] 
