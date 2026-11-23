---
tipo: action
arquivo: telegram_experiencia.py
linha: 2924
---
# home_income

Entradas do mês: filtra Histórico por receita (empilha trail).

`act:home_income`

## Vai para
- (grava_estado) [[state_Session.history_filter-db2cb|Session.history_filter]] receita
- (grava_estado) [[state_Session.trail-b6f1c|Session.trail]] 
- (navega) [[screen_history-d40e7|history]] 
- (grava_estado) [[state_Session.history_account_filter-0cdca|Session.history_account_filter]] 
- (grava_estado) [[state_Session.history_category_filter-6f763|Session.history_category_filter]] 
- (grava_estado) [[state_Session.search-c5f30|Session.search]] 
- (grava_estado) [[state_Session.page-3e7eb|Session.page]] 
- (chama) [[fn_ux.render-b3471|Experience.render]] 
- (le_estado) [[state_Session.view-a9ea1|Session.view]] 
- (le_estado) [[state_Session.month-7f614|Session.month]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_month_actions-bedf6|month_actions]] 📥 Entradas do mês
