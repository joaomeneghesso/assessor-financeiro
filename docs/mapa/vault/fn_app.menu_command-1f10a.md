---
tipo: handler
arquivo: app.py
linha: 4540
---
# app.menu_command

/menu: limpa pendencias guiada/exclusao/servico e abre ux view home

`fn:app.menu_command`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (exige_pin) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] 'saldo geral'
- (grava_estado) [[state_PENDENCIAS_GUIADAS-21a17|PENDENCIAS_GUIADAS]] limpa
- (grava_estado) [[state_PENDENCIAS_EXCLUSAO-1f0a4|PENDENCIAS_EXCLUSAO]] limpa
- (grava_estado) [[state_ux.session_draft_stage_pending-60605|ux.session(draft/stage/pending)]] clear_service_pending
- (chama) [[fn_ux.run_experience-c1322|ux.run_experience]] act view home

## Vem de
- (chama) [[cmd_menu-be698|/menu]] CommandHandler
- (chama) [[fn_app.start-649a9|start]] sem deep link
- (navega) [[cb_pin_pair_i-32cd9|pin_pair:<i>]] apos desbloquear abre menu; a acao bloqueada original NAO e reexecutada
- (chama) [[fn_app.processar_callback_pin-11bd1|app.processar_callback_pin]] 
