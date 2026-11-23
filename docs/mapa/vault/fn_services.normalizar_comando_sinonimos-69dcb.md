---
tipo: service
arquivo: services.py
linha: 6479
---
# services.normalizar_comando_sinonimos

Converte sinônimos (ver/listar/deletar/trocar/pausar/criar...) em comando canônico antes do roteamento; só com alvo claro.

`fn:services.normalizar_comando_sinonimos`

## Vai para
- (chama) [[alias_ver_fixo_s-17416|ver|listar|mostrar|consultar|abrir|exibir fixo(s) -> fixos]] services.py:6534
- (chama) [[alias_ver_compromisso_s-6a78f|ver compromisso(s)/compromissos gerais -> compromissos]] services.py:6534
- (chama) [[alias_ver_parcela_s_parcelamento_s-534eb|ver parcela(s)/parcelamento(s) -> parcelamentos]] services.py:6534
- (chama) [[alias_ver_entrada_s_receita_s-62b1e|ver entrada(s)/receita(s) -> entradas]] services.py:6534
- (chama) [[alias_ver_categoria_s-9a983|ver categoria(s) -> categorias]] services.py:6534
- (chama) [[alias_ver_conta_s-c11a9|ver conta(s) -> contas]] services.py:6534
- (chama) [[alias_ver_forma_s-0c712|ver forma(s) -> formas]] services.py:6534
- (chama) [[alias_ver_agenda-a1e70|ver agenda -> agenda]] services.py:6534
- (chama) [[alias_ver_últimas_últimos_últimas_transações-80712|ver últimas/últimos/últimas transações -> últimas 10]] services.py:6534
- (chama) [[alias_ver_últimas_n-033b8|ver últimas <n> -> últimas <n>]] services.py:6538
- (chama) [[alias_ver_nome_aaaa-mm-3737e|ver fixos|entradas|receitas|categorias|contas|formas|parcelas|agenda|compromissos <aaaa-mm>]] services.py:6548
- (chama) [[alias_deletar_fixo_compromisso_id-c42e6|apagar|excluir|deletar|remover|tirar|cancelar fixo|compromisso <id> -> apagar fixo|compromisso <id>]] services.py:6558
- (chama) [[alias_deletar_entrada_receita_id-2a794|deletar entrada|receita <id> -> apagar entrada <id>]] services.py:6563
- (chama) [[alias_deletar_parcelamento_parcela_id-ec4e9|deletar/cancelar parcelamento|parcela <id> -> apagar parcelamento <id>]] services.py:6568
- (chama) [[alias_deletar_lançamento_transação_id_deletar_id-65ad1|deletar lançamento|transação|movimentação <id> ou <id> -> apagar <id>]] services.py:6573
- (chama) [[alias_deletar_id_-_id-9bfae|deletar <id>-<id> -> apagar <id>-<id>]] services.py:6583
- (chama) [[alias_deletar_meta_cat-2607a|deletar meta <cat> -> apagar meta <cat>]] services.py:6588
- (chama) [[alias_trocar_conta_fixo_id_por_x-6c7a9|alterar|mudar|trocar|editar|ajustar|atualizar conta ... -> alterar conta <tipo> <id> para <x>]] services.py:6610
- (chama) [[alias_trocar_forma_fixo_id_por_x-98e2b|... forma ... -> alterar forma <tipo> <id> para <x>]] services.py:6618
- (chama) [[alias_trocar_categoria_fixo_id_por_x-48062|... categoria ... -> alterar categoria <tipo> <id> para <x>]] services.py:6626
- (chama) [[alias_editar_vencimento_fixo_id_para_dia_n-75859|editar vencimento fixo <id> -> alterar vencimento fixo <id> para dia <n>]] services.py:6634
- (chama) [[alias_ajustar_valor_id_para_v-0a7a4|alterar|ajustar valor <id> para <v> -> corrigir <id> para <v>]] services.py:6639
- (chama) [[alias_editar_categoria_id_para_cat-cbf45|editar categoria <id> para <cat> -> mudar <id> para <cat>]] services.py:6644
- (chama) [[alias_suspender_fixo_compromisso_id-4f685|pausar|suspender|desativar|parar|congelar fixo|compromisso <id> -> pausar ...]] services.py:6654
- (chama) [[alias_suspender_entrada_receita_id-09eda|pausar|suspender|desativar|parar|congelar entrada|receita <id> -> pausar entrada <id>]] services.py:6658
- (chama) [[alias_retomar_fixo_compromisso_id-8cacd|reativar|ativar|retomar|religar|voltar fixo|compromisso <id> -> reativar ...]] services.py:6662
- (chama) [[alias_retomar_entrada_receita_id-fd15f|reativar|ativar|retomar|religar|voltar entrada|receita <id> -> reativar entrada <id>]] services.py:6666
- (chama) [[alias_criar_fixo_...-6a30b|cadastrar|adicionar|incluir|criar fixo <...> -> novo fixo <...>]] services.py:6674
- (chama) [[alias_criar_entrada_fixa_...-2f3a4|cadastrar|adicionar|incluir|criar entrada fixa <...> -> nova entrada fixa <...>]] services.py:6679
- (chama) [[alias_cancelar_fixo_compromisso_id-cd917|cancelar fixo|compromisso <id>]] services.py:6593
- (chama) [[alias_cancelar_parcelamento_parcela_id-8b140|cancelar parcelamento|parcela <id>]] services.py:6597

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] 8517
- (chama) [[fn_services.preparar_previa_exclusao-a7664|services.preparar_previa_exclusao]] 6720
- (chama) [[fn_services.comando_destrutivo_exclusao-4cbe5|services.comando_destrutivo_exclusao]] 6934
- (chama) [[mod_services.py-b3de3|services.py]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] auxiliar de normalização/validação
