---
tipo: text_trigger
arquivo: services.py
linha: 9253
---
# exportar csv <período|aaaa-mm>

Exporta CSV de um período ou mês; formato inválido responde ajuda.

`text:exportar csv <período|aaaa-mm>`

## Vai para
- (chama) [[fn_services.exportar_csv_periodo-4b592|services.exportar_csv_periodo]] 
- (chama) [[fn_services.exportar_csv_mes-69fcd|services.exportar_csv_mes]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9253
