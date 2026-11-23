---
tipo: handler
arquivo: app.py
linha: 1622
---
# app.cancelar_confirmacao_exclusao

Limpa PENDENCIAS_EXCLUSAO

`fn:app.cancelar_confirmacao_exclusao`

## Vai para
- (grava_estado) [[state_PENDENCIAS_EXCLUSAO-1f0a4|PENDENCIAS_EXCLUSAO]] limpa

## Vem de
- (chama) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] texto 'cancelar'
- (chama) [[cb___cancelar_exclusao-623cb|__cancelar_exclusao__]] 
