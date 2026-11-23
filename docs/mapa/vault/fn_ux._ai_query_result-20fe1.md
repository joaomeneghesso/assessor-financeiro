---
tipo: handler
arquivo: telegram_experiencia.py
linha: 4628
---
# _ai_query_result

Executa consulta estruturada (payables, totais, categorias, rotas). Grava Session.month = months[-1] (l.3741).

`fn:ux._ai_query_result`

## Vai para
- (chama) [[fn_ux._ai_months-95d1a|_ai_months]] 
- (chama) [[fn_ux._month_from_text-ef224|_month_from_text]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.3741 s.month=months[-1] - NUNCA restaurado depois
- (chama) [[fn_ux._pay_month_screen-fe596|_pay_month_screen]] qtype payables
- (chama) [[act_view-1d8b8|view]] intent renderizável
- (chama) [[fn_ux._suspend_flow-76c4a|_suspend_flow]] 
- (chama) [[fn_ux._ai_registration_preview-cdfb6|_ai_registration_preview]] register_expense/income
- (chama) [[fn_ux.question_result-77118|question_result]] 
- (grava_estado) [[bug_menu_mes_novembro-e8fd4|BUG mês vaza para o Menu]] origem do vazamento (l.3741)

## Vem de
- (chama) [[fn_assessor_ia_local.interpretar_contexto-e0413|interpretar_contexto]] parsed -> consulta determinística
- (chama) [[fn_ux.fast_deterministic_query-fb2df|fast_deterministic_query]] payables
- (chama) [[fn_ux.dispatch_text-8df9e|ux.dispatch_text]] 
