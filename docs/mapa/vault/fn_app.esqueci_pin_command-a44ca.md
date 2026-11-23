---
tipo: handler
arquivo: app.py
linha: 4461
---
# esqueci_pin_command

Instrucao de reset de PIN

`fn:app.esqueci_pin_command`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (chama) [[fn_app.enviar_resposta-bb2f6|app.enviar_resposta]] /seguranca

## Vem de
- (chama) [[cmd_esqueci_pin-498c9|/esqueci_pin]] CommandHandler
