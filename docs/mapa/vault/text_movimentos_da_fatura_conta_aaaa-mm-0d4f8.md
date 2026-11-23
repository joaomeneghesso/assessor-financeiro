---
tipo: text_trigger
arquivo: services.py
linha: 8502
---
# movimentos da fatura <conta> [aaaa-mm]

-> 'movimentos'.

`text:movimentos da fatura <conta> [aaaa-mm]`

## Vai para
- (chama) [[fn_services.listar_movimentos_fatura_formatado-92a3d|services.listar_movimentos_fatura_formatado]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8502
