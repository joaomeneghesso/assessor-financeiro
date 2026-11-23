---
tipo: text_trigger
arquivo: telegram_experiencia.py
linha: 
---
# fluxo_expirado

Resposta solta a fluxo vencido (>600 s) -> tela de recomeçar.

`text:fluxo_expirado`

## Vai para
- (chama) [[fn_ux.dispatch_text-8df9e|ux.dispatch_text]] 
- (chama) [[fn_ux._tela_fluxo_expirado-10505|ux._tela_fluxo_expirado]] 
