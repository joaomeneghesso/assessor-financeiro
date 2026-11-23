---
tipo: service
arquivo: telegram_recursos.py
linha: 63
---
# telegram_recursos.dispatch

Ações origin | invoice_origin | quiz | quiz_answer | innovations | media_help | topics_setup (somente leitura).

`fn:telegram_recursos.dispatch`

## Vai para
- (le_estado) [[state_Session.month-7f614|Session.month]] origin usa s.month (108-112)
- (chama) [[fn_services.obter_metricas_resultado_mes-ecfb1|services.obter_metricas_resultado_mes]] 109
- (chama) [[fn_services.calcular_resumo_fatura-b4797|services.calcular_resumo_fatura]] 73 (invoice_origin)
- (chama) [[fn_services.resolver_item_checklist-a2267|services.resolver_item_checklist]] 70
- (chama) [[fn_consulta_cache.contexto_consulta-9f519|consulta_cache.contexto_consulta]] 69, 108

## Vem de
- (chama) [[mod_telegram_recursos.py-a9bf3|telegram_recursos.py]] 
- (chama) [[fn_telegram_experiencia.act-0d59a|telegram_experiencia.act]] 2338-2340
- (chama) [[act_origin-c0e35|origin]] 
- (chama) [[act_invoice_origin-2fa66|invoice_origin]] 
- (chama) [[act_quiz-7df1d|quiz]] 
- (chama) [[act_quiz_answer-2848b|quiz_answer]] 
- (chama) [[act_innovations-894de|innovations]] 
- (chama) [[act_media_help-a5ec1|media_help]] 
- (chama) [[act_topics_setup-544d4|topics_setup]] 
