---
tipo: text_trigger
arquivo: services.py
linha: 8543
---
# vencimento da fatura <cartão> [aaaa-mm] dia <n>

Grava vencimento de fatura.

`text:vencimento da fatura <cartão> [aaaa-mm] dia <n>`

## Vai para
- (chama) [[fn_services.definir_vencimento_fatura_por_nome_formatado-dacf0|services.definir_vencimento_fatura_por_nome_formatado]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8543
