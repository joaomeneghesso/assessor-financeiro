---
tipo: screen
arquivo: telegram_experiencia.py
linha: 1250
---
# history

Histórico: lançamentos do mês com filtros tipo/conta/categoria/busca e base data|fatura.

`screen:history`

## Vai para
- (le_estado) [[state_Session.month-7f614|Session.month]] título/consulta usa s.month
- (chama) [[fn_ux.history_items-a4c0f|history_items]] 
- (chama) [[fn_db.buscar_transacoes_por_mes-9d185|buscar_transacoes_por_mes]] 
- (chama) [[fn_db.buscar_transacoes_por_competencia-4f076|buscar_transacoes_por_competencia]] 
- (le_estado) [[state_Session.history_filter-db2cb|Session.history_filter]] 
- (le_estado) [[state_Session.history_account_filter-0cdca|Session.history_account_filter]] 
- (le_estado) [[state_Session.history_category_filter-6f763|Session.history_category_filter]] 
- (le_estado) [[state_Session.search-c5f30|Session.search]] 
- (le_estado) [[state_Session.history_basis-93b47|Session.history_basis]] 
- (navega) [[act_transaction-fab7d|transaction]] #id · descrição
- (navega) [[act_page-3b059|page]] ‹ Anteriores / Próximos ›
- (navega) [[act_history_tools-33d2b|history_tools]] 🔎 Busca e filtros
- (navega) [[fn_ux.nav-29bea|Experience.nav]] nav
- (grava_estado) [[state_Session.page-3e7eb|Session.page]] 

## Vem de
- (navega) [[screen_more-4f9f6|more]] 🔎 Histórico
- (navega) [[screen_attention-ebc03|attention]] Ver Histórico
- (navega) [[screen_closing_details-60038|closing_details]] 🔎 Ver lançamentos
- (navega) [[screen_review-185df|review]] 🔎 Histórico
- (navega) [[screen_review_details-b6002|review_details]] Abrir histórico
- (navega) [[screen_receivables-eb894|receivables]] Abrir Histórico
- (navega) [[screen_obligation-113ca|obligation]] Procurar no Histórico / Abrir revisões
- (navega) [[fn_ux.expired_callback_screen-327bb|expired_callback_screen]] 🔎 Histórico
- (navega) [[act_filter-91736|filter]] history
- (navega) [[act_clear_filters-83f26|clear_filters]] 
- (navega) [[act_clear_search-c0a6d|clear_search]] 
- (navega) [[act_history_basis-12c34|history_basis]] 
- (navega) [[act_category-edf48|category]] 
- (navega) [[act_home_income-c95f5|home_income]] 
- (navega) [[act_account_filter-0f866|account_filter]] 
- (navega) [[act_cancel-c6497|cancel]] 
- (navega) [[screen_advanced_help-617c1|advanced_help]] 
- (navega) [[screen_transaction-cd364|transaction]] 
- (navega) [[act_busca-82b5b|busca]] 📒 Histórico do mês
