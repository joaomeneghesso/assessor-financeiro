---
tipo: action
arquivo: telegram_experiencia.py
linha: 2923
---
# render_current

Re-renderiza a tela atual (s.view) sem mexer no mês.

`act:render_current`

## Vai para
- (chama) [[fn_ux.render-b3471|Experience.render]] 
- (le_estado) [[state_Session.view-a9ea1|Session.view]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_pay_tools-19539|pay_tools]] ← Voltar a A pagar
- (navega) [[screen_history_tools-cc0f8|history_tools]] ← Voltar ao Histórico
- (navega) [[screen_period_tools-35de3|period_tools]] ↻ Atualizar
- (navega) [[act_period_tools-9b2d7|period_tools]] botão da resposta
- (chama) [[fn_ux._pay_tools_screen-7fc89|_pay_tools_screen]] 
- (chama) [[fn_ux._history_tools_screen-c950e|_history_tools_screen]] 
