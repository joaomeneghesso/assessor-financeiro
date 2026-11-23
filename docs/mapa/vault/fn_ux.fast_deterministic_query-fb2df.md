---
tipo: handler
arquivo: telegram_experiencia.py
linha: 4593
---
# fast_deterministic_query

Consulta textual inequívoca sem IA: saldo <conta>, quanto vou pagar [em <mês>] [conta]. Texto SEM mês volta ao mês corrente; COM mês grava Session.month.

`fn:ux.fast_deterministic_query`

## Vai para
- (chama) [[fn_ux._month_from_text-ef224|_month_from_text]] 
- (chama) [[fn_consultas_rapidas.interpretar_consulta-9e67b|consultas_rapidas.interpretar_consulta]] 
- (chama) [[fn_ux._balance_account_screen-85ed8|_balance_account_screen]] saldo <conta>
- (chama) [[fn_ux._pay_account_screen-545a8|_pay_account_screen]] quanto vou pagar <conta>
- (chama) [[fn_ux._ai_query_result-20fe1|_ai_query_result]] payables
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.3720 s.month=mês do texto (ou corrente se sem mês)
- (grava_estado) [[state_Session.pay_month_page-6ad4e|Session.pay_month_page]] zera
- (grava_estado) [[bug_menu_mes_novembro-e8fd4|BUG mês vaza para o Menu]] origem do vazamento (l.3720)

## Vem de
- (chama) [[fn_ux.dispatch_text-8df9e|ux.dispatch_text]] global_candidate (pergunta/consulta)
