---
tipo: handler
arquivo: app.py
linha: 5049
---
# app.callback_submenu

Roteador de CallbackQuery: pin_*, af:, ux:, cmd:* (inclui __legado__ com vinculo de previa)

`fn:app.callback_submenu`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (navega) [[cb_pin-c0fea|pin_*]] ordem 1
- (navega) [[cb_af-51179|af:]] ordem 2 (se telegram_alertas.callback nao tratar, segue)
- (navega) [[cb_ux-378ef|ux:]] ordem 3 (limpa PENDENCIAS_EXCLUSAO; depois ux.dispatch_callback)
- (navega) [[cb_cmd-8bcfe|cmd:]] ordem 4 (fallback): token -> CALLBACK_COMANDOS
- (le_estado) [[state_ux.session_draft_stage_pending-60605|ux.session(draft/stage/pending)]] ux.run_experience handle_text
- (chama) [[fn_ux.dispatch_callback-a9f29|ux.dispatch_callback]] 

## Vem de
- (chama) [[handler_CallbackQueryHandler-4ad8f|CallbackQueryHandler(callback_submenu)]] 
- (chama) [[fn_app.reexecutar_acao_pendente_pin-28973|reexecutar_acao_pendente_pin]] se a acao era um botao
