---
tipo: service
arquivo: services.py
linha: 8328
---
# services.executar_alteracao_confirmada

Reentra em processar_mensagem com _ALTERACAO_CONFIRMADA ligado (execução confirmada).

`fn:services.executar_alteracao_confirmada`

## Vai para
- (grava_estado) [[state__ALTERACAO_CONFIRMADA-fe9b4|_ALTERACAO_CONFIRMADA]] set(True)/reset
- (chama) [[fn_services.processar_mensagem-0f752|services.processar_mensagem]] reentra no roteador com flag

## Vem de
- (chama) [[fn_services.confirmar_alteracao_pendente-f320b|services.confirmar_alteracao_pendente]] 
