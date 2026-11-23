---
tipo: state
arquivo: services.py
linha: 299
---
# PENDENCIAS_CONFIRMACAO

Dict global {sessão: pendência} de confirmação de lançamento (legado). Efêmero em memória.

`state:PENDENCIAS_CONFIRMACAO`

## Vem de
- (le_estado) [[fn_services.confirmar_lancamento_pendente-2b96c|services.confirmar_lancamento_pendente]] 
- (grava_estado) [[fn_services.cancelar_lancamento_pendente-41125|services.cancelar_lancamento_pendente]] limpa
