---
tipo: handler
arquivo: app.py
linha: 4479
---
# app.limpar_command

Apaga mensagens rastreadas em MENSAGENS_CHAT

`fn:app.limpar_command`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (le_estado) [[state_MENSAGENS_CHAT-a0bbb|MENSAGENS_CHAT]] 
- (grava_estado) [[state_MENSAGENS_CHAT-a0bbb|MENSAGENS_CHAT]] zera

## Vem de
- (chama) [[cmd_limpar-95d87|/limpar]] CommandHandler
- (chama) [[cmd_clear-91068|/clear]] CommandHandler
