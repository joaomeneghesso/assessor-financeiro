---
tipo: handler
arquivo: app.py
linha: 4711
---
# atencao_command

abrir_atalho_ux attention

`fn:app.atencao_command`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (chama) [[fn_app.abrir_atalho_ux-61f4e|app.abrir_atalho_ux]] attention
- (exige_pin) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] 'saldo geral' (nao e acao sensivel: so PIN se exportacao)

## Vem de
- (chama) [[cmd_atencao-91288|/atencao]] CommandHandler
