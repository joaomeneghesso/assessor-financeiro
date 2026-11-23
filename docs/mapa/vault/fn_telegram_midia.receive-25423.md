---
tipo: handler
arquivo: telegram_midia.py
linha: 247
---
# telegram_midia.receive

telegram_midia: foto/audio/OCR (sempre com revisao)

`fn:telegram_midia.receive`

## Vai para
- (chama) [[fn_telegram_midia.reconhecer_foto-8734c|telegram_midia.reconhecer_foto]] 273
- (chama) [[fn_transcricao_audio.transcrever_audio-a44a2|transcricao_audio.transcrever_audio]] 276
- (chama) [[fn_telegram_midia.review-9d355|telegram_midia.review]] 281
- (grava_estado) [[state_Session.media_review-1b659|Session.media_review]] 

## Vem de
- (chama) [[fn_app.receber_midia-88fae|receber_midia]] 
- (chama) [[mod_telegram_midia.py-d20ab|telegram_midia.py]] 
- (chama) [[mod_app.py-57fef|app.py]] app.py:4385 receber_midia (handler de voice/audio/photo)
