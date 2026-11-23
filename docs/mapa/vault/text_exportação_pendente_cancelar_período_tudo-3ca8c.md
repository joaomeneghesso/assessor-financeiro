---
tipo: text_trigger
arquivo: services.py
linha: 8845
---
# exportação pendente (cancelar|período|tudo)

Só ativa com PENDENCIAS_EXPORTACAO da sessão.

`text:exportação pendente (cancelar|período|tudo)`

## Vai para
- (chama) [[fn_services.exportar_csv_periodo-4b592|services.exportar_csv_periodo]] 
- (chama) [[fn_services.exportar_csv_completo-ab986|services.exportar_csv_completo]] 
- (grava_estado) [[state_PENDENCIAS_EXPORTACAO-908bd|PENDENCIAS_EXPORTACAO]] limpa ao cancelar/receber período

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8845
