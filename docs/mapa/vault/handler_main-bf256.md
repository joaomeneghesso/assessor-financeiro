---
tipo: handler
arquivo: app.py
linha: 5577
---
# main()

Valida seguranca, verifica banco, init_db, trava de instancia, limitador persistente, registra handlers, run_polling

`handler:main`

## Vai para
- (chama) [[handler_CallbackQueryHandler-4ad8f|CallbackQueryHandler(callback_submenu)]] 
- (chama) [[handler_MessageHandler.text-d92c9|MessageHandler(TEXT & ~COMMAND)]] 
- (chama) [[handler_MessageHandler.media-84332|MessageHandler(VOICE|AUDIO|PHOTO)]] 
- (chama) [[cmd_start-ad3b7|/start]] 
- (chama) [[cmd_help-8f98e|/help]] 
- (chama) [[cmd_mes-c68e2|/mes]] 
- (chama) [[cmd_registrar-e1453|/registrar]] 
- (chama) [[cmd_pagar-2cad9|/pagar]] 
- (chama) [[cmd_historico-7c809|/historico]] 
- (chama) [[cmd_saldos-983af|/saldos]] 
- (chama) [[cmd_fechamento-91459|/fechamento]] 
- (chama) [[cmd_atencao-91288|/atencao]] 
- (chama) [[cmd_aprender-9853d|/aprender]] 
- (chama) [[cmd_dashboard-a49b5|/dashboard]] 
- (chama) [[cmd_recursos-2721a|/recursos]] 
- (chama) [[cmd_topicos-6a34a|/topicos]] 
- (chama) [[cmd_menu-be698|/menu]] 
- (chama) [[cmd_atalhos-bf841|/atalhos]] 
- (chama) [[cmd_cancelar-18e66|/cancelar]] 
- (chama) [[cmd_limpar-95d87|/limpar]] 
- (chama) [[cmd_clear-91068|/clear]] 
- (chama) [[cmd_seguranca-97c12|/seguranca]] 
- (chama) [[cmd_bloquear-80413|/bloquear]] 
- (chama) [[cmd_desbloquear-a195b|/desbloquear]] 
- (chama) [[cmd_esqueci_pin-498c9|/esqueci_pin]] 
- (chama) [[cmd_reset-e7bdc|/reset]] 
- (chama) [[cmd_resetarpin-60ca1|/resetarpin]] 
- (chama) [[cmd_meuid-1259a|/meuid]] 
- (agenda) [[fn_app.inicializar_alertas-42b78|app.inicializar_alertas]] post_init
- (chama) [[fn_app.validar_configuracao_seguranca-24d4a|validar_configuracao_seguranca]] 
- (chama) [[fn_app.ativar_limitador_persistente-7c987|ativar_limitador_persistente]] 
- (chama) [[fn_app.avisar_erro_ao_titular-f3533|avisar_erro_ao_titular]] add_error_handler
