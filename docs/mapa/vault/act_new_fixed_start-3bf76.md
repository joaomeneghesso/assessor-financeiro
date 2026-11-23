---
tipo: action
arquivo: telegram_experiencia.py
linha: 2849
---
# new_fixed_start

Inicia cadastro de novo fixo.

`act:new_fixed_start`

## Vai para
- (chama) [[fn_ux._new_fixed_prompt-ecd34|_new_fixed_prompt]] 
- (grava_estado) [[state_Session.new_fixed-b5c04|Session.new_fixed]] 
- (chama) [[fn_ux.begin_new_fixed-c0f92|ux.begin_new_fixed]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_register-1389d|register]] 🧾 Novo fixo
- (chama) [[act_guided-cf3e7|guided]] registrar_fixo
