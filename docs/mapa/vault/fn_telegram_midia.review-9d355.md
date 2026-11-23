---
tipo: service
arquivo: telegram_midia.py
linha: 93
---
# telegram_midia.review

Monta tela de revisão (despesa/entrada/fatura/transferência) a partir do texto; grava s.media_review.

`fn:telegram_midia.review`

## Vai para
- (chama) [[fn_telegram_midia.receipt_fields-e0eb3|telegram_midia.receipt_fields]] 
- (chama) [[fn_telegram_midia.audio_kind_hint-23262|telegram_midia.audio_kind_hint]] 
- (chama) [[fn_services.parsear_comando_transferencia_caixa-32f04|services.parsear_comando_transferencia_caixa]] 104
- (chama) [[fn_registro_conversa.extrair_campos-776ac|registro_conversa.extrair_campos]] 109
- (grava_estado) [[state_Session.media_review-1b659|Session.media_review]] 115

## Vem de
- (chama) [[mod_telegram_midia.py-d20ab|telegram_midia.py]] 
- (chama) [[fn_telegram_midia.receive-25423|telegram_midia.receive]] 281
