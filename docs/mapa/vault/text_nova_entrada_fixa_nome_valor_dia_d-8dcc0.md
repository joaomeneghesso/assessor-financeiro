---
tipo: text_trigger
arquivo: services.py
linha: 8888
---
# nova entrada fixa <nome> <valor> dia <d>

Cadastra entrada fixa.

`text:nova entrada fixa <nome> <valor> dia <d>`

## Vai para
- (chama) [[fn_compromissos.cadastrar_entrada_fixa_formatado-c714f|compromissos.cadastrar_entrada_fixa_formatado]] 
- (chama) [[fn_services.parsear_comando_entrada_fixa-da90a|services.parsear_comando_entrada_fixa]] 

## Vem de
- (alias_de) [[alias_criar_entrada_fixa_...-2f3a4|cadastrar|adicionar|incluir|criar entrada fixa <...> -> nova entrada fixa <...>]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8888
