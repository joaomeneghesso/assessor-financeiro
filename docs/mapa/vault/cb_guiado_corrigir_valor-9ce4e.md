---
tipo: callback
arquivo: app.py
linha: 1698
---
# guiado:corrigir_valor

Pede novo valor -> 'corrigir <id> para <v>'

`cb:guiado:corrigir_valor`

## Vai para
- (chama) [[fn_app.iniciar_fluxo_guiado-16de0|app.iniciar_fluxo_guiado]] 
- (grava_estado) [[state_PENDENCIAS_GUIADAS-21a17|PENDENCIAS_GUIADAS]] corrigir_valor

## Vem de
- (navega) [[cb_guiado-020e0|guiado:<tipo>[:<id>]]] 
- (navega) [[btn_Valor-5237d|💵 Valor]] envia 'corrigir_valor:<id>'
