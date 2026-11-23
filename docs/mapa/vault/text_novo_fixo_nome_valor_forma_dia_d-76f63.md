---
tipo: text_trigger
arquivo: services.py
linha: 8955
---
# novo fixo <nome> <valor> [forma] dia <d>

Cadastra fixo.

`text:novo fixo <nome> <valor> [forma] dia <d>`

## Vai para
- (chama) [[fn_compromissos.cadastrar_fixo_manual_formatado-4c26d|compromissos.cadastrar_fixo_manual_formatado]] 
- (chama) [[fn_services.parsear_comando_novo_fixo-33e28|services.parsear_comando_novo_fixo]] 

## Vem de
- (alias_de) [[alias_criar_fixo_...-6a30b|cadastrar|adicionar|incluir|criar fixo <...> -> novo fixo <...>]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8955
