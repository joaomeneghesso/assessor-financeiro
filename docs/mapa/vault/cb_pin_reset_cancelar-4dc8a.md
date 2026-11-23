---
tipo: callback
arquivo: app.py
linha: 746
---
# pin_reset_cancelar

cancela reset guiado e reabre teclado PIN

`cb:pin_reset_cancelar`

## Vai para
- (grava_estado) [[state_PENDENCIAS_RESET_PIN-f7ae3|PENDENCIAS_RESET_PIN]] limpa
- (navega) [[fn_app.enviar_teclado_pin-92b87|app.enviar_teclado_pin]] 

## Vem de
- (navega) [[fn_app.processar_callback_pin-11bd1|app.processar_callback_pin]] 
- (navega) [[btn_Cancelar_recuperação-c71aa|✖️ Cancelar recuperação]] envia 'pin_reset_cancelar'
