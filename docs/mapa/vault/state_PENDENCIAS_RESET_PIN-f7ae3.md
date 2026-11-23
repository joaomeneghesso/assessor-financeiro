---
tipo: state
arquivo: app.py
linha: 1355
---
# PENDENCIAS_RESET_PIN

dict por user_id: recuperacao guiada de PIN (etapas)

`state:PENDENCIAS_RESET_PIN`

## Vem de
- (le_estado) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] ordem 2
- (grava_estado) [[cb_pin_reset_cancelar-4dc8a|pin_reset_cancelar]] limpa
- (grava_estado) [[fn_app.iniciar_reset_pin_guiado-0cbbb|app.iniciar_reset_pin_guiado]] 
- (le_estado) [[fn_app.processar_reset_pin_guiado-9e198|app.processar_reset_pin_guiado]] 
