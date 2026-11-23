---
tipo: callback
arquivo: app.py
linha: 1698
---
# guiado:alterar_conta_fixo

Pede conta do fixo -> 'alterar conta fixo <id> para <c>'

`cb:guiado:alterar_conta_fixo`

## Vai para
- (chama) [[fn_app.iniciar_fluxo_guiado-16de0|app.iniciar_fluxo_guiado]] 
- (grava_estado) [[state_PENDENCIAS_GUIADAS-21a17|PENDENCIAS_GUIADAS]] alterar_conta_fixo

## Vem de
- (navega) [[cb_guiado-020e0|guiado:<tipo>[:<id>]]] 
- (navega) [[btn_Alterar_conta-9a995|🏦 Alterar conta]] envia 'alterar_conta_fixo'
