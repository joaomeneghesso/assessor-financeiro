---
tipo: handler
arquivo: app.py
linha: 967
---
# guardar_acao_pendente_pin

Guarda o update bloqueado em ACAO_PENDENTE_PIN com validade curta

`fn:app.guardar_acao_pendente_pin`

## Vai para
- (grava_estado) [[state_ACAO_PENDENTE_PIN-0c5d8|ACAO_PENDENTE_PIN]] 

## Vem de
- (chama) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] guarda a acao bloqueada antes de abrir o teclado
- (chama) [[fn_app.enviar_resposta-bb2f6|app.enviar_resposta]] arquivo (backup/CSV) so vai ao chat com PIN valido
