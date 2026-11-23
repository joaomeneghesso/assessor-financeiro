---
tipo: action
arquivo: telegram_experiencia.py
linha: 3188
---
# chart

Dashboard/painel em PNG (home/history/pay/balance/budgets/analytics/evolution/diagnosis).

`act:chart`

## Vai para
- (navega) [[screen_dashboard-6ba51|dashboard]] 
- (chama) [[fn_ux.pause_for_guidance-482b6|pause_for_guidance]] 
- (le_estado) [[state_Session.month-7f614|Session.month]] 
- (chama) [[fn_orientacao.coletar-ba856|coletar]] 
- (chama) [[fn_dashboard_metricas.enriquecer-42163|dashboard_metricas.enriquecer]] 
- (le_estado) [[state_Session.privacy-8341f|Session.privacy]] 
- (volta) [[fn_ux.dispatch_callback-a9f29|ux.dispatch_callback]] envia foto
- (chama) [[fn_ux._draft_pause_row-e966d|ux._draft_pause_row]] 
- (chama) [[fn_db.read_only_mode-088bd|db.read_only_mode]] 
- (chama) [[fn_saldo_resumo.resumir_saldo-111a2|saldo_resumo.resumir_saldo]] 
- (chama) [[fn_ux.history_items-a4c0f|history_items]] 
- (le_estado) [[state_Session.learning_stage-1e8f0|Session.learning_stage]] 
- (le_estado) [[state_Session.fixed_edit-92b26|Session.fixed_edit]] 
- (le_estado) [[state_Session.new_fixed-b5c04|Session.new_fixed]] 
- (le_estado) [[state_Session.search-c5f30|Session.search]] 
- (le_estado) [[state_Session.history_category_filter-6f763|Session.history_category_filter]] 
- (le_estado) [[state_Session.history_account_filter-0cdca|Session.history_account_filter]] 
- (le_estado) [[state_Session.history_filter-db2cb|Session.history_filter]] 
- (navega) [[act_view-1d8b8|view]] botão da resposta
- (navega) [[act_dashboard_month-21b8f|dashboard_month]] botão da resposta
- (navega) [[act_origin-c0e35|origin]] botão da resposta
- (navega) [[act_learning_resume-96135|learning_resume]] botão da resposta

## Vem de
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] dashboard_route
- (chama) [[cmd_dashboard-a49b5|/dashboard]] 
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_month_actions-bedf6|month_actions]] 🖼 Painel visual
- (navega) [[screen_balance_details-02072|balance_details]] Ver gráfico
- (navega) [[screen_pay_tools-19539|pay_tools]] Ver painel visual
- (navega) [[screen_history_tools-cc0f8|history_tools]] Resumo visual
- (navega) [[screen_analytics-4bd00|analytics]] 📊 Gráfico
- (navega) [[screen_budgets-b41b9|budgets]] Ver gráfico
- (navega) [[screen_review_tools-cb4c3|review_tools]] 📊 Painel visual
- (navega) [[screen_dashboard-6ba51|dashboard]] 📊 Visão do mês / 📈 Evolução / 🔎 Diagnóstico / 🏷 Gastos / 🧾 A pagar / 🎯 Limites
- (chama) [[act_dashboard_month-21b8f|dashboard_month]] após s.month±1
- (chama) [[fn_ux._pay_tools_screen-7fc89|_pay_tools_screen]] 
- (chama) [[fn_ux._history_tools_screen-c950e|_history_tools_screen]] 
