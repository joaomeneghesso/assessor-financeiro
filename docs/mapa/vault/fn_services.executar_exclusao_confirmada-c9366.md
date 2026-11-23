---
tipo: handler
arquivo: services.py
linha: 8061
---
# services.executar_exclusao_confirmada

services: executa exclusao apos confirmacao

`fn:services.executar_exclusao_confirmada`

## Vai para
- (grava_estado) [[state__EXCLUSAO_CONFIRMADA-6a03b|_EXCLUSAO_CONFIRMADA]] set(True)/reset
- (chama) [[fn_services.processar_mensagem-0f752|services.processar_mensagem]] reentra no roteador com flag

## Vem de
- (chama) [[fn_app.executar_confirmacao_exclusao-c222c|app.executar_confirmacao_exclusao]] 
- (chama) [[fn_services.confirmar_exclusao_pendente-f4a37|services.confirmar_exclusao_pendente]] 
