---
tipo: text_trigger
arquivo: services.py
linha: 8489
---
# cancelar pagamento|estorno|crédito

Descarta o movimento de fatura pendente.

`text:cancelar pagamento|estorno|crédito`

## Vai para
- (chama) [[fn_services.cancelar_movimento_fatura_pendente-fc5da|services.cancelar_movimento_fatura_pendente]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8489
