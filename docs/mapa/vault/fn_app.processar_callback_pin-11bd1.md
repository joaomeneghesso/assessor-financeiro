---
tipo: handler
arquivo: app.py
linha: 746
---
# app.processar_callback_pin

Teclado de PIN: pin_pair/pin_limpar/pin_cancelar/pin_resetar/pin_reset_cancelar

`fn:app.processar_callback_pin`

## Vai para
- (navega) [[cb_pin_pair_i-32cd9|pin_pair:<i>]] 
- (navega) [[cb_pin_limpar-ceb0c|pin_limpar]] 
- (navega) [[cb_pin_cancelar-c97bd|pin_cancelar]] 
- (navega) [[cb_pin_resetar-60741|pin_resetar]] 
- (navega) [[cb_pin_reset_cancelar-4dc8a|pin_reset_cancelar]] 
- (chama) [[fn_app.reexecutar_acao_pendente_pin-28973|reexecutar_acao_pendente_pin]] PIN correto; sem acao pendente abre /menu
- (chama) [[fn_app.menu_command-1f10a|app.menu_command]] 

## Vem de
- (chama) [[cb_pin-c0fea|pin_*]] 
