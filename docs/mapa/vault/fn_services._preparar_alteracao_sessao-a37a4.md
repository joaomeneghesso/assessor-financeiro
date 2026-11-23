---
tipo: service
arquivo: services.py
linha: 8321
---
# services._preparar_alteracao_sessao

Guarda {comando, prévia} em PENDENCIAS_ALTERACAO e devolve a prévia com instrução 'confirmar alteracao'; prévia bloqueada não gera pendência.

`fn:services._preparar_alteracao_sessao`

## Vai para
- (grava_estado) [[state_PENDENCIAS_ALTERACAO-e88b3|PENDENCIAS_ALTERACAO]] define pendência (prévia antes → depois)

## Vem de
- (chama) [[text_prévia_de_alteração_digitada_mudar_corrigir_meta_fixos_entradas...-27bdc|prévia de alteração digitada (mudar|corrigir|meta|fixos|entradas...)]] 
