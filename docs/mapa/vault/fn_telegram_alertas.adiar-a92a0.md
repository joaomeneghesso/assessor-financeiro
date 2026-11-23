---
tipo: service
arquivo: telegram_alertas.py
linha: 36
---
# telegram_alertas.adiar

Soneca de 1 h: grava experiencia_soneca.

`fn:telegram_alertas.adiar`

## Vai para
- (grava_estado) [[state_db_auditoria_eventos-e3dd2|db:auditoria_eventos]] experiencia_soneca

## Vem de
- (chama) [[fn_telegram_alertas.callback-80f31|telegram_alertas.callback]] 
