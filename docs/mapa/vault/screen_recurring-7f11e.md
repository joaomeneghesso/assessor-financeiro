---
tipo: screen
arquivo: telegram_experiencia.py
linha: 3899
---
# recurring

Pagamentos que se repetem (≥3 meses).

`screen:recurring`

## Vai para
- (le_estado) [[state_Session.month-7f614|Session.month]] título/consulta usa s.month
- (chama) [[fn_orientacao.coletar-ba856|coletar]] 
- (navega) [[act_transaction-fab7d|transaction]] Revisar lançamento recente
- (navega) [[act_page-3b059|page]] ‹ Anteriores / Próximas ›
- (navega) [[fn_ux.nav-29bea|Experience.nav]] nav
- (grava_estado) [[state_Session.page-3e7eb|Session.page]] 

## Vem de
- (navega) [[screen_planning_tools-d534b|planning_tools]] 🔁 Recorrências
