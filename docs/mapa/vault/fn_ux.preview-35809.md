---
tipo: handler
arquivo: telegram_experiencia.py
linha: 2388
---
# preview

Prévia/confirmação do registro (Salvar/Editar/Relacionar/Simular).

`fn:ux.preview`

## Vai para
- (chama) [[fn_db.buscar_transacoes_por_mes-9d185|buscar_transacoes_por_mes]] 
- (chama) [[fn_conciliacao.alvo-7b858|alvo]] 
- (chama) [[fn_services.obter_metricas_resultado_mes-ecfb1|services.obter_metricas_resultado_mes]] 
- (le_estado) [[state_Session.draft-81d88|Session.draft]] 
- (navega) [[act_commit-ada76|commit]] ✅ Salvar despesa/entrada
- (navega) [[act_edit_menu-ff828|edit_menu]] ✏️ Editar dados
- (navega) [[act_installment_schedule-2acd8|installment_schedule]] 📅 Ver parcelas
- (navega) [[act_pick_target-407d8|pick_target]] 🔗 Relacionar a uma previsão
- (navega) [[act_commit_link-b8e95|commit_link]] Confirmar vínculo
- (navega) [[act_keep_separate-a37e9|keep_separate]] É outra operação; manter separado
- (navega) [[act_simulate_variant-afc9e|simulate_variant]] À vista/3x/6x (simulação)
- (navega) [[act_start-ebd45|start]] Nova simulação
- (navega) [[act_cancel-c6497|cancel]] Cancelar
- (chama) [[fn_ux._registration_stage-7351f|ux._registration_stage]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (chama) [[fn_ux.prompt-41177|prompt]] 
- (chama) [[fn_telegram_registros.validar_transacao-8ba78|telegram_registros.validar_transacao]] 
- (chama) [[fn_db.read_only_mode-088bd|db.read_only_mode]] 
- (chama) [[fn_ux._aviso_saldo_negativo-0fdcc|ux._aviso_saldo_negativo]] 
- (chama) [[fn_contas_inativas.esta_inativa-72d78|contas_inativas.esta_inativa]] 
- (chama) [[fn_ux.simulation_details-e3554|ux.simulation_details]] 
- (chama) [[fn_ux.payload-2099f|ux.payload]] 
- (chama) [[fn_telegram_registros.buscar_duplicata-f51a5|telegram_registros.buscar_duplicata]] 
- (chama) [[act_edit-7bceb|edit]] 
- (chama) [[act_view-1d8b8|view]] 
- (chama) [[act_dup_view-7ad35|dup_view]] 

## Vem de
- (navega) [[act_preview-5365c|preview]] 
- (chama) [[act_flow_resume-b920b|flow_resume]] 
- (navega) [[act_simulate_variant-afc9e|simulate_variant]] 
- (navega) [[act_choose_target-6f13c|choose_target]] 
- (navega) [[act_settle-bc62a|settle]] 
- (navega) [[act_repeat-a98e8|repeat]] 
- (navega) [[fn_ux.answer-a52eb|answer]] 
- (navega) [[fn_ux.parse_draft-0ebfb|parse_draft]] 
- (chama) [[act_back_step-afc43|back_step]] 
- (chama) [[act_conflict_keep-95a36|conflict_keep]] 
- (chama) [[act_dup_back-8d8c0|dup_back]] 
- (chama) [[fn_ux.installment_schedule-6e2cc|installment_schedule]] 
