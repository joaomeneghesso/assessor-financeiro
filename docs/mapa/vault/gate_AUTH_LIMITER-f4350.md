---
tipo: security_gate
arquivo: app.py
linha: 66
---
# AUTH_LIMITER

Limitador de tentativas de PIN; na subida real do bot e trocado por LimitadorPersistente (.runtime/auth_limiter.bin, DPAPI)

`gate:AUTH_LIMITER`

## Vai para
- (le_estado) [[state_AUTH_LIMITER-e62f8|AUTH_LIMITER]] 

## Vem de
- (chama) [[text_desbloquear_pin-3c305|desbloquear <pin>]] 
- (chama) [[cb_pin_pair_i-32cd9|pin_pair:<i>]] 
