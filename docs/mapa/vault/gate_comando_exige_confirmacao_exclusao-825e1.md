---
tipo: security_gate
arquivo: app.py
linha: 1469
---
# comando_exige_confirmacao_exclusao

Regex de apagar/excluir/remover/cancelar ... -> exige previa+confirmar

`gate:comando_exige_confirmacao_exclusao`

## Vai para
- (navega) [[fn_app.solicitar_confirmacao_exclusao-1455f|app.solicitar_confirmacao_exclusao]] 

## Vem de
- (chama) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] ordem 12: apagar/excluir... -> previa (antes, gate de PIN do comando)
- (chama) [[cb_cmd-8bcfe|cmd:]] app.py
