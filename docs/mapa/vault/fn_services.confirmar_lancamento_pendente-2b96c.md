---
tipo: service
arquivo: services.py
linha: 9529
---
# services.confirmar_lancamento_pendente

Função de negócio (destino de roteamento).

`fn:services.confirmar_lancamento_pendente`

## Vai para
- (le_estado) [[state_PENDENCIAS_CONFIRMACAO-76a92|PENDENCIAS_CONFIRMACAO]] 
- (grava_estado) [[state_db_transacoes-fbd85|db:transacoes]] 

## Vem de
- (chama) [[text_confirmar-98b3b|confirmar]] 
