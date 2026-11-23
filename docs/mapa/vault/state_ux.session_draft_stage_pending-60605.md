---
tipo: state
arquivo: app.py
linha: 4540
---
# ux.session(draft/stage/pending)

Sessao UX nativa (stage, draft, fixed_edit, new_fixed, service pending) por user:chat; competidor das PENDENCIAS_* legadas

`state:ux.session(draft/stage/pending)`

## Vem de
- (grava_estado) [[fn_app.menu_command-1f10a|app.menu_command]] clear_service_pending
- (grava_estado) [[fn_app.cancelar_command-98dd8|cancelar_command]] invalidate
- (grava_estado) [[fn_app.bloquear_command-58dbc|bloquear_command]] invalidate (descarta registros)
- (grava_estado) [[fn_app.help_command-cfdad|help_command]] pause_for_guidance/_suspend_flow
- (le_estado) [[fn_app.callback_submenu-249d5|app.callback_submenu]] ux.run_experience handle_text
- (le_estado) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] ux.dispatch_text
