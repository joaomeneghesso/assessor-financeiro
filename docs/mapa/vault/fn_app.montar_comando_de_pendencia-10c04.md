---
tipo: handler
arquivo: app.py
linha: 1858
---
# app.montar_comando_de_pendencia

Converte o texto digitado em comando de servico conforme PENDENCIAS_GUIADAS.tipo

`fn:app.montar_comando_de_pendencia`

## Vai para
- (le_estado) [[state_PENDENCIAS_GUIADAS-21a17|PENDENCIAS_GUIADAS]] 
- (navega) [[text_corrigir_id_para_valor-c713e|corrigir <id> para <valor>]] 
- (navega) [[text_mudar_id_para_categoria-45f77|mudar <id> para <categoria>]] 
- (navega) [[text_corrigir_conta_id_para_conta-9f564|corrigir conta <id> para <conta>]] 
- (navega) [[text_alterar_conta_fixo_id_para_conta-6cfaa|alterar conta fixo <id> para <conta>]] 
- (navega) [[text_apagar_id-9d0af|apagar <id>]] 
- (navega) [[text_apagar_fixo_id-ae71a|apagar fixo <id>]] 
- (navega) [[text_recebi_texto-be1f6|recebi <texto>]] 
- (navega) [[text_comprei_texto-91be1|comprei <texto>]] 
- (navega) [[text_novo_fixo_texto-1c479|novo fixo <texto>]] 

## Vem de
- (chama) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] ordem 13: converte o texto no comando de servico
