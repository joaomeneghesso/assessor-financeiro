---
tipo: callback
arquivo: app.py
linha: 1698
---
# guiado:apagar_lancamento

Com id: previa+Sim/Nao via solicitar_confirmacao_exclusao (exige PIN gate); sem fallback pende 'confirmar_apagar_lancamento'

`cb:guiado:apagar_lancamento`

## Vai para
- (chama) [[fn_app.iniciar_fluxo_guiado-16de0|app.iniciar_fluxo_guiado]] 
- (grava_estado) [[state_PENDENCIAS_GUIADAS-21a17|PENDENCIAS_GUIADAS]] confirmar_apagar_lancamento
- (chama) [[fn_app.solicitar_confirmacao_exclusao-1455f|app.solicitar_confirmacao_exclusao]] 
- (exige_pin) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] 'apagar <id>'

## Vem de
- (navega) [[cb_guiado-020e0|guiado:<tipo>[:<id>]]] 
- (navega) [[btn_Apagar-217f5|🗑 Apagar]] envia 'apagar_lancamento:<id>'
