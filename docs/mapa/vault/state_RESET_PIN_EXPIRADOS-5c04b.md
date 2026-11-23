---
tipo: state
arquivo: app.py
linha: 299
---
# RESET_PIN_EXPIRADOS

set de user_id cuja recuperacao de PIN expirou; a mensagem seguinte e apagada e avisada

`state:RESET_PIN_EXPIRADOS`

## Vem de
- (le_estado) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] ordem 2b: recuperacao expirada -> apaga a mensagem seguinte e avisa
