---
tipo: screen
arquivo: telegram_experiencia.py
linha: 1916
---
# receivables

A receber / entradas previstas do mês.

`screen:receivables`

## Vai para
- (le_estado) [[state_Session.month-7f614|Session.month]] título/consulta usa s.month
- (chama) [[fn_compromissos.projetar_entradas_programadas_mes-f92d7|projetar_entradas_programadas_mes]] 
- (chama) [[fn_conciliacao.alvo-7b858|alvo]] 
- (navega) [[act_settle-bc62a|settle]] Registrar recebimento #id
- (navega) [[act_page-3b059|page]] ‹ Anteriores / Próximas ›
- (navega) [[screen_history-d40e7|history]] Abrir Histórico
- (navega) [[fn_ux.nav-29bea|Experience.nav]] nav
- (grava_estado) [[state_Session.page-3e7eb|Session.page]] 
- (navega) [[act_view-1d8b8|view]] 

## Vem de
- (navega) [[screen_month_actions-bedf6|month_actions]] 💵 A receber
- (navega) [[screen_resources-d1f70|resources]] 💵 A receber
- (navega) [[screen_planning_tools-d534b|planning_tools]] 💵 A receber
- (navega) [[fn_ux.question_result-77118|question_result]] Entradas previstas
- (navega) [[act_cancel-c6497|cancel]] 
- (navega) [[screen_advanced_help-617c1|advanced_help]] 
