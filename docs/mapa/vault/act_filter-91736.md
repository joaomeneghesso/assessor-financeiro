---
tipo: action
arquivo: telegram_experiencia.py
linha: 2907
---
# filter

Filtro pay(all/overdue/soon/review) ou history(all/receita/despesa); page=0.

`act:filter`

## Vai para
- (grava_estado) [[state_Session.pay_filter-c235f|Session.pay_filter]] pay
- (grava_estado) [[state_Session.history_filter-db2cb|Session.history_filter]] history
- (grava_estado) [[state_Session.page-3e7eb|Session.page]] 
- (chama) [[fn_ux.render-b3471|Experience.render]] 
- (navega) [[screen_pay-ee2a3|pay]] pay
- (navega) [[screen_history-d40e7|history]] history

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_attention-ebc03|attention]] Resolver / conferir (dinâmico)
- (navega) [[screen_pay_tools-19539|pay_tools]] Todas/Vencidas/7 dias/Revisar baixas
- (navega) [[screen_history_tools-cc0f8|history_tools]] Todos/Despesas/Entradas
- (navega) [[screen_review_details-b6002|review_details]] 🔎 Revisar baixas antigas
- (navega) [[screen_agenda-a82fc|agenda]] Ver vencidas
- (navega) [[screen_obligation-113ca|obligation]] 
- (chama) [[fn_ux._pay_tools_screen-7fc89|_pay_tools_screen]] 
- (chama) [[fn_ux._history_tools_screen-c950e|_history_tools_screen]] 
