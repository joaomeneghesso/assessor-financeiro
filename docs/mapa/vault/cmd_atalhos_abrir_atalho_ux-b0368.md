---
tipo: handler
arquivo: app.py
linha: 
---
# /pagar /historico /saldos /fechamento /atencao /recursos

app.py:4460 abrir_atalho_ux: reseta Session.month ao corrente e abre a tela (ou cash_accounts).

`cmd:atalhos_abrir_atalho_ux`

## Vai para
- (grava_estado) [[state_Session.month-7f614|Session.month]] app.py:4468 reseta ao corrente
- (chama) [[act_view-1d8b8|view]] 
- (chama) [[act_cash_accounts-a48cb|cash_accounts]] 

## Vem de
- (chama) [[cmd_mes-c68e2|/mes]] 
