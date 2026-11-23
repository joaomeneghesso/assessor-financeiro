---
tipo: screen
arquivo: telegram_experiencia.py
linha: 4023
---
# obligation

Detalhe de obrigação (usa o mês de origem do item).

`screen:obligation`

## Vai para
- (chama) [[fn_services.resolver_item_checklist-a2267|services.resolver_item_checklist]] 
- (chama) [[fn_services.aplicar_status_checklist-8e28a|services.aplicar_status_checklist]] 
- (le_estado) [[state_Session.selected_obligation-4fd8c|Session.selected_obligation]] 
- (navega) [[act_invoice_begin-31c3f|invoice_begin]] Registrar pagamento (fatura)
- (navega) [[act_settle-bc62a|settle]] Registrar pagamento (compromisso)
- (navega) [[screen_history-d40e7|history]] Procurar no Histórico / Abrir revisões
- (navega) [[act_legacy-00431|legacy]] Memória completa
- (navega) [[act_invoice_origin-2fa66|invoice_origin]] 🔎 De onde veio esta fatura?
- (navega) [[act_topic-518da|topic]] Entender faturas
- (navega) [[screen_pay-ee2a3|pay]] 🧾 Voltar a A pagar
- (chama) [[fn_telegram_recursos.rich_summary-daab9|telegram_recursos.rich_summary]] 
- (chama) [[fn_ux.due_label-8d089|ux.due_label]] 
- (chama) [[fn_services.item_checklist_eh_credito_individual-ab4d0|item_checklist_eh_credito_individual]] 
- (le_estado) [[state_Session.privacy-8341f|Session.privacy]] 
- (navega) [[act_view-1d8b8|view]] 
- (navega) [[act_filter-91736|filter]] 
- (navega) [[screen_reconciliations-256e3|reconciliations]] 

## Vem de
- (navega) [[act_detail_obligation-b6e92|detail_obligation]] 
