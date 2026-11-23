---
tipo: state
arquivo: app.py
linha: 1359
---
# MENSAGENS_CHAT

dict chat_id -> ids de mensagens rastreadas (max 300) para /limpar

`state:MENSAGENS_CHAT`

## Vem de
- (le_estado) [[fn_app.limpar_command-b7131|app.limpar_command]] 
- (grava_estado) [[fn_app.limpar_command-b7131|app.limpar_command]] zera
- (grava_estado) [[fn_app.enviar_resposta-bb2f6|app.enviar_resposta]] registrar_mensagem_enviada
