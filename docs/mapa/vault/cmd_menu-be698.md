---
tipo: command
arquivo: app.py
linha: 5611
---
# /menu

Abre Central/home e limpa pendencias

`cmd:/menu`

## Vai para
- (chama) [[fn_app.menu_command-1f10a|app.menu_command]] CommandHandler
- (chama) [[fn_telegram_experiencia.act-0d59a|telegram_experiencia.act]] app.py:4343 ('view','home')
- (le_estado) [[state_Session.month-7f614|Session.month]] tela Início usa s.month, que pode ficar de uma consulta anterior (até TTL 600 s)
- (chama) [[act_view-1d8b8|view]] view home - sem reset do mês (app.py:4343)
- (navega) [[screen_home-111fe|home]] home no mês da sessão
- (le_estado) [[bug_menu_mes_novembro-e8fd4|BUG mês vaza para o Menu]] não reseta (app.py:4343)

## Vem de
- (chama) [[handler_main-bf256|main()]] 
- (navega) [[cb_expirado-57247|botao expirado]] 
- (navega) [[fn_app.inicializar_alertas-42b78|app.inicializar_alertas]] set_my_commands: menu, atalhos, mes, registrar, pagar, historico, saldos, fechamento, atencao, help, aprender, dashboard, recursos, cancelar, bloquear
- (chama) [[cmd_start-ad3b7|/start]] sem args
