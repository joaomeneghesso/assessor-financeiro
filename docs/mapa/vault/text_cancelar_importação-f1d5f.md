---
tipo: text_trigger
arquivo: services.py
linha: 8881
---
# cancelar importação

Limpa PENDENCIAS_IMPORTACAO; nada gravado.

`text:cancelar importação`

## Vai para
- (chama) [[fn_services._limpar_pendencia-91039|services._limpar_pendencia]] 
- (grava_estado) [[state_PENDENCIAS_IMPORTACAO-26caf|PENDENCIAS_IMPORTACAO]] limpa

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8881
