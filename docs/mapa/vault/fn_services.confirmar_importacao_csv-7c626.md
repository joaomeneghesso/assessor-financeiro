---
tipo: service
arquivo: services.py
linha: 9502
---
# services.confirmar_importacao_csv

Função de negócio (destino de roteamento).

`fn:services.confirmar_importacao_csv`

## Vai para
- (le_estado) [[state_PENDENCIAS_IMPORTACAO-26caf|PENDENCIAS_IMPORTACAO]] 
- (grava_estado) [[state_db_transacoes-fbd85|db:transacoes]] importa transações

## Vem de
- (chama) [[text_confirmar_importação-2b686|confirmar importação]] 
