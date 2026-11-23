---
tipo: service
arquivo: services.py
linha: 7895
---
# services._preparar_movimento_fatura_sessao

Função de negócio (destino de roteamento).

`fn:services._preparar_movimento_fatura_sessao`

## Vai para
- (grava_estado) [[state_PENDENCIAS_PAGAMENTO_FATURA-2f592|PENDENCIAS_PAGAMENTO_FATURA]] 

## Vem de
- (chama) [[text_estorno_crédito_abatimento_reembolso_valor_na_fatura_conta-d1c20|estorno|crédito|abatimento|reembolso <valor> na fatura <conta>]] 
- (chama) [[text_paguei_valor_da_fatura_conta_usando_origem-f02dc|paguei <valor> da fatura <conta> usando <origem>]] 
- (chama) [[text_paguei_o_restante_da_fatura_conta_usando_origem-9db49|paguei o restante da fatura <conta> usando <origem>]] 
