---
tipo: handler
arquivo: telegram_experiencia.py
linha: 631
---
# obligations

Obrigações em aberto do mês + pendências anteriores; projeção futura só inclui vencidas.

`fn:ux.obligations`

## Vai para
- (chama) [[fn_services.montar_itens_checklist_mes-586cd|services.montar_itens_checklist_mes]] 
- (chama) [[fn_services.aplicar_status_checklist-8e28a|services.aplicar_status_checklist]] 
- (chama) [[fn_services.listar_pendencias_abertas_anteriores-9817a|listar_pendencias_abertas_anteriores]] 
- (chama) [[fn_services.listar_revisoes_baixas_anteriores-ea7e8|listar_revisoes_baixas_anteriores]] 
- (chama) [[fn_services.item_checklist_eh_credito_individual-ab4d0|item_checklist_eh_credito_individual]] 

## Vem de
- (chama) [[screen_pay-ee2a3|pay]] 
- (chama) [[screen_home-111fe|home]] 
- (chama) [[fn_orientacao.coletar-ba856|coletar]] 
