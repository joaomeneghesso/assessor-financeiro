---
tipo: state
arquivo: app.py
linha: 64
---
# PIN_TECLADO

dict user_id -> pares embaralhados + escolhas do teclado de PIN

`state:PIN_TECLADO`

## Vem de
- (grava_estado) [[cb_pin_pair_i-32cd9|pin_pair:<i>]] 
- (grava_estado) [[cb_pin_limpar-ceb0c|pin_limpar]] 
- (grava_estado) [[cb_pin_cancelar-c97bd|pin_cancelar]] 
- (grava_estado) [[fn_app.enviar_teclado_pin-92b87|app.enviar_teclado_pin]] 
