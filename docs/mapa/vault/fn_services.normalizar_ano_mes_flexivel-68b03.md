---
tipo: service
arquivo: services.py
linha: 7319
---
# services.normalizar_ano_mes_flexivel

Aceita AAAA-MM, M/AAAA, 'nome ano'/'nome/ano' (jan..dez, abreviações). Sem ano -> None.

`fn:services.normalizar_ano_mes_flexivel`

## Vai para
- (chama) [[fn_services.texto_chave_saldo-d7dd4|services.texto_chave_saldo]] 7166

## Vem de
- (chama) [[text_quanto_vou_pagar-9e130|quanto vou pagar]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] auxiliar de normalização/validação
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 
