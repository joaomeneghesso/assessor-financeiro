---
tipo: modulo
grupo: Entrada e operação
linhas: 5537
tags: [modulo, entrada-e-operacao]
---
# app.py

**Grupo:** [[Entrada e operação]] · **Linhas:** 5537 · **Funções:** 188 · **Classes:** 0

> [!warning] Linha de base
> Limite de 5537 linhas (hoje 5537). Este arquivo não pode crescer: código novo vai em módulo próprio.

## Usa

- [[categorias_pessoais.py]] *(importação tardia, dentro de função)*
- [[config.py]]
- [[database.py]] *(importação tardia, dentro de função)*
- [[estado_runtime.py]]
- [[limitador_persistente.py]] *(importação tardia, dentro de função)*
- [[operacao_bot.py]] *(importação tardia, dentro de função)*
- [[registro_logs.py]] *(importação tardia, dentro de função)*
- [[relogio.py]]
- [[security.py]]
- [[services.py]] *(importação tardia, dentro de função)*
- [[telegram_alertas.py]] *(importação tardia, dentro de função)*
- [[telegram_design.py]] *(importação tardia, dentro de função)*
- [[telegram_execucao.py]]
- [[telegram_experiencia.py]]
- [[telegram_midia.py]] *(importação tardia, dentro de função)*
- [[telegram_recursos.py]] *(importação tardia, dentro de função)*

## Usado por

- (ninguém no código de produção; ponto de entrada ou script)

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `bloquear_assessor` | 192 | 0 | 5 |  |
| `callback_submenu` | 5050 | 0 | 4 |  |
| `receber_mensagem` | 4813 | 0 | 4 |  |
| `definir_pendencia_exclusao` | 1461 | 0 | 3 |  |
| `definir_pendencia_guiada` | 1678 | 0 | 3 |  |
| `desbloquear_assessor` | 185 | 0 | 3 |  |
| `montar_teclado_inline_para_resposta` | 2702 | 0 | 3 |  |
| `obter_pendencia_exclusao` | 1474 | 0 | 3 |  |
| `registrar_callback_comando` | 1998 | 0 | 3 |  |
| `acao_exige_pin` | 930 | 0 | 2 | PIN de segunda camada apenas para ações de alto impacto ou exfiltração. |
| `bloquear_se_assessor_travado` | 1022 | 0 | 2 |  |
| `enviar_resposta` | 3300 | 0 | 2 |  |
| `iniciar_teclado_pin` | 667 | 0 | 2 |  |
| `limpar_pendencia_guiada` | 1658 | 0 | 2 |  |
| `montar_teclado_confirmacoes_texto` | 2065 | 0 | 2 | Botões para as respostas que hoje pedem uma frase digitada. |
| `obter_pendencia_guiada` | 1666 | 0 | 2 |  |
| `persistir_callback_comandos` | 1347 | 0 | 2 |  |
| `processar_callback_pin` | 765 | 0 | 2 |  |
| `processar_reset_pin` | 553 | 0 | 2 |  |
| `_restaurar_callbacks` | 1324 | 0 | 1 | Restaura botões salvos; qualquer formato inesperado é descartado. |
| `assessor_esta_desbloqueado` | 145 | 0 | 1 |  |
| `ativar_limitador_persistente` | 5440 | 0 | 1 | Troca o limitador em memória pelo persistido em .runtime (DPAPI). |
| `atualizar_valor_env` | 231 | 0 | 1 |  |
| `avisar_erro_ao_titular` | 5432 | 0 | 1 | Aviso curto do tratador global; nunca responde fora da allowlist. |
| `comando_exige_confirmacao_exclusao` | 1483 | 0 | 1 |  |

## Tudo que define

188 definições; as 40 maiores:

- `montar_teclado_inline_para_resposta` (L2702, 461 linhas)
- `montar_teclado_acao_produtiva` (L2459, 241 linhas)
- `receber_mensagem` (L4813, 235 linhas)
- `callback_submenu` (L5050, 209 linhas)
- `montar_help_por_tema` (L4203, 176 linhas)
- `iniciar_fluxo_guiado` (L1712, 158 linhas)
- `processar_callback_pin` (L765, 144 linhas)
- `enviar_resposta` (L3300, 143 linhas)
- `processar_reset_pin_guiado` (L407, 132 linhas)
- `processar_reset_pin` (L553, 100 linhas)
- `montar_teclado_confirmacoes_texto` (L2065, 79 linhas) — Botões para as respostas que hoje pedem uma frase digitada.
- `montar_comando_de_pendencia` (L1872, 62 linhas)
- `linha_parece_comando_ou_exemplo` (L1141, 60 linhas)
- `main` (L5474, 60 linhas)
- `montar_help_principal` (L3446, 57 linhas)
- `obter_etapas_feedback_visual` (L4717, 52 linhas)
- `acao_exige_pin` (L930, 50 linhas) — PIN de segunda camada apenas para ações de alto impacto ou exfiltração.
- `executar_confirmacao_exclusao` (L1584, 50 linhas)
- `limpar_command` (L4481, 47 linhas)
- `extrair_ids_lista_visual_transacoes` (L2316, 44 linhas)
- `montar_help_checklist` (L3696, 44 linhas)
- `montar_help_saldo` (L3650, 43 linhas)
- `montar_help_fixos` (L3537, 40 linhas)
- `extrair_categorias_da_resposta` (L2220, 39 linhas)
- `montar_help_caixa` (L4032, 39 linhas)
- `obter_status_seguranca` (L1039, 38 linhas)
- `inicializar_alertas` (L5366, 38 linhas)
- `montar_teclado_pin` (L693, 35 linhas)
- `solicitar_confirmacao_exclusao` (L1547, 35 linhas)
- `montar_help_agenda` (L3742, 34 linhas)
- `montar_help_caju` (L4142, 34 linhas)
- `oferecer_aprendizado_categoria` (L1962, 33 linhas) — Oferece uma regra pessoal apenas depois de uma correção confirmada.
- `montar_help_consultas` (L3614, 33 linhas)
- `montar_help_corrigir` (L3813, 33 linhas)
- `montar_help_parcelas` (L3579, 32 linhas)
- `montar_help_detalhar` (L3778, 32 linhas)
- `montar_help_excluir` (L3848, 32 linhas)
- `montar_help_assessor` (L3997, 32 linhas)
- `rotina_backup_diario` (L5322, 31 linhas)
- `assessor_esta_desbloqueado` (L145, 29 linhas)

## Testes que usam (14)

- `tests/test_app_pin_pendencias_bloco_p1.py`
- `tests/test_apresentacao_telegram_406.py`
- `tests/test_bloco_a_protecao_dados.py`
- `tests/test_bloco_b_complementos.py`
- `tests/test_bloco_d_usabilidade.py`
- `tests/test_botoes_confirmacao.py`
- `tests/test_confiabilidade_413.py`
- `tests/test_gravacao_confirmacao_legado.py`
- `tests/test_help_aprender_dashboard_407.py`
- `tests/test_inovacoes_410.py`
- `tests/test_legado_app_onda2.py`
- `tests/test_paginacao_ultimas_botao.py`
- `tests/test_pin_gate_normalizacao.py`
- `tests/test_pin_teclado_assincrono.py`

## No mapa de rotas

- **Módulo (1):** [[mod_app.py-57fef|app.py]]
- **Rotinas agendadas (5):** [[job_rotina_alerta_diario-7759e|rotina_alerta_diario]], [[job_rotina_backup_diario-a6f56|rotina_backup_diario]], [[job_rotina_lembrete_pagamentos_diario-95ac7|rotina_lembrete_pagamentos_diario]], [[job_rotina_resumo_domingo-a471e|rotina_resumo_domingo]], [[job_telegram_alertas.rotina-da520|telegram_alertas.rotina]]
- **Travas de segurança (8):** [[gate_acao_exige_pin-e6d76|acao_exige_pin]], [[gate_AUTH_LIMITER-f4350|AUTH_LIMITER]], [[gate_autolock-026e9|assessor_esta_desbloqueado]], [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]], [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]], [[gate_comando_exige_confirmacao_exclusao-825e1|comando_exige_confirmacao_exclusao]], [[gate_comando_publico_morto-ecabe|comando_publico / COMANDOS_PUBLICOS]], [[gate_exportacao_exige_pin-22a92|exportacao_exige_pin]]
- **Comandos (25):** [[cmd_aprender-9853d|/aprender]], [[cmd_atalhos-bf841|/atalhos]], [[cmd_atencao-91288|/atencao]], [[cmd_bloquear-80413|/bloquear]], [[cmd_cancelar-18e66|/cancelar]], [[cmd_clear-91068|/clear]], [[cmd_dashboard-a49b5|/dashboard]], [[cmd_desbloquear-a195b|/desbloquear]], [[cmd_esqueci_pin-498c9|/esqueci_pin]], [[cmd_fechamento-91459|/fechamento]], [[cmd_help-8f98e|/help]], [[cmd_historico-7c809|/historico]], [[cmd_limpar-95d87|/limpar]], [[cmd_menu-be698|/menu]], [[cmd_mes-c68e2|/mes]], [[cmd_meuid-1259a|/meuid]], [[cmd_pagar-2cad9|/pagar]], [[cmd_recursos-2721a|/recursos]], [[cmd_registrar-e1453|/registrar]], [[cmd_reset-e7bdc|/reset]], [[cmd_resetarpin-60ca1|/resetarpin]], [[cmd_saldos-983af|/saldos]], [[cmd_seguranca-97c12|/seguranca]], [[cmd_start-ad3b7|/start]], [[cmd_topicos-6a34a|/topicos]]
- **Estado da sessão (18):** [[state_ACAO_PENDENTE_PIN-0c5d8|ACAO_PENDENTE_PIN]], [[state_AUTH_LIMITER-e62f8|AUTH_LIMITER]], [[state_CALLBACK_COMANDOS-49632|CALLBACK_COMANDOS]], [[state_EXCLUSAO_EXPIRADAS-95cde|EXCLUSAO_EXPIRADAS]], [[state_MENSAGENS_CHAT-a0bbb|MENSAGENS_CHAT]], [[state_menu_inferior_novo-5257a|montar_menu_principal (ReplyKeyboard)]], [[state_mes_base-b9f3b|mes_base]], [[state_PENDENCIAS_APRENDIZADO_CATEGORIA-ac4b1|PENDENCIAS_APRENDIZADO_CATEGORIA]], [[state_PENDENCIAS_EXCLUSAO-1f0a4|PENDENCIAS_EXCLUSAO]], [[state_PENDENCIAS_GUIADAS-21a17|PENDENCIAS_GUIADAS]], [[state_PENDENCIAS_RESET_PIN-f7ae3|PENDENCIAS_RESET_PIN]], [[state_PIN_TECLADO-570e9|PIN_TECLADO]], [[state_RESET_PIN_EXPIRADOS-5c04b|RESET_PIN_EXPIRADOS]], [[state_session.month-91610|session.month]], [[state_SESSOES_SEGURANCA-5af35|SESSOES_SEGURANCA]], [[state_ux.session_draft_stage_pending-60605|ux.session(draft/stage/pending)]], [[state_VINCULOS_BOTAO-d6c43|VINCULOS_BOTAO]], [[text___fallback_hoje-287b7|date.today()]]
- **Callbacks (33):** [[cb___aprender_categoria_nao-1637f|__aprender_categoria_nao__]], [[cb___aprender_categoria_sim-65b68|__aprender_categoria_sim__]], [[cb___bloquear-20806|__bloquear__]], [[cb___cancelar_exclusao-623cb|__cancelar_exclusao__]], [[cb___confirmar_exclusao-3fc51|__confirmar_exclusao__]], [[cb___exportar_periodo-dad4a|__exportar_periodo__:<mes_atual|mes_passado|ano_atual>]], [[cb___guiado_cancelar-d5857|__guiado_cancelar__]], [[cb___help-92276|__help__]], [[cb___legado-f60eb|__legado__[tipo:assinatura]:<cmd>]], [[cb___nada_alterado-e515f|__nada_alterado__]], [[cb___perguntar_herdar-854f4|__perguntar_herdar__:<saldo inicial AAAA-MM conta herdado>]], [[cb_af-51179|af:]], [[cb_cmd-8bcfe|cmd:]], [[cb_expirado-57247|botao expirado]], [[cb_guiado-020e0|guiado:<tipo>[:<id>]]], [[cb_guiado_alterar_conta_fixo-0885d|guiado:alterar_conta_fixo]], [[cb_guiado_apagar_fixo-6811a|guiado:apagar_fixo]], [[cb_guiado_apagar_lancamento-0d61d|guiado:apagar_lancamento]], [[cb_guiado_corrigir_categoria-8f04b|guiado:corrigir_categoria]], [[cb_guiado_corrigir_conta-74439|guiado:corrigir_conta]], [[cb_guiado_corrigir_valor-9ce4e|guiado:corrigir_valor]], [[cb_guiado_registrar_despesa-9a43c|guiado:registrar_despesa]], [[cb_guiado_registrar_entrada-a97f6|guiado:registrar_entrada]], [[cb_guiado_registrar_fixo-9b449|guiado:registrar_fixo]], [[cb_guiado_registrar_parcela-4d4fa|guiado:registrar_parcela]], [[cb_limpar-4d60a|/limpar | /clear]], [[cb_pin-c0fea|pin_*]], [[cb_pin_cancelar-c97bd|pin_cancelar]], [[cb_pin_limpar-ceb0c|pin_limpar]], [[cb_pin_pair_i-32cd9|pin_pair:<i>]] …
- **Tratadores (88):** [[cmd_atalhos_abrir_atalho_ux-b0368|/pagar /historico /saldos /fechamento /atencao /recursos]], [[fn_app.abrir_atalho_ux-61f4e|app.abrir_atalho_ux]], [[fn_app.aprender_command-b4392|aprender_command]], [[fn_app.atalhos_command-41178|atalhos_command]], [[fn_app.atencao_command-b3322|atencao_command]], [[fn_app.ativar_limitador_persistente-7c987|ativar_limitador_persistente]], [[fn_app.avisar_erro_ao_titular-f3533|avisar_erro_ao_titular]], [[fn_app.bloquear_command-58dbc|bloquear_command]], [[fn_app.botao_comando-efd13|botao_comando]], [[fn_app.botao_comando_vinculado-beb3a|botao_comando_vinculado]], [[fn_app.botao_texto-e5d6a|botao_texto]], [[fn_app.callback_submenu-249d5|app.callback_submenu]], [[fn_app.cancelar_command-98dd8|cancelar_command]], [[fn_app.cancelar_confirmacao_exclusao-2489c|app.cancelar_confirmacao_exclusao]], [[fn_app.dashboard_command-1e8d5|dashboard_command]], [[fn_app.desbloquear_command-2c762|desbloquear_command]], [[fn_app.descartar_acao_pendente_pin-4ebf5|descartar_acao_pendente_pin]], [[fn_app.enviar_resposta-bb2f6|app.enviar_resposta]], [[fn_app.enviar_teclado_pin-92b87|app.enviar_teclado_pin]], [[fn_app.esqueci_pin_command-a44ca|esqueci_pin_command]], [[fn_app.executar_confirmacao_exclusao-c222c|app.executar_confirmacao_exclusao]], [[fn_app.fechamento_command-07cdf|fechamento_command]], [[fn_app.formato_nao_suportado-ab147|formato_nao_suportado]], [[fn_app.guardar_acao_pendente_pin-68f50|guardar_acao_pendente_pin]], [[fn_app.help_command-cfdad|help_command]], [[fn_app.historico_command-1af15|historico_command]], [[fn_app.inicializar_alertas-42b78|app.inicializar_alertas]], [[fn_app.iniciar_feedback_visual-746ba|app.iniciar_feedback_visual]], [[fn_app.iniciar_fluxo_guiado-16de0|app.iniciar_fluxo_guiado]], [[fn_app.iniciar_reset_pin_guiado-0cbbb|app.iniciar_reset_pin_guiado]] …
- **Gatilhos de texto (145):** [[text___atalho_menu-5b206|ATALHOS_MENU]], [[text___help-1d119|__help__]], [[text_a_pagar-1032e|a pagar]], [[text_agenda-5ce89|agenda]], [[text_agenda_AAAA-MM-73c26|agenda <AAAA-MM>]], [[text_agenda_mes-1-8410f|agenda {mes-1}]], [[text_agenda_mes_1-46f3b|agenda {mes+1}]], [[text_ajustes-6dc04|ajustes]], [[text_alterar_conta_fixo_id_para_conta-6cfaa|alterar conta fixo <id> para <conta>]], [[text_apagar_fixo_id-ae71a|apagar fixo <id>]], [[text_apagar_id-9d0af|apagar <id>]], [[text_aprender-93bdc|aprender]], [[text_aprender_auditoria-045fe|aprender auditoria]], [[text_aprender_caixa-66378|aprender caixa]], [[text_aprender_checklist-e7d23|aprender checklist]], [[text_aprender_conciliação-2409e|aprender conciliação]], [[text_aprender_dados-1877b|aprender dados]], [[text_aprender_faturas-b3297|aprender faturas]], [[text_aprender_lançamentos-898d0|aprender lançamentos]], [[text_aprender_planejamento-d526c|aprender planejamento]], [[text_aprender_previsões-576e7|aprender previsões]], [[text_aprender_primeiros_passos-8ea86|aprender primeiros passos]], [[text_aprender_rotina-208d6|aprender rotina]], [[text_aprender_transferências-7efc1|aprender transferências]], [[text_aprender_tudo-ed148|aprender tudo]], [[text_assessor-a1510|assessor]], [[text_backup-301db|backup]], [[text_backup_automatico-24458|backup automatico]], [[text_bloquear-31a41|bloquear]], [[text_buscar-3a9fd|buscar]] …
- **Botões (174):** [[btn_1..5_id_visual-767ad|1..5 (id visual)]], [[btn_A_pagar_help-796bc|💳 A pagar (help)]], [[btn_Abrir_A_pagar-ece60|🧾 Abrir A pagar]], [[btn_Agenda_geral-7b611|📆 Agenda geral]], [[btn_Agora_não-20c6b|Agora não]], [[btn_Ajuda-7a335|❓ Ajuda]], [[btn_Ajuda-e729d|📘 Ajuda]], [[btn_Ajuda_entradas-bd1c4|⚙️ Ajuda entradas]], [[btn_Ajustes-8142c|⚙️ Ajustes]], [[btn_Alterar_conta-9a995|🏦 Alterar conta]], [[btn_Anterior_conta-0191d|◀️ Anterior (conta)]], [[btn_Anterior_lista-b7750|◀️ Anterior (lista)]], [[btn_Apagar-217f5|🗑 Apagar]], [[btn_Apagar_fixo-2aaee|🗑 Apagar fixo]], [[btn_Aprender-e747c|✅ Aprender]], [[btn_Auditoria-4a1af|🧪 Auditoria]], [[btn_Aula_completa-a8b0c|📚 Aula completa]], [[btn_Backup-91051|💾 Backup]], [[btn_Banco_conta-23963|🏦 Banco/conta]], [[btn_Bancos_parcelas-7a6b7|💳 Bancos/parcelas]], [[btn_Bloquear_agora-bdf62|🔒 Bloquear agora]], [[btn_Buscar-a4d9d|🔎 Buscar]], [[btn_Caixa-b303a|🏦 Caixa]], [[btn_Caixa_help-d0c9d|🏦 Caixa (help)]], [[btn_Caju_VR-4bb6f|🥗 Caju/VR]], [[btn_Cancelar___guiado_cancelar-3c583|✖️ Cancelar [__guiado_cancelar__]]], [[btn_Cancelar_exportação-70835|✖️ Cancelar exportação]], [[btn_Cancelar_fatura-e1ef8|✖️ Cancelar fatura]], [[btn_Cancelar_pin-dc0ab|✖️ Cancelar (pin)]], [[btn_Cancelar_recuperação-c71aa|✖️ Cancelar recuperação]] …

## Documentos que citam

- [[mapa/LEIA-ME]]
- [[reavaliacao/00_veredito]]
- [[reavaliacao/01_arquitetura]]
- [[reavaliacao/03_seguranca_privacidade]]
- [[reavaliacao/07_inventario_gravacao_legado]]
- [[reavaliacao/08_onda3_etapa1]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
