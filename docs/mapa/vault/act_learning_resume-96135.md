---
tipo: action
arquivo: telegram_experiencia.py
linha: 2838
---
# learning_resume

Retoma cadastro de fixo pausado.

`act:learning_resume`

## Vai para
- (le_estado) [[state_Session.learning_stage-1e8f0|Session.learning_stage]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (navega) [[screen_fixos-1e200|fixos]] 
- (navega) [[fn_ux._new_fixed_prompt-ecd34|_new_fixed_prompt]] 
- (chama) [[fn_fixos_interface.retomar-ea2c7|fixos_interface.retomar]] 
- (le_estado) [[state_Session.fixed_edit-92b26|Session.fixed_edit]] 
- (le_estado) [[state_Session.new_fixed-b5c04|Session.new_fixed]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[act_chart-efa97|chart]] botão da resposta
