---
tipo: screen
arquivo: telegram_experiencia.py
linha: 1937
---
# reconciliations

Conciliação: pendências e vínculos do mês.

`screen:reconciliations`

## Vai para
- (le_estado) [[state_Session.month-7f614|Session.month]] título/consulta usa s.month
- (chama) [[fn_services.obter_metricas_resultado_mes-ecfb1|services.obter_metricas_resultado_mes]] 
- (chama) [[fn_conciliacao.listar_vinculos-ca122|listar_vinculos]] 
- (navega) [[screen_review-185df|review]] 🧩 Resolver pendências
- (navega) [[act_unlink_preview-4398d|unlink_preview]] Desvincular #id
- (navega) [[act_page-3b059|page]] ‹ Anteriores / Próximas ›
- (navega) [[fn_ux.nav-29bea|Experience.nav]] nav
- (grava_estado) [[state_Session.page-3e7eb|Session.page]] 
- (navega) [[act_view-1d8b8|view]] 

## Vem de
- (navega) [[screen_month_actions-bedf6|month_actions]] 🔗 Conciliação
- (navega) [[screen_review_details-b6002|review_details]] 🔗 Movimentos conciliados
- (navega) [[screen_review_tools-cb4c3|review_tools]] 🔗 Conciliações
- (navega) [[screen_transaction-cd364|transaction]] Ver conciliação
- (navega) [[screen_advanced_help-617c1|advanced_help]] 
- (navega) [[screen_obligation-113ca|obligation]] 
