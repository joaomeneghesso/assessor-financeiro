---
tipo: callback
arquivo: app.py
linha: 1698
---
# guiado:registrar_fixo

Fixo: abre ux new_fixed_start (nao usa PENDENCIAS_GUIADAS)

`cb:guiado:registrar_fixo`

## Vai para
- (chama) [[fn_app.iniciar_fluxo_guiado-16de0|app.iniciar_fluxo_guiado]] 
- (chama) [[fn_ux.run_experience-c1322|ux.run_experience]] act new_fixed_start

## Vem de
- (navega) [[cb_guiado-020e0|guiado:<tipo>[:<id>]]] 
- (navega) [[btn_Fixo_mensal-da0f8|🧾 Fixo mensal]] envia 'registrar_fixo'
