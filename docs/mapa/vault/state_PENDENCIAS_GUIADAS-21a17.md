---
tipo: state
arquivo: app.py
linha: 1353
---
# PENDENCIAS_GUIADAS

TopicPending por chat_id: fluxo guiado aguardando texto (tipo/dados)

`state:PENDENCIAS_GUIADAS`

## Vem de
- (grava_estado) [[fn_app.menu_command-1f10a|app.menu_command]] limpa
- (grava_estado) [[fn_app.cancelar_command-98dd8|cancelar_command]] limpa
- (le_estado) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] ordem 13: fluxo guiado aguardando texto
- (grava_estado) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] limpa ao consumir
- (grava_estado) [[cb___guiado_cancelar-d5857|__guiado_cancelar__]] limpa
- (grava_estado) [[cb_guiado_registrar_despesa-9a43c|guiado:registrar_despesa]] registrar_despesa
- (grava_estado) [[cb_guiado_registrar_entrada-a97f6|guiado:registrar_entrada]] registrar_entrada
- (grava_estado) [[cb_guiado_registrar_parcela-4d4fa|guiado:registrar_parcela]] registrar_parcela
- (grava_estado) [[cb_guiado_corrigir_valor-9ce4e|guiado:corrigir_valor]] corrigir_valor
- (grava_estado) [[cb_guiado_corrigir_categoria-8f04b|guiado:corrigir_categoria]] corrigir_categoria
- (grava_estado) [[cb_guiado_corrigir_conta-74439|guiado:corrigir_conta]] corrigir_conta
- (grava_estado) [[cb_guiado_apagar_lancamento-0d61d|guiado:apagar_lancamento]] confirmar_apagar_lancamento
- (grava_estado) [[cb_guiado_alterar_conta_fixo-0885d|guiado:alterar_conta_fixo]] alterar_conta_fixo
- (grava_estado) [[cb_guiado_apagar_fixo-6811a|guiado:apagar_fixo]] confirmar_apagar_fixo
- (grava_estado) [[fn_app.iniciar_fluxo_guiado-16de0|app.iniciar_fluxo_guiado]] 
- (le_estado) [[fn_app.montar_comando_de_pendencia-10c04|app.montar_comando_de_pendencia]] 
