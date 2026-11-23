---
tipo: handler
arquivo: telegram_experiencia.py
linha: 1664
---
# open_learning

Abre aula/lista de aulas (pausa fluxo).

`fn:ux.open_learning`

## Vai para
- (grava_estado) [[state_Session.lesson-d22b3|Session.lesson]] 
- (navega) [[screen_learn-155c2|learn]] 
- (navega) [[screen_lesson-90d28|lesson]] 
- (chama) [[fn_ux.pause_for_guidance-482b6|pause_for_guidance]] 

## Vem de
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 
- (chama) [[cmd_aprender-9853d|/aprender]] 
- (chama) [[act_lesson-3f7e5|lesson]] 
- (chama) [[act_view-1d8b8|view]] 
