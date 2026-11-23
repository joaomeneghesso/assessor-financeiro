---
tipo: handler
arquivo: app.py
linha: 4599
---
# meuid_command

Mostra dados do Telegram (exige gate de PIN so se acao sensivel; nao e)

`fn:app.meuid_command`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (exige_pin) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] '/meuid' (nunca exige)

## Vem de
- (chama) [[cmd_meuid-1259a|/meuid]] CommandHandler
