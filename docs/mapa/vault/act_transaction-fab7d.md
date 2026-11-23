---
tipo: action
arquivo: telegram_experiencia.py
linha: 2892
---
# transaction

Abre detalhe de lançamento.

`act:transaction`

## Vai para
- (grava_estado) [[state_Session.selected_id-f42af|Session.selected_id]] 
- (grava_estado) [[state_Session.trail-b6f1c|Session.trail]] 
- (navega) [[screen_transaction-cd364|transaction]] 
- (le_estado) [[state_Session.view-a9ea1|Session.view]] 
- (le_estado) [[state_Session.month-7f614|Session.month]] 
- (le_estado) [[state_Session.page-3e7eb|Session.page]] 
- (chama) [[fn_ux.render-b3471|Experience.render]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (grava_estado) [[state_Session.settings_draft-703dd|Session.settings_draft]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_history-d40e7|history]] #id · descrição
- (navega) [[screen_recurring-7f11e|recurring]] Revisar lançamento recente
- (navega) [[act_cat_preview-76b38|cat_preview]] botão da resposta
- (navega) [[act_cat_confirm-ff9ed|cat_confirm]] botão da resposta
- (navega) [[act_cat_learn-63acd|cat_learn]] botão da resposta
- (navega) [[act_date_type-a560a|date_type]] botão da resposta
- (navega) [[act_date_confirm-130a2|date_confirm]] botão da resposta
- (chama) [[fn_ux._categoria_menu-09adc|ux._categoria_menu]] 
- (chama) [[fn_ux._data_menu-cf2f5|ux._data_menu]] 
- (chama) [[fn_ux._data_previa-2934f|ux._data_previa]] 
