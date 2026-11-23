---
tipo: state
arquivo: services.py
linha: 8104
---
# _ALTERACAO_CONFIRMADA

ContextVar bool: marca execução de alteração já confirmada; nunca vem do texto digitado.

`state:_ALTERACAO_CONFIRMADA`

## Vem de
- (grava_estado) [[fn_services.executar_alteracao_confirmada-b88d8|services.executar_alteracao_confirmada]] set(True)/reset
- (le_estado) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] 8446
