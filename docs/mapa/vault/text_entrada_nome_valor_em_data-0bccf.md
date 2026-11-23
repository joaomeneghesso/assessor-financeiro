---
tipo: text_trigger
arquivo: services.py
linha: 8905
---
# entrada <nome> <valor> em <data>

Cadastra entrada futura avulsa.

`text:entrada <nome> <valor> em <data>`

## Vai para
- (chama) [[fn_compromissos.cadastrar_entrada_avulsa_formatado-87f07|compromissos.cadastrar_entrada_avulsa_formatado]] 
- (chama) [[fn_services.parsear_comando_entrada_avulsa-c4a7d|services.parsear_comando_entrada_avulsa]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8905
