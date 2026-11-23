---
tipo: action
arquivo: telegram_experiencia.py
linha: 3353
---
# start

Inicia registro (despesa/receita/simulate).

`act:start`

## Vai para
- (chama) [[fn_ux.begin-7f489|begin]] 
- (le_estado) [[state_Session.suspended_draft-e4ebe|Session.suspended_draft]] 
- (le_estado) [[state_Session.suspended_stage-bae0e|Session.suspended_stage]] 
- (navega) [[act_resume_suspended-0e970|resume_suspended]] botão da resposta
- (navega) [[act_discard_and_start-8d1d6|discard_and_start]] botão da resposta

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_register-1389d|register]] − Despesa
- (navega) [[screen_planning_tools-d534b|planning_tools]] 🔮 Simular compra
- (navega) [[screen_assistant-c05b6|assistant]] Posso comprar?
- (navega) [[fn_ux.preview-35809|preview]] Nova simulação
- (navega) [[screen_can_buy-e0e39|can_buy]] 
- (navega) [[screen_advanced_help-617c1|advanced_help]] 
- (chama) [[fn_ux.begin_can_buy-202cd|ux.begin_can_buy]] 
