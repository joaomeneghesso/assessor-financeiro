---
tipo: callback
arquivo: app.py
linha: 1698
---
# guiado:apagar_fixo

Com id: previa+Sim/Nao; sem id pede id (apagar_fixo_sem_id)

`cb:guiado:apagar_fixo`

## Vai para
- (chama) [[fn_app.iniciar_fluxo_guiado-16de0|app.iniciar_fluxo_guiado]] 
- (grava_estado) [[state_PENDENCIAS_GUIADAS-21a17|PENDENCIAS_GUIADAS]] confirmar_apagar_fixo
- (chama) [[fn_app.solicitar_confirmacao_exclusao-1455f|app.solicitar_confirmacao_exclusao]] 
- (exige_pin) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] 'apagar fixo <id>'

## Vem de
- (navega) [[cb_guiado-020e0|guiado:<tipo>[:<id>]]] 
- (navega) [[btn_Apagar_fixo-2aaee|🗑 Apagar fixo]] envia 'apagar_fixo'
