---
tipo: handler
arquivo: telegram_experiencia.py
linha: 4751
---
# question_result

Fallback: tenta orient.reconhecer_pergunta, senão tela "Qual caminho?".

`fn:ux.question_result`

## Vai para
- (chama) [[act_view-1d8b8|view]] 
- (chama) [[fn_orientacao.reconhecer_pergunta-2077d|reconhecer_pergunta]] 
- (grava_estado) [[state_Session.ai_question-7def3|Session.ai_question]] 
- (navega) [[screen_analytics-4bd00|analytics]] Analisar meus gastos
- (navega) [[screen_balance-64c54|balance]] Ver meu saldo
- (navega) [[screen_pay-ee2a3|pay]] Contas a pagar
- (navega) [[screen_receivables-eb894|receivables]] Entradas previstas
- (navega) [[screen_plan-adfe6|plan]] Planejar meu mês
- (navega) [[screen_register-1389d|register]] Registrar movimento
- (navega) [[act_ask-dbbdf|ask]] Perguntar de novo
- (navega) [[screen_home-111fe|home]] 🏠 Início
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 

## Vem de
- (chama) [[fn_ux.dispatch_text-8df9e|ux.dispatch_text]] LocalUnavailable + "?"
- (chama) [[fn_ux._ai_query_result-20fe1|_ai_query_result]] 
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 
