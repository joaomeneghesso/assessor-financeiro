---
tipo: state
arquivo: telegram_experiencia.py
linha: 381
---
# Session.tokens

Mapa token ux:<12 bytes urlsafe> -> ação; recriado a cada tela em tokens_for (clear!). Só vale para a última tela enviada.

`state:Session.tokens`

## Vem de
- (grava_estado) [[fn_ux.tokens_for-f67d6|Experience.tokens_for]] clear()+novos tokens
- (le_estado) [[fn_ux.resolve-4d9fe|Experience.resolve]] 
