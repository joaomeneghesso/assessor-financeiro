---
tipo: handler
arquivo: app.py
linha: 4644
---
# help_command

Ajuda UX 2.0 por topico; cai em advanced_help com montar_help_por_tema

`fn:app.help_command`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (chama) [[fn_ux.run_experience-c1322|ux.run_experience]] act view help / topic / advanced_help
- (chama) [[fn_app.montar_help_por_tema-2f32e|app.montar_help_por_tema]] fallback tema legado
- (grava_estado) [[state_ux.session_draft_stage_pending-60605|ux.session(draft/stage/pending)]] pause_for_guidance/_suspend_flow

## Vem de
- (chama) [[cmd_help-8f98e|/help]] CommandHandler
