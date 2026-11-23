---
tipo: state
arquivo: app.py
linha: 1354
---
# PENDENCIAS_EXCLUSAO

TopicPending por chat_id: exclusao aguardando confirmacao (comando+previa)

`state:PENDENCIAS_EXCLUSAO`

## Vem de
- (grava_estado) [[fn_app.menu_command-1f10a|app.menu_command]] limpa
- (grava_estado) [[fn_app.cancelar_command-98dd8|cancelar_command]] limpa
- (le_estado) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] ordem 11: frase confirmar exclusao -> executar; cancelar/nao -> cancelar; outro texto -> aviso
- (grava_estado) [[fn_app.solicitar_confirmacao_exclusao-1455f|app.solicitar_confirmacao_exclusao]] 
- (le_estado) [[fn_app.executar_confirmacao_exclusao-c222c|app.executar_confirmacao_exclusao]] 
- (grava_estado) [[fn_app.executar_confirmacao_exclusao-c222c|app.executar_confirmacao_exclusao]] limpa
- (grava_estado) [[fn_app.cancelar_confirmacao_exclusao-2489c|app.cancelar_confirmacao_exclusao]] limpa
- (grava_estado) [[text_apagar_id-9d0af|apagar <id>]] ATENCAO: via pendencia guiada vai direto a processar_mensagem (4751) sem solicitar_confirmacao_exclusao
- (grava_estado) [[text_apagar_fixo_id-ae71a|apagar fixo <id>]] idem: confirmacao legada so por texto 'confirmar'
- (le_estado) [[fn_services.confirmar_exclusao_pendente-f4a37|services.confirmar_exclusao_pendente]] 
- (grava_estado) [[fn_services.cancelar_exclusao_pendente-f7c25|services.cancelar_exclusao_pendente]] limpa
- (grava_estado) [[fn_services._preparar_exclusao_sessao-b1879|services._preparar_exclusao_sessao]] define pendência (prévia)
