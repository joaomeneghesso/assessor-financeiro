---
tipo: state
arquivo: app.py
linha: 63
---
# SESSOES_SEGURANCA

dict user_id -> {desbloqueado, ultimo acesso} da camada PIN

`state:SESSOES_SEGURANCA`

## Vem de
- (le_estado) [[gate_autolock-026e9|assessor_esta_desbloqueado]] 
- (grava_estado) [[fn_app.bloquear_command-58dbc|bloquear_command]] bloqueia
- (grava_estado) [[text_bloquear-31a41|bloquear]] 
- (grava_estado) [[text_desbloquear_pin-3c305|desbloquear <pin>]] desbloqueia
- (grava_estado) [[cb_pin_pair_i-32cd9|pin_pair:<i>]] desbloqueia
- (grava_estado) [[cb___bloquear-20806|__bloquear__]] 
