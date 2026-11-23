---
tipo: callback
arquivo: app.py
linha: 746
---
# pin_pair:<i>

toque no par de digitos; ao completar verifica PIN em thread

`cb:pin_pair:<i>`

## Vai para
- (grava_estado) [[state_PIN_TECLADO-570e9|PIN_TECLADO]] 
- (chama) [[gate_AUTH_LIMITER-f4350|AUTH_LIMITER]] 
- (grava_estado) [[state_SESSOES_SEGURANCA-5af35|SESSOES_SEGURANCA]] desbloqueia
- (navega) [[fn_app.menu_command-1f10a|app.menu_command]] apos desbloquear abre menu; a acao bloqueada original NAO e reexecutada
- (navega) [[btn_Bloquear_agora-bdf62|🔒 Bloquear agora]] 
- (navega) [[btn_Bloquear_agora-bdf62|🔒 Bloquear agora]] teclado inline

## Vem de
- (navega) [[fn_app.processar_callback_pin-11bd1|app.processar_callback_pin]] 
- (navega) [[btn_pares_N-M_pin_pair_i-ecf4f|pares N-M (pin_pair:i)]] envia 'pin_pair:<i>'
