---
tipo: handler
arquivo: telegram_experiencia.py
linha: 4778
---
# ux.run_experience

telegram_experiencia: act/render/handle_text/open_learning/advanced_help

`fn:ux.run_experience`

## Vai para
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (grava_estado) [[state_Session.persist-7ac83|Session.persist]] 
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 

## Vem de
- (chama) [[fn_app.abrir_atalho_ux-61f4e|app.abrir_atalho_ux]] act view/cash_accounts
- (chama) [[fn_app.dashboard_command-1e8d5|dashboard_command]] act chart
- (chama) [[fn_app.recursos_command-92877|recursos_command]] act innovations
- (chama) [[fn_app.menu_command-1f10a|app.menu_command]] act view home
- (chama) [[fn_app.aprender_command-b4392|aprender_command]] open_learning
- (chama) [[fn_app.help_command-cfdad|help_command]] act view help / topic / advanced_help
- (chama) [[fn_app.start-649a9|start]] deep link (render/act)
- (chama) [[cb_cmd-8bcfe|cmd:]] handle_text(comando) ANTES do legado, exceto __legado__/__exportar_periodo__ (app.py)
- (chama) [[cb_guiado_registrar_fixo-9b449|guiado:registrar_fixo]] act new_fixed_start
- (chama) [[fn_ux.dispatch_text-8df9e|ux.dispatch_text]] 
- (chama) [[fn_ux.dispatch_callback-a9f29|ux.dispatch_callback]] act(action)
