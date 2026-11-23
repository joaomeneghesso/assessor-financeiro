---
tipo: text_trigger
arquivo: services.py
linha: 9326
---
# alterar conta <id> para <conta> (lançamento)

Troca a conta de um lançamento (passa por prévia; parcela isolada é bloqueada).

`text:alterar conta <id> para <conta> (lançamento)`

## Vai para
- (chama) [[fn_services.corrigir_conta_por_id-4f258|services.corrigir_conta_por_id]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9326
