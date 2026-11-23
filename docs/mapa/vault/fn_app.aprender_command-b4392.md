---
tipo: handler
arquivo: app.py
linha: 4610
---
# aprender_command

ux open_learning (publico: sem PIN)

`fn:app.aprender_command`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (chama) [[fn_ux.run_experience-c1322|ux.run_experience]] open_learning

## Vem de
- (chama) [[cmd_aprender-9853d|/aprender]] CommandHandler
