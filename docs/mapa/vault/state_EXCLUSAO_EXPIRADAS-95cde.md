---
tipo: state
arquivo: app.py
linha: 300
---
# EXCLUSAO_EXPIRADAS

set de chat_id com exclusao pendente vencida (TTL 10 min); um 'sim' tardio nunca confirma

`state:EXCLUSAO_EXPIRADAS`

## Vem de
- (le_estado) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] ordem 8: exclusao pendente vencida -> aviso; um sim tardio nao confirma
- (le_estado) [[cb___confirmar_exclusao-3fc51|__confirmar_exclusao__]] 
