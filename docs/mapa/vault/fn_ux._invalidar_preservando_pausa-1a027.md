---
tipo: handler
arquivo: telegram_experiencia.py
linha: 4936
---
# _invalidar_preservando_pausa

EXPERIENCE.invalidate (apaga Session inteira, incl. mês) preservando rascunho pausado; usado por comando operacional.

`fn:ux._invalidar_preservando_pausa`

## Vai para
- (grava_estado) [[state_Experience.sessions-934fe|Experience.sessions]] apaga Session (mês volta ao corrente)

## Vem de
- (chama) [[fn_ux.dispatch_text-8df9e|ux.dispatch_text]] comando operacional
