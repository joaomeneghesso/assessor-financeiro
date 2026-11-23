---
tipo: security_gate
arquivo: app.py
linha: 1003
---
# bloquear_se_assessor_travado

Se acao sensivel (acao_exige_pin ou exportacao_exige_pin) e PIN configurado e sessao travada: guarda a acao (ACAO_PENDENTE_PIN) e abre o teclado de PIN; apos desbloquear a acao e reexecutada

`gate:bloquear_se_assessor_travado`

## Vai para
- (chama) [[gate_acao_exige_pin-e6d76|acao_exige_pin]] 
- (chama) [[gate_exportacao_exige_pin-22a92|exportacao_exige_pin]] 
- (le_estado) [[gate_autolock-026e9|assessor_esta_desbloqueado]] 
- (chama) [[fn_app.guardar_acao_pendente_pin-68f50|guardar_acao_pendente_pin]] guarda a acao bloqueada antes de abrir o teclado
- (chama) [[fn_app.enviar_teclado_pin-92b87|app.enviar_teclado_pin]] 

## Vem de
- (exige_pin) [[fn_app.mes_command-26e50|mes_command]] 'saldo geral' (nao e acao sensivel: so PIN se exportacao)
- (exige_pin) [[fn_app.registrar_command-868b6|registrar_command]] 'saldo geral' (nao e acao sensivel: so PIN se exportacao)
- (exige_pin) [[fn_app.pagar_command-dd25a|pagar_command]] 'saldo geral' (nao e acao sensivel: so PIN se exportacao)
- (exige_pin) [[fn_app.historico_command-1af15|historico_command]] 'saldo geral' (nao e acao sensivel: so PIN se exportacao)
- (exige_pin) [[fn_app.saldos_command-20ef1|saldos_command]] 'saldo geral' (nao e acao sensivel: so PIN se exportacao)
- (exige_pin) [[fn_app.fechamento_command-07cdf|fechamento_command]] 'saldo geral' (nao e acao sensivel: so PIN se exportacao)
- (exige_pin) [[fn_app.atencao_command-b3322|atencao_command]] 'saldo geral' (nao e acao sensivel: so PIN se exportacao)
- (exige_pin) [[fn_app.dashboard_command-1e8d5|dashboard_command]] 'dashboard'
- (exige_pin) [[fn_app.recursos_command-92877|recursos_command]] 'dashboard'
- (exige_pin) [[fn_app.atalhos_command-41178|atalhos_command]] 'saldo geral'
- (exige_pin) [[fn_app.menu_command-1f10a|app.menu_command]] 'saldo geral'
- (exige_pin) [[fn_app.start-649a9|start]] 'dashboard' exceto lesson/help/learn
- (exige_pin) [[fn_app.meuid_command-1bec7|meuid_command]] '/meuid' (nunca exige)
- (exige_pin) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] ordem 12 (exclusao), 13 (comando guiado montado) e 14 (apos normalizar atalho ATALHOS_MENU)
- (exige_pin) [[cb_cmd-8bcfe|cmd:]] checa o comando depois de remover o prefixo __legado__ e converter periodo
- (exige_pin) [[cb___legado-f60eb|__legado__[tipo:assinatura]:<cmd>]] 
- (exige_pin) [[cb_guiado_apagar_lancamento-0d61d|guiado:apagar_lancamento]] 'apagar <id>'
- (exige_pin) [[cb_guiado_apagar_fixo-6811a|guiado:apagar_fixo]] 'apagar fixo <id>'
- (exige_pin) [[fn_app.abrir_atalho_ux-61f4e|app.abrir_atalho_ux]] 'saldo geral' (nao e acao sensivel)
