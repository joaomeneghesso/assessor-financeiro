---
tipo: handler
arquivo: app.py
linha: 4560
---
# start

Deep link (args) ou menu_command

`fn:app.start`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (chama) [[fn_app.menu_command-1f10a|app.menu_command]] sem deep link
- (chama) [[fn_ux.run_experience-c1322|ux.run_experience]] deep link (render/act)
- (exige_pin) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] 'dashboard' exceto lesson/help/learn

## Vem de
- (chama) [[cmd_start-ad3b7|/start]] CommandHandler
