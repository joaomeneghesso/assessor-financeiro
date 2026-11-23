---
tipo: handler
arquivo: app.py
linha: 3298
---
# app.enviar_resposta

Envia resposta; anexa teclado inline por montar_teclado_inline_para_resposta e persiste callbacks

`fn:app.enviar_resposta`

## Vai para
- (grava_estado) [[state_MENSAGENS_CHAT-a0bbb|MENSAGENS_CHAT]] registrar_mensagem_enviada
- (chama) [[fn_app.montar_teclado_inline_para_resposta-e330f|app.montar_teclado_inline_para_resposta]] 
- (chama) [[fn_app.guardar_acao_pendente_pin-68f50|guardar_acao_pendente_pin]] arquivo (backup/CSV) so vai ao chat com PIN valido
- (chama) [[fn_app.enviar_teclado_pin-92b87|app.enviar_teclado_pin]] 

## Vem de
- (chama) [[fn_app.esqueci_pin_command-a44ca|esqueci_pin_command]] /seguranca
- (chama) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] 
- (chama) [[cb_cmd-8bcfe|cmd:]] 
- (chama) [[text_menu-03529|menu]] teclado inline da Central (comando in __help__/menu/central)
- (chama) [[cb___help-92276|__help__]] teclado de /help
