---
tipo: state
arquivo: app.py
linha: 1300
---
# CALLBACK_COMANDOS

dict token 'cmd:<rand>' -> comando; max 500 (poda 250 mais antigos); persistido em .runtime/telegram_callbacks.bin; expira 24h

`state:CALLBACK_COMANDOS`

## Vem de
- (le_estado) [[cb_cmd-8bcfe|cmd:]] expirado -> 'Esse botão expirou'
- (grava_estado) [[fn_app.registrar_callback_comando-5ee62|app.registrar_callback_comando]] 
- (le_estado) [[cb___legado-f60eb|__legado__[tipo:assinatura]:<cmd>]] assinatura via services.assinatura_pendencia
