---
tipo: text_trigger
arquivo: services.py
linha: 8828
---
# últimas <filtro|n>

Número -> lista paginada das últimas N; texto -> filtro. Também 'listar últimos <filtro>'.

`text:últimas <filtro|n>`

## Vai para
- (chama) [[fn_services.montar_lista_transacoes_paginada-aad96|services.montar_lista_transacoes_paginada]] 
- (chama) [[fn_services.listar_ultimas_paginado-750fd|services.listar_ultimas_paginado]] 

## Vem de
- (alias_de) [[alias_ver_últimas_últimos_últimas_transações-80712|ver últimas/últimos/últimas transações -> últimas 10]] 
- (alias_de) [[alias_ver_últimas_n-033b8|ver últimas <n> -> últimas <n>]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8828
