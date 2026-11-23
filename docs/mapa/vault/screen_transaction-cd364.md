---
tipo: screen
arquivo: telegram_experiencia.py
linha: 3995
---
# transaction

Detalhe do lançamento #id.

`screen:transaction`

## Vai para
- (chama) [[fn_conciliacao.listar_vinculos-ca122|listar_vinculos]] 
- (chama) [[fn_db.buscar_transacao_por_id-d0e04|buscar_transacao_por_id]] 
- (le_estado) [[state_Session.selected_id-f42af|Session.selected_id]] 
- (navega) [[act_copy_text-219aa|copy_text]] 📋 Copiar referência
- (navega) [[act_repeat-a98e8|repeat]] Repetir como novo registro
- (navega) [[act_link_existing-2737a|link_existing]] Vincular a previsão
- (navega) [[screen_reconciliations-256e3|reconciliations]] Ver conciliação
- (navega) [[act_guided-cf3e7|guided]] Corrigir categoria/valor
- (navega) [[act_legacy-00431|legacy]] Outros ajustes
- (navega) [[act_topic-518da|topic]] Entender correções/parcelas
- (chama) [[fn_telegram_registros.evento_registro_recente-3aace|telegram_registros.evento_registro_recente]] 
- (le_estado) [[state_Session.owner-41459|Session.owner]] 
- (navega) [[act_undo_preview-52def|undo_preview]] 
- (navega) [[act_cat_menu-e3fc1|cat_menu]] 
- (navega) [[act_date_menu-7448e|date_menu]] 
- (navega) [[act_legacy_raw-2e265|legacy_raw]] 
- (navega) [[act_view-1d8b8|view]] 
- (navega) [[screen_history-d40e7|history]] 

## Vem de
- (navega) [[act_transaction-fab7d|transaction]] 
- (navega) [[act_busca-82b5b|busca]] N. lançamento
