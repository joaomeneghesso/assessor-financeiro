---
tipo: callback
arquivo: app.py
linha: 5071
---
# cmd:

Token cmd:<rand> -> CALLBACK_COMANDOS (24 h)

`cb:cmd:`

## Vai para
- (le_estado) [[state_CALLBACK_COMANDOS-49632|CALLBACK_COMANDOS]] expirado -> 'Esse botão expirou'
- (navega) [[cb_expirado-57247|botao expirado]] 
- (navega) [[cb___legado-f60eb|__legado__[tipo:assinatura]:<cmd>]] valor em CALLBACK_COMANDOS
- (navega) [[cb___exportar_periodo-dad4a|__exportar_periodo__:<mes_atual|mes_passado|ano_atual>]] valor em CALLBACK_COMANDOS
- (navega) [[cb___guiado_cancelar-d5857|__guiado_cancelar__]] valor em CALLBACK_COMANDOS
- (navega) [[cb___perguntar_herdar-854f4|__perguntar_herdar__:<saldo inicial AAAA-MM conta herdado>]] valor em CALLBACK_COMANDOS
- (navega) [[cb___nada_alterado-e515f|__nada_alterado__]] valor em CALLBACK_COMANDOS
- (navega) [[cb___bloquear-20806|__bloquear__]] valor em CALLBACK_COMANDOS
- (navega) [[cb___confirmar_exclusao-3fc51|__confirmar_exclusao__]] valor em CALLBACK_COMANDOS
- (navega) [[cb___cancelar_exclusao-623cb|__cancelar_exclusao__]] valor em CALLBACK_COMANDOS
- (navega) [[cb___aprender_categoria_sim-65b68|__aprender_categoria_sim__]] valor em CALLBACK_COMANDOS
- (navega) [[cb___aprender_categoria_nao-1637f|__aprender_categoria_nao__]] valor em CALLBACK_COMANDOS
- (navega) [[cb_guiado-020e0|guiado:<tipo>[:<id>]]] valor em CALLBACK_COMANDOS
- (navega) [[cb_limpar-4d60a|/limpar | /clear]] valor em CALLBACK_COMANDOS
- (exige_pin) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] checa o comando depois de remover o prefixo __legado__ e converter periodo
- (chama) [[gate_comando_exige_confirmacao_exclusao-825e1|comando_exige_confirmacao_exclusao]] app.py
- (chama) [[fn_ux.run_experience-c1322|ux.run_experience]] handle_text(comando) ANTES do legado, exceto __legado__/__exportar_periodo__ (app.py)
- (chama) [[fn_app.obter_resposta_comando_especial-bcaa6|app.obter_resposta_comando_especial]] 
- (chama) [[fn_services.processar_mensagem-0f752|services.processar_mensagem]] fallback
- (chama) [[fn_app.enviar_resposta-bb2f6|app.enviar_resposta]] 

## Vem de
- (navega) [[fn_app.callback_submenu-249d5|app.callback_submenu]] ordem 4 (fallback): token -> CALLBACK_COMANDOS
