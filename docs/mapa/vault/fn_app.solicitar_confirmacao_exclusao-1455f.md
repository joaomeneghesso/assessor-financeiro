---
tipo: handler
arquivo: app.py
linha: 1533
---
# app.solicitar_confirmacao_exclusao

Gera previa, grava PENDENCIAS_EXCLUSAO e mostra Sim/Nao apagar

`fn:app.solicitar_confirmacao_exclusao`

## Vai para
- (chama) [[fn_services.preparar_previa_exclusao-a7664|services.preparar_previa_exclusao]] 
- (grava_estado) [[state_PENDENCIAS_EXCLUSAO-1f0a4|PENDENCIAS_EXCLUSAO]] 
- (navega) [[btn_Sim_apagar-63d9a|🗑 Sim, apagar]] montar_botoes_confirmacao_exclusao
- (navega) [[btn_Não_apagar-76da1|✖️ Não apagar]] 
- (navega) [[btn_Sim_apagar-63d9a|🗑 Sim, apagar]] teclado inline
- (navega) [[btn_Não_apagar-76da1|✖️ Não apagar]] teclado inline

## Vem de
- (chama) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] 
- (navega) [[gate_comando_exige_confirmacao_exclusao-825e1|comando_exige_confirmacao_exclusao]] 
- (chama) [[cb_guiado_apagar_lancamento-0d61d|guiado:apagar_lancamento]] 
- (chama) [[cb_guiado_apagar_fixo-6811a|guiado:apagar_fixo]] 
