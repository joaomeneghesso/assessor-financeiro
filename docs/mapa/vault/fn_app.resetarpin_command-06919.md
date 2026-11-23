---
tipo: handler
arquivo: app.py
linha: 4469
---
# resetarpin_command

Reset de PIN via comando

`fn:app.resetarpin_command`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (chama) [[fn_app.processar_reset_pin-092e9|app.processar_reset_pin]] 

## Vem de
- (chama) [[cmd_reset-e7bdc|/reset]] CommandHandler
- (chama) [[cmd_resetarpin-60ca1|/resetarpin]] CommandHandler
