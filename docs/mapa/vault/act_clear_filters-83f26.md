---
tipo: action
arquivo: telegram_experiencia.py
linha: 3010
---
# clear_filters

Zera filtros do Histórico.

`act:clear_filters`

## Vai para
- (grava_estado) [[state_Session.history_filter-db2cb|Session.history_filter]] 
- (grava_estado) [[state_Session.history_account_filter-0cdca|Session.history_account_filter]] 
- (grava_estado) [[state_Session.history_category_filter-6f763|Session.history_category_filter]] 
- (grava_estado) [[state_Session.search-c5f30|Session.search]] 
- (navega) [[screen_history-d40e7|history]] 
- (grava_estado) [[state_Session.page-3e7eb|Session.page]] 
- (chama) [[fn_ux.render-b3471|Experience.render]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_history_tools-cc0f8|history_tools]] Limpar filtros
- (chama) [[fn_ux._history_tools_screen-c950e|_history_tools_screen]] 
