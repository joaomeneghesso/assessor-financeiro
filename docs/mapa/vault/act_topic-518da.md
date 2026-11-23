---
tipo: action
arquivo: telegram_experiencia.py
linha: 2828
---
# topic

Abre tópico de ajuda (pausa fluxo).

`act:topic`

## Vai para
- (grava_estado) [[state_Session.topic-489d3|Session.topic]] 
- (grava_estado) [[state_Session.trail-b6f1c|Session.trail]] 
- (chama) [[fn_ux._suspend_flow-76c4a|_suspend_flow]] 
- (navega) [[screen_help_topic-07999|help_topic]] 
- (chama) [[fn_ux.pause_for_guidance-482b6|pause_for_guidance]] 
- (chama) [[fn_ux.render-b3471|Experience.render]] 
- (le_estado) [[state_Session.view-a9ea1|Session.view]] 
- (le_estado) [[state_Session.month-7f614|Session.month]] 
- (le_estado) [[state_Session.page-3e7eb|Session.page]] 
- (grava_estado) [[state_Session.settings_draft-703dd|Session.settings_draft]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (le_estado) [[state_Session.draft-81d88|Session.draft]] 

## Vem de
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] /help <tema>
- (chama) [[cmd_help-8f98e|/help]] 
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_balance_details-02072|balance_details]] Como interpretar
- (navega) [[screen_data_tools-d1767|data_tools]] 🔐 Privacidade
- (navega) [[screen_help-8e6e8|help]] Começar/Registrar/Pagar/Dinheiro/Consultar/Mais
- (navega) [[screen_setup-2cfa0|setup]] Ajuda de previsões
- (navega) [[screen_command_help-4b0d8|command_help]] 📤 Exportação/🔐 Segurança
- (navega) [[screen_transaction-cd364|transaction]] Entender correções/parcelas
- (navega) [[screen_obligation-113ca|obligation]] Entender faturas
- (navega) [[act_balance_initial-82e49|balance_initial]] botão da resposta
- (navega) [[screen_help_topic-07999|help_topic]] 
