---
tipo: text_trigger
arquivo: app.py
linha: 4876
---
# desbloquear <pin>

Texto 'desbloquear 123456' (PIN vai em claro no chat)

`text:desbloquear <pin>`

## Vai para
- (chama) [[gate_AUTH_LIMITER-f4350|AUTH_LIMITER]] 
- (grava_estado) [[state_SESSOES_SEGURANCA-5af35|SESSOES_SEGURANCA]] desbloqueia

## Vem de
- (chama) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] ordem 7: desbloqueio por PIN em texto (limiter+auditoria); apaga a mensagem com o PIN
