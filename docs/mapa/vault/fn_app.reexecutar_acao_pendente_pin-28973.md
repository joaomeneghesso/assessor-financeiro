---
tipo: handler
arquivo: app.py
linha: 987
---
# reexecutar_acao_pendente_pin

Apos PIN correto refaz a acao bloqueada: callback_submenu (se era botao) ou receber_mensagem (se era texto)

`fn:app.reexecutar_acao_pendente_pin`

## Vai para
- (le_estado) [[state_ACAO_PENDENTE_PIN-0c5d8|ACAO_PENDENTE_PIN]] 
- (chama) [[fn_app.callback_submenu-249d5|app.callback_submenu]] se a acao era um botao
- (chama) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] se a acao era texto

## Vem de
- (chama) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] ordem 7: apos desbloqueio correto refaz a acao bloqueada
- (chama) [[fn_app.processar_callback_pin-11bd1|app.processar_callback_pin]] PIN correto; sem acao pendente abre /menu
