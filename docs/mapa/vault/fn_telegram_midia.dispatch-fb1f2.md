---
tipo: service
arquivo: telegram_midia.py
linha: 170
---
# telegram_midia.dispatch

Ações media_kind/media_edit/media_transfer_*; 'media_transfer_commit' grava transferência; despesas/entradas viram rascunho UX2.

`fn:telegram_midia.dispatch`

## Vai para
- (le_estado) [[state_Session.media_review-1b659|Session.media_review]] 
- (chama) [[fn_telegram_midia._draft_from_media-fe37a|telegram_midia._draft_from_media]] 
- (chama) [[fn_database.inserir_transferencia_caixa-d62ec|database.inserir_transferencia_caixa]] 197 (media_transfer_commit)
- (navega) [[fn_telegram_experiencia._advance_registration-7c204|telegram_experiencia._advance_registration]] 217: vai ao fluxo guiado com confirmação

## Vem de
- (chama) [[mod_telegram_midia.py-d20ab|telegram_midia.py]] 
- (chama) [[act_media_kind-6fe72|media_kind]] 
- (chama) [[act_media_continue-7fe1f|media_continue]] 
- (chama) [[act_media_edit-32d4c|media_edit]] 
- (chama) [[act_media_transfer_edit-ef319|media_transfer_edit]] 
- (chama) [[act_media_transfer_back-94ae2|media_transfer_back]] 
- (chama) [[act_media_transfer_field-85203|media_transfer_field]] 
- (chama) [[act_media_transfer_commit-20617|media_transfer_commit]] 
