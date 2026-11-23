---
tipo: callback
arquivo: app.py
linha: 1698
---
# guiado:registrar_parcela

Parcela: prefixa 'comprei '

`cb:guiado:registrar_parcela`

## Vai para
- (chama) [[fn_app.iniciar_fluxo_guiado-16de0|app.iniciar_fluxo_guiado]] 
- (grava_estado) [[state_PENDENCIAS_GUIADAS-21a17|PENDENCIAS_GUIADAS]] registrar_parcela

## Vem de
- (navega) [[cb_guiado-020e0|guiado:<tipo>[:<id>]]] 
- (navega) [[btn_Compra_parcelada-960ec|💳 Compra parcelada]] envia 'registrar_parcela'
