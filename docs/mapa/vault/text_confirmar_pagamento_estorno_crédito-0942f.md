---
tipo: text_trigger
arquivo: services.py
linha: 8484
---
# confirmar pagamento|estorno|crédito

Grava o movimento de fatura previsto na prévia.

`text:confirmar pagamento|estorno|crédito`

## Vai para
- (chama) [[fn_services.confirmar_movimento_fatura_pendente-95ee9|services.confirmar_movimento_fatura_pendente]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8484
