---
tipo: action
arquivo: telegram_experiencia.py
linha: 3348
---
# current_month

Volta ao mês atual e re-render.

`act:current_month`

## Vai para
- (grava_estado) [[state_Session.month-7f614|Session.month]] mês corrente l.2824
- (grava_estado) [[state_Session.page-3e7eb|Session.page]] 
- (chama) [[fn_ux.render-b3471|Experience.render]] 
- (navega) [[screen_home-111fe|home]] tela action[1]

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (chama) [[btn_Mês_atual-9f60a|Mês atual / ↩ Mês atual]] 
- (navega) [[act_period_tools-9b2d7|period_tools]] botão da resposta
- (navega) [[screen_home-111fe|home]] 
- (navega) [[screen_month_actions-bedf6|month_actions]] 
