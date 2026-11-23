---
tipo: text_trigger
arquivo: services.py
linha: 8508
---
# paguei <valor> da fatura <conta> usando <origem>

Pagamento parcial de fatura (prévia).

`text:paguei <valor> da fatura <conta> usando <origem>`

## Vai para
- (chama) [[fn_services._preparar_movimento_fatura_sessao-44ad5|services._preparar_movimento_fatura_sessao]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8508
