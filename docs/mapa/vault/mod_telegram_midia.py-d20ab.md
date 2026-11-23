---
tipo: module
arquivo: telegram_midia.py
linha: 
---
# telegram_midia.py

Foto/áudio -> texto local (OCR/transcrição) -> prévia revisável; nunca grava sem revisão.

`mod:telegram_midia.py`

## Vai para
- (chama) [[fn_telegram_midia.receive-25423|telegram_midia.receive]] 
- (chama) [[fn_telegram_midia.review-9d355|telegram_midia.review]] 
- (chama) [[fn_telegram_midia.dispatch-fb1f2|telegram_midia.dispatch]] 
- (chama) [[fn_telegram_midia.answer-67dec|telegram_midia.answer]] 
- (chama) [[fn_services.parsear_comando_transferencia_caixa-32f04|services.parsear_comando_transferencia_caixa]] review (104)

## Vem de
- (chama) [[mod_telegram_experiencia.py-c6fa1|telegram_experiencia.py]] act 2342 -> dispatch; 1907 -> answer
