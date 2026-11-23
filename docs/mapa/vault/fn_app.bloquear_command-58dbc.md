---
tipo: handler
arquivo: app.py
linha: 4422
---
# bloquear_command

Bloqueia PIN e invalida sessao UX

`fn:app.bloquear_command`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (grava_estado) [[state_SESSOES_SEGURANCA-5af35|SESSOES_SEGURANCA]] bloqueia
- (grava_estado) [[state_ux.session_draft_stage_pending-60605|ux.session(draft/stage/pending)]] invalidate (descarta registros)

## Vem de
- (chama) [[cmd_bloquear-80413|/bloquear]] CommandHandler
