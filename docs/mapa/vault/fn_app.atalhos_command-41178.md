---
tipo: handler
arquivo: app.py
linha: 4529
---
# atalhos_command

Abre teclado inferior (ReplyKeyboard) de atalhos

`fn:app.atalhos_command`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (exige_pin) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] 'saldo geral'
- (grava_estado) [[state_menu_inferior_novo-5257a|montar_menu_principal (ReplyKeyboard)]] abre=True

## Vem de
- (chama) [[cmd_atalhos-bf841|/atalhos]] CommandHandler
