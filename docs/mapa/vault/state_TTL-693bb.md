---
tipo: state
arquivo: telegram_experiencia.py
linha: 59
---
# TTL

TTL=600 s: Session expira (e o mês volta ao atual) após 10 min sem toque; callbacks ux: expiram junto (resolve l.523).

`state:TTL`

## Vem de
- (le_estado) [[fn_ux.session-8e514|Experience.session]] expurga sessões > 600 s
- (le_estado) [[fn_ux.resolve-4d9fe|Experience.resolve]] 
