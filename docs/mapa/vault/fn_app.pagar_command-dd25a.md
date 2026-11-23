---
tipo: handler
arquivo: app.py
linha: 4695
---
# pagar_command

abrir_atalho_ux pay

`fn:app.pagar_command`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (chama) [[fn_app.abrir_atalho_ux-61f4e|app.abrir_atalho_ux]] pay
- (exige_pin) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] 'saldo geral' (nao e acao sensivel: so PIN se exportacao)

## Vem de
- (chama) [[cmd_pagar-2cad9|/pagar]] CommandHandler
