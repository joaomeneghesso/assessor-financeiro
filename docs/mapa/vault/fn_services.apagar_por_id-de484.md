---
tipo: service
arquivo: services.py
linha: 11201
---
# services.apagar_por_id

Função de negócio (destino de roteamento).

`fn:services.apagar_por_id`

## Vai para
- (grava_estado) [[state_db_transacoes-fbd85|db:transacoes]] só executa com _EXCLUSAO_CONFIRMADA

## Vem de
- (chama) [[text_apagar_id-9d0af|apagar <id>]] 
