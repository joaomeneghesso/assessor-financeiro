---
tipo: modulo
grupo: Camada de negócio e interpretação
linhas: 11767
tags: [modulo, camada-de-negocio-e-interpretacao]
---
# services.py

**Grupo:** [[Camada de negócio e interpretação]] · **Linhas:** 11767 · **Funções:** 359 · **Classes:** 1

> [!warning] Linha de base
> Limite de 11767 linhas (hoje 11767). Este arquivo não pode crescer: código novo vai em módulo próprio.

## Usa

- [[assessor.py]]
- [[backup_externo.py]] *(importação tardia, dentro de função)*
- [[categorias.py]]
- [[categorias_pessoais.py]] *(importação tardia, dentro de função)*
- [[compromissos.py]] *(importação tardia, dentro de função)*
- [[conciliacao.py]] *(importação tardia, dentro de função)*
- [[config.py]]
- [[consulta_cache.py]]
- [[database.py]] *(importação tardia, dentro de função)*
- [[faturas_competencia.py]]
- [[fixos_edicao.py]] *(importação tardia, dentro de função)*
- [[fixos_vigencia.py]] *(importação tardia, dentro de função)*
- [[money.py]] *(importação tardia, dentro de função)*
- [[parser_financeiro.py]]
- [[relogio.py]]
- [[reservas_faturas.py]] *(importação tardia, dentro de função)*
- [[roteamento_seguro.py]] *(importação tardia, dentro de função)*
- [[sugestoes_comando.py]] *(importação tardia, dentro de função)*
- [[transcricao_audio.py]] *(importação tardia, dentro de função)*
- [[version.py]]

## Usado por

- [[app.py]] — `_obter_pendencia`, `_parse_apagar_data_pagamento`, `assinatura_pendencia`, `criar_backup_pre_exclusao`, `executar_exclusao_confirmada`, `existe_backup_diario_hoje`, `exportacao_exige_pin`, `normalizar_comando_sinonimos` +4
- [[assessor_orientacao.py]] — `obter_metricas_resultado_mes`
- [[backup_externo_cli.py]] — `criar_backup_db`
- [[busca_lancamentos.py]] — `normalizar_busca_texto`, `transacao_contem_termo`
- [[consultas_pagar.py]] — `aplicar_status_checklist`, `montar_itens_checklist_mes`, `normalizar_busca_texto`
- [[dashboard_metricas.py]]
- [[efeito_baixa.py]] — `calcular_caixa_por_conta_mes`, `normalizar_busca_texto`, `obter_metricas_resultado_mes`
- [[fatura_conferencia.py]] — `mesma_conta_saldo`
- [[reservas_faturas.py]] — `mesma_conta_saldo`, `pagamentos_fatura_posteriores`, `transacao_afeta_saldo_disponivel`
- [[saldos_edicao.py]] — `calcular_caixa_por_conta_mes`, `mesma_conta_saldo`, `normalizar_conta_caixa`
- [[telegram_experiencia.py]] — `_limpar_pendencia`, `_obter_pendencia`, `aplicar_status_checklist`, `cadastrar_fixo_guiado`, `calcular_caixa_por_conta_mes`, `calcular_resumo_fatura`, `conta_centraliza_fluxo_mensal`, `conta_virtual_caixa` +22
- [[telegram_midia.py]] — `mesma_conta_saldo`, `parsear_comando_transferencia_caixa`
- [[telegram_recursos.py]] — `calcular_resumo_fatura`, `obter_metricas_resultado_mes`, `resolver_item_checklist`
- [[telegram_registros.py]] — `calcular_resumo_fatura`, `mesma_conta_saldo`, `nome_conta_fatura_padrao`, `normalizar_conta_caixa`
- [[tools__medir_desempenho.py|tools/medir_desempenho.py]]

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `mesma_conta_saldo` | 1965 | 6 | 1 |  |
| `obter_metricas_resultado_mes` | 4701 | 4 | 20 |  |
| `calcular_caixa_por_conta_mes` | 11753 | 3 | 14 |  |
| `calcular_resumo_fatura` | 7712 | 3 | 4 |  |
| `normalizar_busca_texto` | 11077 | 3 | 0 |  |
| `normalizar_conta_caixa` | 3528 | 3 | 0 | Para caixa, Pix/débito/dinheiro/transferência não são contas. |
| `processar_mensagem` | 11762 | 2 | 25 |  |
| `montar_itens_checklist_mes` | 5419 | 2 | 11 |  |
| `_obter_pendencia` | 319 | 2 | 3 |  |
| `aplicar_status_checklist` | 5595 | 2 | 3 |  |
| `parsear_comando_transferencia_caixa` | 3629 | 2 | 0 |  |
| `resolver_item_checklist` | 5640 | 2 | 0 |  |
| `transacao_afeta_saldo_disponivel` | 1983 | 2 | 0 |  |
| `criar_backup_db` | 10774 | 1 | 3 |  |
| `cadastrar_fixo_guiado` | 211 | 1 | 2 | Cadastra um fixo com campos explícitos; não cria transação/despesa. |
| `executar_exclusao_confirmada` | 8073 | 1 | 2 | Executa uma exclusão já prévia-validada e confirmada pelo titular. |
| `exportacao_exige_pin` | 434 | 1 | 2 | True se o texto pede exportar mais que o limite sem PIN (ou a base inteira). |
| `formatar_moeda` | 360 | 1 | 2 |  |
| `assinatura_pendencia` | 334 | 1 | 1 | Identifica a prévia pendente atual (fatura, exclusão ou importação). |
| `conta_centraliza_fluxo_mensal` | 1922 | 1 | 1 |  |
| `criar_backup_pre_exclusao` | 10797 | 1 | 1 | Backup obrigatório antes de apagar: devolve o caminho ou levanta erro. |
| `existe_backup_diario_hoje` | 10808 | 1 | 1 | True se já existe backup diário com data de hoje (relógio local). |
| `normalizar_comando_sinonimos` | 6491 | 1 | 1 | Converte sinônimos comuns para comandos canônicos antes do parser financeiro. |
| `parsear_comando_entrada_avulsa` | 1116 | 1 | 1 |  |
| `parsear_comando_movimento_fatura` | 7970 | 1 | 1 |  |

## Tudo que define

360 definições; as 40 maiores:

- `_processar_mensagem_core` (L8670, 1096 linhas)
- `_calcular_saldo_mensal_etapa` (L2480, 386 linhas)
- `normalizar_comando_sinonimos` (L6491, 203 linhas) — Converte sinônimos comuns para comandos canônicos antes do parser financeiro.
- `gerar_auditoria_resultado_mes_ux` (L4778, 194 linhas) — Explica, item a item, a formação do resultado operacional do mês.
- `montar_itens_checklist_mes` (L5419, 174 linhas)
- `preparar_previa_exclusao` (L6731, 157 linhas)
- `gerar_revisao_inteligente` (L1755, 152 linhas)
- `gerar_dashboard_categorias_visual_mes` (L3283, 148 linhas)
- `gerar_compromissos_ux` (L5050, 146 linhas) — Visão operacional do que ainda pesa no mês.
- `gerar_dashboard_visual_mes` (L3098, 140 linhas)
- `gerar_checklist_pagamentos` (L6001, 138 linhas)
- `previa_alteracao` (L8200, 131 linhas) — Prévia (antes → depois) de um comando de texto que altera dados.
- `movimentacoes_conta_mes_formatado` (L7196, 110 linhas)
- `gerar_auditoria_despesas_mes` (L2903, 103 linhas)
- `definir_saldo_inicial_formatado` (L4341, 92 linhas)
- `registrar_compra_parcelada` (L10947, 92 linhas)
- `_calcular_caixa_por_conta_etapa` (L3855, 91 linhas) — Calcula caixa por conta/banco de forma conservadora.
- `gerar_caixa_por_conta_mes` (L3948, 91 linhas) — Mostra dinheiro em caixa por banco/conta.
- `parsear_comando_saldo_inicial` (L4443, 88 linhas)
- `extrato_conta_mes_formatado` (L7060, 88 linhas)
- `definir_data_pagamento_checklist_formatado` (L5769, 85 linhas)
- `exportar_csv_periodo` (L10602, 85 linhas)
- `montar_contexto_financeiro` (L9857, 83 linhas) — Monta o contexto usado pelo modo assessor e pelo fechamento mensal.
- `cadastrar_fixo_guiado` (L211, 82 linhas) — Cadastra um fixo com campos explícitos; não cria transação/despesa.
- `gerar_saldo_mes_ux` (L4073, 81 linhas)
- `parsear_comando_entrada_avulsa` (L1116, 73 linhas)
- `_receitas_previstas_herdadas` (L2406, 72 linhas) — Receitas previstas de meses anteriores ainda não recebidas em ``ano_mes``.
- `_calcular_metricas_resultado_mes` (L4628, 71 linhas)
- `gerar_status` (L10433, 71 linhas)
- `parsear_comando_novo_fixo` (L1203, 68 linhas)
- `_definir_saldo_inicial_conta_herdada` (L4189, 64 linhas) — Define o saldo inicial de UMA conta em mês que herda o saldo.
- `definir_vencimento_fatura_por_nome_formatado` (L5704, 63 linhas) — Configura vencimento mensal ou recorrente usando o nome do cartão.
- `detalhar_item_checklist_formatado` (L6140, 63 linhas)
- `gerar_relatorio_mes` (L10506, 63 linhas)
- `gerar_pendencias_abertas_formatado` (L2300, 61 linhas)
- `revisar_categorias_suspeitas` (L1465, 60 linhas)
- `marcar_itens_checklist_formatado` (L6320, 58 linhas)
- `parsear_comando_movimento_fatura` (L7970, 58 linhas)
- `construir_grupos_parcelamentos` (L10012, 55 linhas)
- `gerar_resumo_mes` (L11286, 55 linhas)

## Testes que usam (93)

- `tests/__init__.py`
- `tests/conftest.py`
- `tests/test_ajustar_saldo_seletor.py`
- `tests/test_alertas_fase1.py`
- `tests/test_auditoria_resultado_mes_rc152.py`
- `tests/test_backup_externo.py`
- `tests/test_baixa_fixo_conta.py`
- `tests/test_bloco_a_protecao_dados.py`
- `tests/test_bloco_b_complementos.py`
- `tests/test_bloco_b_datas_comandos.py`
- `tests/test_bloco_b_fatura_telas.py`
- `tests/test_bloco_b_saldos_pagamentos.py`
- `tests/test_bloco_c_auditoria.py`
- `tests/test_bloco_c_ciclo_vida.py`
- `tests/test_bloco_d_usabilidade.py`
- `tests/test_botoes_confirmacao.py`
- `tests/test_botoes_finais_regressao.py`
- `tests/test_busca_lancamentos.py`
- `tests/test_categorizacao_unificada.py`
- `tests/test_checklist_compatibilidade_legada.py`
- … +73

## No mapa de rotas

- **Módulo (1):** [[mod_services.py-b3de3|services.py]]
- **Estado da sessão (8):** [[state__ALTERACAO_CONFIRMADA-fe9b4|_ALTERACAO_CONFIRMADA]], [[state__CONTEXTO_HERANCA-4e486|_CONTEXTO_HERANCA]], [[state__EXCLUSAO_CONFIRMADA-6a03b|_EXCLUSAO_CONFIRMADA]], [[state_PENDENCIAS_ALTERACAO-e88b3|PENDENCIAS_ALTERACAO]], [[state_PENDENCIAS_CONFIRMACAO-76a92|PENDENCIAS_CONFIRMACAO]], [[state_PENDENCIAS_EXPORTACAO-908bd|PENDENCIAS_EXPORTACAO]], [[state_PENDENCIAS_IMPORTACAO-26caf|PENDENCIAS_IMPORTACAO]], [[state_PENDENCIAS_PAGAMENTO_FATURA-2f592|PENDENCIAS_PAGAMENTO_FATURA]]
- **Funções no mapa (143):** [[fn_services._avaliar_heranca-4ea4d|services._avaliar_heranca]], [[fn_services._bloqueio_parcela_isolada-acc72|services._bloqueio_parcela_isolada]], [[fn_services._chave_sessao-9a5da|services._chave_sessao]], [[fn_services._limpar_pendencia-91039|services._limpar_pendencia]], [[fn_services._obter_pendencia-ef8f7|services._obter_pendencia]], [[fn_services._preparar_alteracao_sessao-a37a4|services._preparar_alteracao_sessao]], [[fn_services._preparar_exclusao_sessao-b1879|services._preparar_exclusao_sessao]], [[fn_services._preparar_movimento_fatura_sessao-44ad5|services._preparar_movimento_fatura_sessao]], [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]], [[fn_services.analisar_compra-ef5f7|services.analisar_compra]], [[fn_services.analisar_csv_importacao-744a8|services.analisar_csv_importacao]], [[fn_services.apagar_data_pagamento_checklist_formatado-1db1a|services.apagar_data_pagamento_checklist_formatado]], [[fn_services.apagar_meta_formatado-6b1a5|services.apagar_meta_formatado]], [[fn_services.apagar_movimento_fatura_formatado-e829c|services.apagar_movimento_fatura_formatado]], [[fn_services.apagar_parcelamento_unificado-84a14|services.apagar_parcelamento_unificado]], [[fn_services.apagar_por_faixa-66240|services.apagar_por_faixa]], [[fn_services.apagar_por_id-de484|services.apagar_por_id]], [[fn_services.apagar_transferencia_caixa_formatado-0ebad|services.apagar_transferencia_caixa_formatado]], [[fn_services.apagar_ultimo-34edd|services.apagar_ultimo]], [[fn_services.aplicar_correcao_categoria_transacao-436fd|services.aplicar_correcao_categoria_transacao]], [[fn_services.aplicar_status_checklist-8e28a|services.aplicar_status_checklist]], [[fn_services.bloco_heranca_mes_anterior-6a843|services.bloco_heranca_mes_anterior]], [[fn_services.buscar_transacao_detalhada_formatado-fa62f|services.buscar_transacao_detalhada_formatado]], [[fn_services.buscar_transacoes_formatado-21d9c|services.buscar_transacoes_formatado]], [[fn_services.calcular_caixa_por_conta_mes-3f8f8|services.calcular_caixa_por_conta_mes]], [[fn_services.calcular_resumo_fatura-b4797|services.calcular_resumo_fatura]], [[fn_services.calcular_saldo_mensal-ab5b8|services.calcular_saldo_mensal]], [[fn_services.cancelar_alteracao_pendente-4e9a5|services.cancelar_alteracao_pendente]], [[fn_services.cancelar_exclusao_pendente-f7c25|services.cancelar_exclusao_pendente]], [[fn_services.cancelar_lancamento_pendente-41125|services.cancelar_lancamento_pendente]] …
- **Chamadas de serviço (8):** [[fn_services.cadastrar_fixo_guiado-6e117|cadastrar_fixo_guiado]], [[fn_services.conta_centraliza_fluxo_mensal-c7415|services.conta_centraliza_fluxo_mensal]], [[fn_services.item_checklist_eh_credito_individual-ab4d0|item_checklist_eh_credito_individual]], [[fn_services.listar_pendencias_abertas_anteriores-9817a|listar_pendencias_abertas_anteriores]], [[fn_services.listar_revisoes_baixas_anteriores-ea7e8|listar_revisoes_baixas_anteriores]], [[fn_services.normalizar_conta_caixa-773c5|services.normalizar_conta_caixa]], [[fn_services.resolver_fatura_checklist_por_nome-14c94|resolver_fatura_checklist_por_nome]], [[fn_services.slug_banco_checklist-ba1f3|services.slug_banco_checklist]]
- **Tratadores (4):** [[fn_services.criar_backup_pre_exclusao-6cdc5|services.criar_backup_pre_exclusao]], [[fn_services.executar_exclusao_confirmada-c9366|services.executar_exclusao_confirmada]], [[fn_services.preparar_previa_exclusao-a7664|services.preparar_previa_exclusao]], [[fn_services.processar_mensagem-0f752|services.processar_mensagem]]
- **Gatilhos de texto (132):** [[text_agenda_aaaa-mm-336aa|agenda <aaaa-mm>]], [[text_alterar_categoria_fixo_compromisso_parcela_id_para_cat-25dd4|alterar categoria <fixo|compromisso|parcela> <id> para <cat>]], [[text_alterar_conta_fixo_compromisso_parcela_id_para_conta-57c4f|alterar conta <fixo|compromisso|parcela> <id> para <conta>]], [[text_alterar_conta_id_para_conta_lançamento-afdda|alterar conta <id> para <conta> (lançamento)]], [[text_alterar_entrada_id_para_valor-f27ee|alterar entrada <id> para <valor>]], [[text_alterar_fixo_id_para_valor-4c93f|alterar fixo <id> para <valor>]], [[text_alterar_forma_fixo_compromisso_parcela_id_para_forma-b1c43|alterar forma <fixo|compromisso|parcela> <id> para <forma>]], [[text_alterar_forma_id_para_forma_lançamento-156be|alterar forma <id> para <forma> (lançamento)]], [[text_alterar_término_fixo_id_para_sem_término-e559b|alterar término fixo <id> para sem término]], [[text_alterar_vencimento_fixo_id_para_dia_d-956bf|alterar vencimento fixo <id> para [dia] <d>]], [[text_analisar_csv_importar_csv_prever_importação-0b8cd|analisar csv|importar csv|prever importação]], [[text_apagar_entrada_id-51fbe|apagar entrada <id>]], [[text_apagar_excluir_deletar_remover_alvo_destrutivo-5f0eb|apagar|excluir|deletar|remover <alvo> (destrutivo)]], [[text_apagar_fixo_compromisso_id-16849|apagar fixo|compromisso <id>]], [[text_apagar_id_-_id-9e912|apagar <id>-<id>]], [[text_apagar_meta_categoria-be042|apagar meta <categoria>]], [[text_apagar_movimento_f_id-07be4|apagar movimento #f<id>]], [[text_apagar_parcelamento_id-06913|apagar parcelamento <id>]], [[text_apagar_transferência_caixa_id-550b5|apagar transferência caixa <id>]], [[text_apagar_vencimento_fixo_código_aaaa-mm-3e45e|apagar vencimento fixo <código> [aaaa-mm]]], [[text_apagar_último-72f84|apagar último]], [[text_aprender_aula_treinamento_manual_tutorial_guia_tópico-bcb0b|aprender|aula|treinamento|manual|tutorial|guia [tópico]]], [[text_auditar_mês_aaaa-mm-ebb72|auditar mês [aaaa-mm]]], [[text_auditoria_despesas_aaaa-mm-9ab1b|auditoria despesas [aaaa-mm]]], [[text_backup_automático-d5735|backup automático]], [[text_buscar_termo-e72a3|buscar <termo>]], [[text_buscar_termo_pagina_n-a6aa2|buscar <termo> pagina <n>]], [[text_caixa_meu_caixa_caixa_por_conta_saldo_das_contas_meu_dinheiro_aaaa-mm-68dac|caixa|meu caixa|caixa por conta|saldo das contas|meu dinheiro [aaaa-mm]]], [[text_cancelar-f5cad|cancelar]], [[text_cancelar_alteracao-64585|cancelar alteracao]] …
- **Apelidos de comando (31):** [[alias_ajustar_valor_id_para_v-0a7a4|alterar|ajustar valor <id> para <v> -> corrigir <id> para <v>]], [[alias_cancelar_fixo_compromisso_id-cd917|cancelar fixo|compromisso <id>]], [[alias_cancelar_parcelamento_parcela_id-8b140|cancelar parcelamento|parcela <id>]], [[alias_criar_entrada_fixa_...-2f3a4|cadastrar|adicionar|incluir|criar entrada fixa <...> -> nova entrada fixa <...>]], [[alias_criar_fixo_...-6a30b|cadastrar|adicionar|incluir|criar fixo <...> -> novo fixo <...>]], [[alias_deletar_entrada_receita_id-2a794|deletar entrada|receita <id> -> apagar entrada <id>]], [[alias_deletar_fixo_compromisso_id-c42e6|apagar|excluir|deletar|remover|tirar|cancelar fixo|compromisso <id> -> apagar fixo|compromisso <id>]], [[alias_deletar_id_-_id-9bfae|deletar <id>-<id> -> apagar <id>-<id>]], [[alias_deletar_lançamento_transação_id_deletar_id-65ad1|deletar lançamento|transação|movimentação <id> ou <id> -> apagar <id>]], [[alias_deletar_meta_cat-2607a|deletar meta <cat> -> apagar meta <cat>]], [[alias_deletar_parcelamento_parcela_id-ec4e9|deletar/cancelar parcelamento|parcela <id> -> apagar parcelamento <id>]], [[alias_editar_categoria_id_para_cat-cbf45|editar categoria <id> para <cat> -> mudar <id> para <cat>]], [[alias_editar_vencimento_fixo_id_para_dia_n-75859|editar vencimento fixo <id> -> alterar vencimento fixo <id> para dia <n>]], [[alias_retomar_entrada_receita_id-fd15f|reativar|ativar|retomar|religar|voltar entrada|receita <id> -> reativar entrada <id>]], [[alias_retomar_fixo_compromisso_id-8cacd|reativar|ativar|retomar|religar|voltar fixo|compromisso <id> -> reativar ...]], [[alias_suspender_entrada_receita_id-09eda|pausar|suspender|desativar|parar|congelar entrada|receita <id> -> pausar entrada <id>]], [[alias_suspender_fixo_compromisso_id-4f685|pausar|suspender|desativar|parar|congelar fixo|compromisso <id> -> pausar ...]], [[alias_trocar_categoria_fixo_id_por_x-48062|... categoria ... -> alterar categoria <tipo> <id> para <x>]], [[alias_trocar_conta_fixo_id_por_x-6c7a9|alterar|mudar|trocar|editar|ajustar|atualizar conta ... -> alterar conta <tipo> <id> para <x>]], [[alias_trocar_forma_fixo_id_por_x-98e2b|... forma ... -> alterar forma <tipo> <id> para <x>]], [[alias_ver_agenda-a1e70|ver agenda -> agenda]], [[alias_ver_categoria_s-9a983|ver categoria(s) -> categorias]], [[alias_ver_compromisso_s-6a78f|ver compromisso(s)/compromissos gerais -> compromissos]], [[alias_ver_conta_s-c11a9|ver conta(s) -> contas]], [[alias_ver_entrada_s_receita_s-62b1e|ver entrada(s)/receita(s) -> entradas]], [[alias_ver_fixo_s-17416|ver|listar|mostrar|consultar|abrir|exibir fixo(s) -> fixos]], [[alias_ver_forma_s-0c712|ver forma(s) -> formas]], [[alias_ver_nome_aaaa-mm-3737e|ver fixos|entradas|receitas|categorias|contas|formas|parcelas|agenda|compromissos <aaaa-mm>]], [[alias_ver_parcela_s_parcelamento_s-534eb|ver parcela(s)/parcelamento(s) -> parcelamentos]], [[alias_ver_últimas_n-033b8|ver últimas <n> -> últimas <n>]] …

## Documentos que citam

- [[mapa/LEIA-ME]]
- [[reavaliacao/00_veredito]]
- [[reavaliacao/01_arquitetura]]
- [[reavaliacao/03_seguranca_privacidade]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
