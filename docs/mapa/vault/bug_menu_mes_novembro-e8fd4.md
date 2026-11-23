---
tipo: state
arquivo: telegram_experiencia.py
linha: 4343
---
# BUG mês vaza para o Menu

Causa provável: Session.month é gravado por fast_deterministic_query (telegram_experiencia.py:3720) e _ai_query_result (l.3741) ao responder "quanto vou pagar em novembro" e nunca é restaurado. /menu (app.py:4343) e os botões ☰ Menu / 🏠 Início (act view, l.2814-2822) abrem Início no mês da sessão; só o TEXTO "menu"/"inicio"/"central" (l.2926-2935), /mes e atalhos de app.py:4468 resetam para o mês corrente. Sessão vive 600 s (TTL) e persiste em .runtime.

`bug:menu_mes_novembro`

## Vai para
- (le_estado) [[state_Session.month-7f614|Session.month]] 

## Vem de
- (grava_estado) [[fn_ux.fast_deterministic_query-fb2df|fast_deterministic_query]] origem do vazamento (l.3720)
- (grava_estado) [[fn_ux._ai_query_result-20fe1|_ai_query_result]] origem do vazamento (l.3741)
- (le_estado) [[cmd_menu-be698|/menu]] não reseta (app.py:4343)
- (le_estado) [[btn_Menu-04e55|☰ Menu]] 
- (le_estado) [[btn_Início-1bd0b|🏠 Início]] 
- (volta) [[text_menu-03529|menu]] único caminho que corrige (reset l.2935)
