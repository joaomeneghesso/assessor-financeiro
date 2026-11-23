---
tipo: callback
arquivo: app.py
linha: 1698
---
# guiado:corrigir_conta

Pede conta -> 'corrigir conta <id> para <c>'

`cb:guiado:corrigir_conta`

## Vai para
- (chama) [[fn_app.iniciar_fluxo_guiado-16de0|app.iniciar_fluxo_guiado]] 
- (grava_estado) [[state_PENDENCIAS_GUIADAS-21a17|PENDENCIAS_GUIADAS]] corrigir_conta

## Vem de
- (navega) [[cb_guiado-020e0|guiado:<tipo>[:<id>]]] 
- (navega) [[btn_Banco_conta-23963|🏦 Banco/conta]] envia 'corrigir_conta:<id>'
