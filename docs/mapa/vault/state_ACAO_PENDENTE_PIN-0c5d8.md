---
tipo: state
arquivo: app.py
linha: 964
---
# ACAO_PENDENTE_PIN

dict user_id -> update bloqueado por PIN (TTL 120 s); reexecutado apos desbloqueio correto (nunca guarda o PIN)

`state:ACAO_PENDENTE_PIN`

## Vem de
- (grava_estado) [[fn_app.guardar_acao_pendente_pin-68f50|guardar_acao_pendente_pin]] 
- (le_estado) [[fn_app.reexecutar_acao_pendente_pin-28973|reexecutar_acao_pendente_pin]] 
- (grava_estado) [[fn_app.descartar_acao_pendente_pin-4ebf5|descartar_acao_pendente_pin]] 
