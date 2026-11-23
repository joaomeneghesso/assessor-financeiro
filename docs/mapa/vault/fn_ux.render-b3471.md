---
tipo: handler
arquivo: telegram_experiencia.py
linha: 684
---
# Experience.render

Valida s.view, chama screen_<view>(s) sob read_only_mode+contexto_consulta; adiciona ↩ Voltar (se trail) e linha de rascunho pausado.

`fn:ux.render`

## Vai para
- (grava_estado) [[state_Session.view-a9ea1|Session.view]] se view informado
- (le_estado) [[state_Session.trail-b6f1c|Session.trail]] mostra ↩ Voltar
- (grava_estado) [[state_Experience._retrato-dbb0d|Experience._retrato]] limpa no finally
- (chama) [[btn_Voltar-c2fc6|↩ Voltar]] 
- (navega) [[screen_home-111fe|home]] screen_<view>
- (navega) [[screen_more-4f9f6|more]] 

## Vem de
- (chama) [[act_view-1d8b8|view]] 
- (chama) [[act_month-43f36|month]] 
- (chama) [[act_current_month-a6e38|current_month]] 
- (chama) [[act_back-bca78|back]] 
- (chama) [[act_render_current-56ec4|render_current]] 
- (chama) [[act_page-3b059|page]] 
- (chama) [[act_filter-91736|filter]] 
- (chama) [[act_topic-518da|topic]] 
- (chama) [[act_lesson_page-69af5|lesson_page]] 
- (chama) [[act_transaction-fab7d|transaction]] 
- (chama) [[act_detail_obligation-b6e92|detail_obligation]] 
- (chama) [[act_accounts_for-fd5a1|accounts_for]] 
- (chama) [[act_ask-dbbdf|ask]] 
- (chama) [[act_help_page-6f4c1|help_page]] 
- (chama) [[act_history_basis-12c34|history_basis]] 
- (chama) [[act_home_income-c95f5|home_income]] 
- (chama) [[act_discard_and_register-b6760|discard_and_register]] 
- (chama) [[act_clear_pay_filters-3757f|clear_pay_filters]] 
- (chama) [[act_pay_account_filter-642f0|pay_account_filter]] 
- (chama) [[act_clear_filters-83f26|clear_filters]] 
- (chama) [[act_account_filter-0f866|account_filter]] 
- (chama) [[act_pref-1dd2f|pref]] 
- (chama) [[act_save_hours-ad3d6|save_hours]] 
- (chama) [[act_save_balance-8b906|save_balance]] 
- (chama) [[act_save_budget-c4116|save_budget]] 
- (chama) [[act_buy_sim-7508a|buy_sim]] 
- (chama) [[act_buy_fatura-a5396|buy_fatura]] 
- (chama) [[act_privacy-0656d|privacy]] 
- (chama) [[act_clear_search-c0a6d|clear_search]] 
- (chama) [[act_cancel-c6497|cancel]] 
- (chama) [[fn_ux._accounts_manage_notice-4b796|ux._accounts_manage_notice]] 
- (chama) [[fn_ux.act-20779|Experience.act]] 
