---
tipo: text_trigger
arquivo: app.py
linha: 9103
---
# fixos

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:fixos`

## Vai para
- (navega) [[btn_Editar_fixos-12cc3|✏️ Editar fixos]] teclado inline
- (navega) [[btn_Agenda_geral-7b611|📆 Agenda geral]] teclado inline
- (navega) [[btn_Categorias_categorias-7f8d8|🏷 Categorias]] teclado inline
- (navega) [[btn_Contas_contas-3e876|💰 Contas]] teclado inline
- (navega) [[btn_Diagnóstico-8e4de|🧠 Diagnóstico]] teclado inline
- (chama) [[fn_compromissos.listar_fixos_formatado-cef5c|compromissos.listar_fixos_formatado]] 

## Vem de
- (navega) [[text___atalho_menu-5b206|ATALHOS_MENU]] 
- (navega) [[btn_Ver_fixos-e1490|🧾 Ver fixos]] envia 'fixos'
- (navega) [[btn_Fixos_fixos-5a228|🧾 Fixos]] envia 'fixos'
- (alias_de) [[alias_ver_fixo_s-17416|ver|listar|mostrar|consultar|abrir|exibir fixo(s) -> fixos]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9103
