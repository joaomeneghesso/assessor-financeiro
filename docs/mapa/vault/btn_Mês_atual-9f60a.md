---
tipo: button
arquivo: telegram_experiencia.py
linha: 
---
# Mês atual / ↩ Mês atual

("current_month",view): reseta mês ao corrente; exibido em Período e em Detalhes do mês quando mês != atual.

`btn:Mês atual`

## Vai para
- (chama) [[act_current_month-a6e38|current_month]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] mês corrente
- (navega) [[screen_home-111fe|home]] ou tela de origem (current_month,view)

## Vem de
- (navega) [[screen_month_actions-bedf6|month_actions]] ↩ Mês atual
- (navega) [[screen_period_tools-35de3|period_tools]] Mês atual
- (navega) [[act_period_tools-9b2d7|period_tools]] 
