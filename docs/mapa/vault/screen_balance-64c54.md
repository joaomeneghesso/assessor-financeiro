---
tipo: screen
arquivo: telegram_experiencia.py
linha: 1018
---
# balance

Saldo: agora, a receber, reservas, previsto no fim do mês.

`screen:balance`

## Vai para
- (le_estado) [[state_Session.month-7f614|Session.month]] título/consulta usa s.month
- (chama) [[fn_services.obter_metricas_resultado_mes-ecfb1|services.obter_metricas_resultado_mes]] 
- (navega) [[act_cash_setup_start-c6f73|cash_setup_start]] ✏️ Ajustar saldo
- (navega) [[act_cash_accounts-a48cb|cash_accounts]] 🏦 Por conta
- (navega) [[act_origin-c0e35|origin]] 🔎 Origem do saldo
- (navega) [[screen_balance_details-02072|balance_details]] 🔎 Ver cálculo
- (navega) [[fn_ux.nav-29bea|Experience.nav]] nav
- (chama) [[fn_saldo_resumo.resumir_saldo-111a2|saldo_resumo.resumir_saldo]] 
- (chama) [[fn_ux._visible-88397|ux._visible]] 
- (chama) [[fn_ux._linhas_receber_herdado-baa3e|ux._linhas_receber_herdado]] 
- (navega) [[act_view-1d8b8|view]] 

## Vem de
- (navega) [[screen_more-4f9f6|more]] 💰 Saldo
- (navega) [[screen_month_actions-bedf6|month_actions]] 💰 Entender o saldo
- (navega) [[screen_attention-ebc03|attention]] Resolver/conferir
- (navega) [[screen_balance_details-02072|balance_details]] ← Saldo
- (navega) [[screen_review_tools-cb4c3|review_tools]] 💰 Entender saldo
- (navega) [[screen_setup-2cfa0|setup]] Entender o saldo
- (navega) [[fn_ux.question_result-77118|question_result]] Ver meu saldo
- (navega) [[act_save_balance-8b906|save_balance]] 
- (navega) [[act_cancel-c6497|cancel]] 
- (navega) [[screen_advanced_help-617c1|advanced_help]] 
