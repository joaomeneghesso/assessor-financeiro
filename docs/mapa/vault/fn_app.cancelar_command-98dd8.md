---
tipo: handler
arquivo: app.py
linha: 5470
---
# cancelar_command

Invalida sessao UX e limpa pendencias guiada/exclusao

`fn:app.cancelar_command`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (grava_estado) [[state_PENDENCIAS_GUIADAS-21a17|PENDENCIAS_GUIADAS]] limpa
- (grava_estado) [[state_PENDENCIAS_EXCLUSAO-1f0a4|PENDENCIAS_EXCLUSAO]] limpa
- (grava_estado) [[state_ux.session_draft_stage_pending-60605|ux.session(draft/stage/pending)]] invalidate
- (le_estado) [[state_PENDENCIAS_APRENDIZADO_CATEGORIA-ac4b1|PENDENCIAS_APRENDIZADO_CATEGORIA]] NAO limpa (inconsistente)

## Vem de
- (chama) [[cmd_cancelar-18e66|/cancelar]] CommandHandler
