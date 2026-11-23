---
tipo: service
arquivo: services.py
linha: 8336
---
# services.confirmar_alteracao_pendente

Confirma a alteração pendente: reconfere a prévia, consome a pendência e reexecuta o comando com a flag de alteração confirmada.

`fn:services.confirmar_alteracao_pendente`

## Vai para
- (le_estado) [[state_PENDENCIAS_ALTERACAO-e88b3|PENDENCIAS_ALTERACAO]] 
- (grava_estado) [[state_PENDENCIAS_ALTERACAO-e88b3|PENDENCIAS_ALTERACAO]] consome antes de executar
- (chama) [[fn_services.executar_alteracao_confirmada-b88d8|services.executar_alteracao_confirmada]] 
- (chama) [[fn_services.previa_alteracao-4f7fc|services.previa_alteracao]] reconfere a prévia

## Vem de
- (chama) [[text_confirmar_alteracao-9443a|confirmar alteracao]] 
