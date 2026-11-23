---
tipo: handler
arquivo: app.py
linha: 4707
---
# fechamento_command

abrir_atalho_ux closing

`fn:app.fechamento_command`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (chama) [[fn_app.abrir_atalho_ux-61f4e|app.abrir_atalho_ux]] closing
- (exige_pin) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] 'saldo geral' (nao e acao sensivel: so PIN se exportacao)

## Vem de
- (chama) [[cmd_fechamento-91459|/fechamento]] CommandHandler
