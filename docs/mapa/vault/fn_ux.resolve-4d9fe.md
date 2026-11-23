---
tipo: handler
arquivo: telegram_experiencia.py
linha: 575
---
# Experience.resolve

Resolve token -> ação; None se sessão expirou (>TTL) ou token não é da última tela.

`fn:ux.resolve`

## Vai para
- (le_estado) [[state_Session.tokens-0998e|Session.tokens]] 
- (le_estado) [[state_TTL-693bb|TTL]] 

## Vem de
- (chama) [[fn_ux.dispatch_callback-a9f29|ux.dispatch_callback]] ux:<token> -> ação
