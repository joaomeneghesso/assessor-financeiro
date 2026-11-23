---
tipo: service
arquivo: services.py
linha: 7933
---
# services.cancelar_movimento_fatura_pendente

Função de negócio (destino de roteamento).

`fn:services.cancelar_movimento_fatura_pendente`

## Vai para
- (grava_estado) [[state_PENDENCIAS_PAGAMENTO_FATURA-2f592|PENDENCIAS_PAGAMENTO_FATURA]] limpa

## Vem de
- (chama) [[text_cancelar_pagamento_estorno_crédito-bc911|cancelar pagamento|estorno|crédito]] 
