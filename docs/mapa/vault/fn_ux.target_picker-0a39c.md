---
tipo: handler
arquivo: telegram_experiencia.py
linha: 1891
---
# target_picker

Escolha da previsão a relacionar, com ‹Mês anterior/Próximo mês › (target_month).

`fn:ux.target_picker`

## Vai para
- (le_estado) [[state_Session.month-7f614|Session.month]] título/consulta usa s.month
- (chama) [[fn_db.listar_compromissos-77786|listar_compromissos]] 
- (chama) [[fn_conciliacao.alvo-7b858|alvo]] 
- (le_estado) [[state_Session.draft-81d88|Session.draft]] 
- (le_estado) [[state_Session.target_page-6e2a0|Session.target_page]] 
- (navega) [[act_choose_target-6f13c|choose_target]] Selecionar #id
- (navega) [[act_target_page-35f9c|target_page]] ‹ Previsões / Mais previsões ›
- (navega) [[act_target_month-a6608|target_month]] ‹ Mês anterior / Próximo mês ›
- (navega) [[act_preview-5365c|preview]] Voltar à prévia
- (navega) [[act_cancel-c6497|cancel]] Cancelar
- (chama) [[act_pick_target_page-e5b06|pick_target_page]] 

## Vem de
- (chama) [[act_pick_target-407d8|pick_target]] 
- (chama) [[act_target_month-a6608|target_month]] 
- (navega) [[act_target_page-35f9c|target_page]] 
- (navega) [[act_pick_target_page-e5b06|pick_target_page]] 
- (navega) [[act_link_existing-2737a|link_existing]] 
