---
tipo: handler
arquivo: telegram_experiencia.py
linha: 1720
---
# begin_settlement

Baixa de compromisso (cria draft vinculado à previsão).

`fn:ux.begin_settlement`

## Vai para
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] 
- (chama) [[fn_conciliacao.alvo-7b858|alvo]] 

## Vem de
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 
- (chama) [[act_settle-bc62a|settle]] 
