---
tipo: text_trigger
arquivo: services.py
linha: 8869
---
# cancelar exportação

Sem pendência: responde que nada foi alterado.

`text:cancelar exportação`

## Vai para
- (le_estado) [[state_PENDENCIAS_EXPORTACAO-908bd|PENDENCIAS_EXPORTACAO]] sem pendência responde que nada foi alterado

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8869
