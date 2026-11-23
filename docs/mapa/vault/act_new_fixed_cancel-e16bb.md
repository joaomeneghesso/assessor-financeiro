---
tipo: action
arquivo: telegram_experiencia.py
linha: 2869
---
# new_fixed_cancel

Cancela cadastro do fixo.

`act:new_fixed_cancel`

## Vai para
- (grava_estado) [[state_Session.new_fixed-b5c04|Session.new_fixed]] 
- (navega) [[screen_home-111fe|home]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (navega) [[act_view-1d8b8|view]] botão da resposta

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[fn_ux._new_fixed_prompt-ecd34|_new_fixed_prompt]] Cancelar
- (navega) [[screen_new_fixed_preview-94294|new_fixed_preview]] Cancelar
- (navega) [[screen_new_fixed_edit_menu-08f30|new_fixed_edit_menu]] Cancelar
- (chama) [[fn_ux._new_fixed_preview-90ab6|_new_fixed_preview]] 
- (chama) [[fn_ux._new_fixed_edit_menu-3488b|ux._new_fixed_edit_menu]] 
