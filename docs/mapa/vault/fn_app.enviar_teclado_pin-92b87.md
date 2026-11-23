---
tipo: handler
arquivo: app.py
linha: 724
---
# app.enviar_teclado_pin

Abre/renova teclado de PIN embaralhado

`fn:app.enviar_teclado_pin`

## Vai para
- (grava_estado) [[state_PIN_TECLADO-570e9|PIN_TECLADO]] 

## Vem de
- (chama) [[fn_app.desbloquear_command-2c762|desbloquear_command]] 
- (navega) [[cb_pin_reset_cancelar-4dc8a|pin_reset_cancelar]] 
- (chama) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] 
- (chama) [[fn_app.enviar_resposta-bb2f6|app.enviar_resposta]] 
