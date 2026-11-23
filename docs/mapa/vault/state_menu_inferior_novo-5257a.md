---
tipo: state
arquivo: app.py
linha: 3158
---
# montar_menu_principal (ReplyKeyboard)

Teclado fixo: Inicio, Registrar, A pagar, Historico, Analises, Mais. Rotulos NAO estao em ATALHOS_MENU (so os antigos Central/Lancar/Ajuda) -> dependem de ux.dispatch_text

`state:menu_inferior_novo`

## Vai para
- (navega) [[fn_ux.dispatch_text-8df9e|ux.dispatch_text]] texto dos botoes

## Vem de
- (grava_estado) [[fn_app.atalhos_command-41178|atalhos_command]] abre=True
