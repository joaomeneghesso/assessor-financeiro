---
tipo: callback
arquivo: app.py
linha: 1698
---
# guiado:registrar_despesa

Despesa: pede frase e grava via services

`cb:guiado:registrar_despesa`

## Vai para
- (chama) [[fn_app.iniciar_fluxo_guiado-16de0|app.iniciar_fluxo_guiado]] 
- (grava_estado) [[state_PENDENCIAS_GUIADAS-21a17|PENDENCIAS_GUIADAS]] registrar_despesa

## Vem de
- (navega) [[cb_guiado-020e0|guiado:<tipo>[:<id>]]] 
- (navega) [[btn_Despesa-bd09d|💸 Despesa]] envia 'registrar_despesa'
- (navega) [[btn_Registrar_despesa-3a157|💸 Registrar despesa]] envia 'registrar_despesa'
