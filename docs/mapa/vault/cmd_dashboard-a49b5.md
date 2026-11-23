---
tipo: command
arquivo: app.py
linha: 5608
---
# /dashboard

ux chart <view>; grava session.month se /dashboard AAAA-MM

`cmd:/dashboard`

## Vai para
- (chama) [[fn_app.dashboard_command-1e8d5|dashboard_command]] CommandHandler
- (chama) [[fn_ux.dashboard_route-5394c|dashboard_route]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] só com período (app.py:4428)
- (chama) [[act_chart-efa97|chart]] 

## Vem de
- (chama) [[handler_main-bf256|main()]] 
