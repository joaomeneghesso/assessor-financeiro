---
tipo: handler
arquivo: app.py
linha: 4625
---
# dashboard_command

ux chart <view>; grava session.month se /dashboard AAAA-MM

`fn:app.dashboard_command`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] 
- (grava_estado) [[state_session.month-91610|session.month]] /dashboard AAAA-MM
- (chama) [[fn_ux.run_experience-c1322|ux.run_experience]] act chart
- (exige_pin) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] 'dashboard'

## Vem de
- (chama) [[cmd_dashboard-a49b5|/dashboard]] CommandHandler
