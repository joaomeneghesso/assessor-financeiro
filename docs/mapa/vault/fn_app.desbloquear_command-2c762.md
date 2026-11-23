---
tipo: handler
arquivo: app.py
linha: 4440
---
# desbloquear_command

Abre teclado de PIN

`fn:app.desbloquear_command`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (chama) [[fn_app.enviar_teclado_pin-92b87|app.enviar_teclado_pin]] 

## Vem de
- (chama) [[cmd_desbloquear-a195b|/desbloquear]] CommandHandler
