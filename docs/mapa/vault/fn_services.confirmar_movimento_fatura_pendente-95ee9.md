---
tipo: service
arquivo: services.py
linha: 7913
---
# services.confirmar_movimento_fatura_pendente

Função de negócio (destino de roteamento).

`fn:services.confirmar_movimento_fatura_pendente`

## Vai para
- (le_estado) [[state_PENDENCIAS_PAGAMENTO_FATURA-2f592|PENDENCIAS_PAGAMENTO_FATURA]] 
- (grava_estado) [[state_db_auditoria_eventos-e3dd2|db:auditoria_eventos]] grava fatura_movimentos + auditoria

## Vem de
- (chama) [[text_confirmar_pagamento_estorno_crédito-0942f|confirmar pagamento|estorno|crédito]] 
