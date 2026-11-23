---
tipo: service
arquivo: telegram_aprendizado.py
linha: 84
---
# telegram_aprendizado.route

fullmatch /?(aprender|aula|treinamento|manual|tutorial|guia)[ tópico]; devolve tópico via ALIASES ('quanto vou pagar' -> aula 'compromissos').

`fn:telegram_aprendizado.route`

## Vai para
- (navega) [[text_aprender_quanto_vou_pagar-76354|aprender quanto vou pagar]] 

## Vem de
- (chama) [[mod_telegram_aprendizado.py-b8561|telegram_aprendizado.py]] 
- (chama) [[fn_telegram_experiencia.handle_text-7faea|telegram_experiencia.handle_text]] 2912 (antes de qualquer outra regra)
- (chama) [[fn_telegram_experiencia.dispatch_text-ef266|telegram_experiencia.dispatch_text]] 4152
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 
