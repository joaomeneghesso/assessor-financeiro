---
tipo: state
arquivo: telegram_experiencia.py
linha: 433
---
# Session.persist

Persistência ProtectedJsonStore (.runtime/telegram_sessions.bin, DPAPI): salva todas as Session ativas; restaurada no boot se < TTL (l.393-431). Faz o mês sobreviver a restart.

`state:Session.persist`

## Vem de
- (grava_estado) [[fn_ux.run_experience-c1322|ux.run_experience]] 
- (grava_estado) [[fn_ux.send_screen-6d6ac|send_screen]] 
- (grava_estado) [[fn_ux.Experience-49638|Experience]] 
