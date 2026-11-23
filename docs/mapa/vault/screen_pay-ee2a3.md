---
tipo: screen
arquivo: telegram_experiencia.py
linha: 1105
---
# pay

A pagar: lista paginada de obrigações do mês; filtros pay_filter/pay_account_filter; mês = s.month.

`screen:pay`

## Vai para
- (le_estado) [[state_Session.month-7f614|Session.month]] título/consulta usa s.month
- (chama) [[fn_ux.obligations-15fc7|obligations]] 
- (chama) [[fn_orientacao.coletar-ba856|coletar]] 
- (le_estado) [[state_Session.pay_filter-c235f|Session.pay_filter]] 
- (le_estado) [[state_Session.pay_account_filter-280ee|Session.pay_account_filter]] 
- (le_estado) [[state_Session.page-3e7eb|Session.page]] 
- (navega) [[act_detail_obligation-b6e92|detail_obligation]] N. <obrigação>
- (navega) [[act_page-3b059|page]] ‹ Anteriores / Próximas ›
- (navega) [[act_pay_tools-3fb1a|pay_tools]] 🔎 Filtrar
- (navega) [[fn_ux.nav-29bea|Experience.nav]] nav
- (chama) [[fn_ux._pay_rich-2174b|ux._pay_rich]] 
- (chama) [[fn_ux.due_label-8d089|ux.due_label]] 

## Vem de
- (navega) [[screen_home-111fe|home]] 🧾 A pagar
- (navega) [[screen_more-4f9f6|more]] 🧾 A pagar
- (navega) [[screen_attention-ebc03|attention]] Conferir A pagar
- (navega) [[screen_closing_details-60038|closing_details]] 🧾 Ver contas
- (navega) [[screen_advanced_help-617c1|advanced_help]] atalhos do tema
- (navega) [[screen_obligation-113ca|obligation]] 🧾 Voltar a A pagar
- (navega) [[screen_pay_month-39a6a|pay_month]] 🧾 Abrir A pagar
- (navega) [[screen_pay_account-46888|pay_account]] Abrir A pagar
- (navega) [[fn_ux.expired_callback_screen-327bb|expired_callback_screen]] 🧾 Abrir A pagar
- (navega) [[fn_ux.question_result-77118|question_result]] Contas a pagar
- (navega) [[act_filter-91736|filter]] pay
- (navega) [[act_clear_pay_filters-3757f|clear_pay_filters]] 
- (navega) [[act_account_filter-0f866|account_filter]] 
- (navega) [[act_pay_account_filter-642f0|pay_account_filter]] 
- (navega) [[act_cancel-c6497|cancel]] 
- (navega) [[act_new_fixed_commit-b9167|new_fixed_commit]] 
