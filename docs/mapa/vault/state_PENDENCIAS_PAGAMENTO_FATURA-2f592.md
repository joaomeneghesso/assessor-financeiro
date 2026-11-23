---
tipo: state
arquivo: services.py
linha: 303
---
# PENDENCIAS_PAGAMENTO_FATURA

Dict global: movimento de fatura (pagamento/estorno/crédito) aguardando confirmar.

`state:PENDENCIAS_PAGAMENTO_FATURA`

## Vem de
- (grava_estado) [[fn_services._preparar_movimento_fatura_sessao-44ad5|services._preparar_movimento_fatura_sessao]] 
- (le_estado) [[fn_services.confirmar_movimento_fatura_pendente-95ee9|services.confirmar_movimento_fatura_pendente]] 
- (grava_estado) [[fn_services.cancelar_movimento_fatura_pendente-fc5da|services.cancelar_movimento_fatura_pendente]] limpa
