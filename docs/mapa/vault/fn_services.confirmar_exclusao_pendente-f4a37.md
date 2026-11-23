---
tipo: service
arquivo: services.py
linha: 8070
---
# services.confirmar_exclusao_pendente

Função de negócio (destino de roteamento).

`fn:services.confirmar_exclusao_pendente`

## Vai para
- (chama) [[fn_services.executar_exclusao_confirmada-c9366|services.executar_exclusao_confirmada]] 
- (chama) [[fn_services.criar_backup_pre_exclusao-6cdc5|services.criar_backup_pre_exclusao]] backup obrigatório antes de apagar
- (le_estado) [[state_PENDENCIAS_EXCLUSAO-1f0a4|PENDENCIAS_EXCLUSAO]] 

## Vem de
- (chama) [[text_confirmar_exclusao-ec8dc|confirmar exclusao]] 
