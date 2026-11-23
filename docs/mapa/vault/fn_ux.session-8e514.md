---
tipo: handler
arquivo: telegram_experiencia.py
linha: 488
---
# Experience.session

Obtém/cria Session; novo => month = date_provider() atual; expurga expiradas; renova touched.

`fn:ux.session`

## Vai para
- (grava_estado) [[state_Session.month-7f614|Session.month]] nova Session: month = date_provider() (l.460)
- (le_estado) [[state_TTL-693bb|TTL]] expurga sessões > 600 s
- (le_estado) [[state_Experience.sessions-934fe|Experience.sessions]] 

## Vem de
- (chama) [[fn_ux.Experience-49638|Experience]] 
- (chama) [[fn_ux.session_key-714ba|session_key]] 
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 
