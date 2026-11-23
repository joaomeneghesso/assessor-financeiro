---
tipo: handler
arquivo: telegram_experiencia.py
linha: 5250
---
# ux.dispatch_callback

telegram_experiencia: trata callbacks ux: (chamado em callback_submenu apos pin_ e af:)

`fn:ux.dispatch_callback`

## Vai para
- (chama) [[act_copy_text-219aa|copy_text]] 
- (chama) [[act_topics_create-058a8|topics_create]] 
- (chama) [[act_ai_status-127b5|ai_status]] 
- (chama) [[act_ai_route-0c6a9|ai_route]] 
- (chama) [[act_guided-cf3e7|guided]] 
- (chama) [[act_legacy-00431|legacy]] 
- (chama) [[act_legacy_raw-2e265|legacy_raw]] 
- (chama) [[act_lock-5ad19|lock]] 
- (navega) [[fn_ux.expired_callback_screen-327bb|expired_callback_screen]] action None
- (chama) [[fn_ux.resolve-4d9fe|Experience.resolve]] ux:<token> -> ação
- (chama) [[fn_ux.run_experience-c1322|ux.run_experience]] act(action)
- (chama) [[fn_ux.send_screen-6d6ac|send_screen]] edit=True
- (le_estado) [[state_Session.month-7f614|Session.month]] só p/ tela expirada de saldos (l.4285)
- (chama) [[fn_ux.clear_service_pending-6ba11|clear_service_pending]] guided
- (chama) [[fn_ux.session_key-714ba|session_key]] 
- (chama) [[fn_ux.act-20779|Experience.act]] 

## Vem de
- (chama) [[cb_ux-378ef|ux:]] 
- (chama) [[fn_app.callback_submenu-249d5|app.callback_submenu]] 
- (volta) [[act_chart-efa97|chart]] envia foto
