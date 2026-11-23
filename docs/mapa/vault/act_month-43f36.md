---
tipo: action
arquivo: telegram_experiencia.py
linha: 3347
---
# month

Mês anterior/próximo (±1) e re-render da tela indicada.

`act:month`

## Vai para
- (grava_estado) [[state_Session.month-7f614|Session.month]] month_shift(±1) l.2823
- (grava_estado) [[state_Session.page-3e7eb|Session.page]] 
- (chama) [[fn_ux.render-b3471|Experience.render]] 
- (navega) [[screen_home-111fe|home]] tela action[2]

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (chama) [[btn_Mês_anterior-c7670|‹ Mês anterior]] 
- (chama) [[btn_Próximo_mês-62aa3|Próximo mês ›]] 
- (navega) [[act_period_tools-9b2d7|period_tools]] botão da resposta
- (navega) [[screen_home-111fe|home]] 
- (navega) [[screen_month_actions-bedf6|month_actions]] 
