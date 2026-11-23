---
tipo: text_trigger
arquivo: telegram_experiencia.py
linha: 
---
# pergunta_compra

Frase 'posso comprar ... em 10x' -> simulação (só leitura).

`text:pergunta_compra`

## Vai para
- (chama) [[fn_ux.dispatch_text-8df9e|ux.dispatch_text]] 
- (chama) [[fn_ux.begin_can_buy-202cd|ux.begin_can_buy]] 
