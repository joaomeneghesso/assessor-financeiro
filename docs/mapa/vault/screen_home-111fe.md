---
tipo: screen
arquivo: telegram_experiencia.py
linha: 731
---
# home

Início: saldo agora, reservado, a receber, fechamento; mês = s.month (l.614-635).

`screen:home`

## Vai para
- (le_estado) [[state_Session.month-7f614|Session.month]] título/consulta usa s.month
- (chama) [[fn_orientacao.coletar-ba856|coletar]] 
- (chama) [[fn_services.obter_metricas_resultado_mes-ecfb1|services.obter_metricas_resultado_mes]] 
- (le_estado) [[state_Session.privacy-8341f|Session.privacy]] 
- (navega) [[screen_register-1389d|register]] ➕ Registrar
- (navega) [[screen_pay-ee2a3|pay]] 🧾 A pagar
- (navega) [[act_cash_setup_start-c6f73|cash_setup_start]] ✏️ Ajustar saldo
- (navega) [[screen_month_actions-bedf6|month_actions]] 🔎 Detalhes
- (navega) [[btn_Menu-04e55|☰ Menu]] ☰ Menu
- (navega) [[act_privacy-0656d|privacy]] 👁 Mostrar/◉ Ocultar
- (chama) [[fn_ux.obligations-15fc7|obligations]] 
- (chama) [[fn_saldo_resumo.resumir_saldo-111a2|saldo_resumo.resumir_saldo]] 
- (chama) [[fn_ux._linhas_receber_herdado-baa3e|ux._linhas_receber_herdado]] 
- (chama) [[fn_ux._hoje_linha-7e88c|ux._hoje_linha]] 
- (navega) [[act_view-1d8b8|view]] 
- (navega) [[act_month-43f36|month]] 
- (navega) [[act_current_month-a6e38|current_month]] 
- (navega) [[screen_more-4f9f6|more]] 

## Vem de
- (navega) [[cmd_menu-be698|/menu]] home no mês da sessão
- (navega) [[btn_Início-1bd0b|🏠 Início]] 
- (navega) [[screen_more-4f9f6|more]] 🏠 Início
- (navega) [[screen_feature_guide-3fc8e|feature_guide]] 🏠 Início
- (navega) [[screen_month_actions-bedf6|month_actions]] ↻ Atualizar
- (navega) [[screen_attention-ebc03|attention]] 🏠 Meu mês
- (navega) [[screen_register-1389d|register]] 🏠 Início
- (navega) [[screen_resources-d1f70|resources]] 🏠 Início
- (navega) [[screen_planning_tools-d534b|planning_tools]] 🏠 Início
- (navega) [[screen_review_tools-cb4c3|review_tools]] 🏠 Início
- (navega) [[screen_data_tools-d1767|data_tools]] 🏠 Início
- (navega) [[screen_category_rules-91f55|category_rules]] 🏠 Início
- (navega) [[screen_help-8e6e8|help]] 🏠 Início
- (navega) [[screen_learn-155c2|learn]] 🏠 Início
- (navega) [[screen_plan-adfe6|plan]] N. Abrir próximo passo
- (navega) [[screen_assistant-c05b6|assistant]] 🏠 Início
- (navega) [[screen_setup-2cfa0|setup]] 🏠 Início
- (navega) [[screen_help_topic-07999|help_topic]] 🏠 Início
- (navega) [[screen_command_help-4b0d8|command_help]] 🏠 Início
- (navega) [[screen_advanced_help-617c1|advanced_help]] 🏠 Início
- (navega) [[screen_pay_month_account_detail-15b60|pay_month_account_detail]] 🏠 Início
- (navega) [[screen_pay_account-46888|pay_account]] 🏠 Início
- (navega) [[screen_cash_accounts-cc984|cash_accounts]] 🏠 Início
- (navega) [[screen_cash_account_detail-b41d6|cash_account_detail]] 🏠 Início
- (navega) [[screen_balance_account-fac81|balance_account]] 🏠 Início
- (navega) [[screen_dashboard-6ba51|dashboard]] Abrir detalhes
- (navega) [[fn_ux.expired_callback_screen-327bb|expired_callback_screen]] 🏠 Início
- (navega) [[fn_ux.question_result-77118|question_result]] 🏠 Início
- (navega) [[act_privacy-0656d|privacy]] 
- (navega) [[act_reconcile_baseline_commit-6bad7|reconcile_baseline_commit]] 
- (navega) [[act_new_fixed_cancel-e16bb|new_fixed_cancel]] 
- (navega) [[act_disabled-6cffe|disabled]] 
- (navega) [[fn_ux.render-b3471|Experience.render]] screen_<view>
- (navega) [[btn_Mês_atual-9f60a|Mês atual / ↩ Mês atual]] ou tela de origem (current_month,view)
- (navega) [[act_month-43f36|month]] tela action[2]
- (navega) [[act_current_month-a6e38|current_month]] tela action[1]
- (navega) [[screen_closing_details-60038|closing_details]] 
- (navega) [[screen_accounts_manage-5980c|accounts_manage]] 
- (navega) [[screen_can_buy-e0e39|can_buy]] 
- (navega) [[screen_accounts-cc0c6|accounts]] 
