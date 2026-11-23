---
tipo: callback
arquivo: app.py
linha: 1698
---
# guiado:corrigir_categoria

Pede categoria -> 'mudar <id> para <cat>' + oferta aprendizado

`cb:guiado:corrigir_categoria`

## Vai para
- (chama) [[fn_app.iniciar_fluxo_guiado-16de0|app.iniciar_fluxo_guiado]] 
- (grava_estado) [[state_PENDENCIAS_GUIADAS-21a17|PENDENCIAS_GUIADAS]] corrigir_categoria

## Vem de
- (navega) [[cb_guiado-020e0|guiado:<tipo>[:<id>]]] 
- (navega) [[btn_Categoria-6a865|🏷 Categoria]] envia 'corrigir_categoria:<id>'
