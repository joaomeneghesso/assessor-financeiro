---
tipo: handler
arquivo: app.py
linha: 5490
---
# app.inicializar_alertas

post_init: set_my_commands, descricao, menu button; agenda rotina_backup_diario e, se houver destino, telegram_alertas.rotina

`fn:app.inicializar_alertas`

## Vai para
- (agenda) [[job_rotina_backup_diario-a6f56|rotina_backup_diario]] criar_tarefa_monitorada (tarefa de fundo)
- (agenda) [[job_telegram_alertas.rotina-da520|telegram_alertas.rotina]] se obter_chat_id_alertas()
- (navega) [[cmd_menu-be698|/menu]] set_my_commands: menu, atalhos, mes, registrar, pagar, historico, saldos, fechamento, atencao, help, aprender, dashboard, recursos, cancelar, bloquear

## Vem de
- (agenda) [[handler_main-bf256|main()]] post_init
