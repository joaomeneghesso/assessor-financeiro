---
tipo: state
arquivo: consulta_cache.py
linha: 12
---
# CONTEXTO_CONSULTA

ContextVar com dict de cache de UMA consulta/renderização; resetado ao sair de contexto_consulta(). Não guarda mês nem persiste entre mensagens.

`state:CONTEXTO_CONSULTA`

## Vem de
- (le_estado) [[fn_services.obter_metricas_resultado_mes-ecfb1|services.obter_metricas_resultado_mes]] _consulta_cache(chave) usa o dict do contexto se existir
- (grava_estado) [[fn_services.obter_metricas_resultado_mes-ecfb1|services.obter_metricas_resultado_mes]] memoriza resultado no cache do contexto atual
- (le_estado) [[fn_services.calcular_saldo_mensal-ab5b8|services.calcular_saldo_mensal]] _consulta_cache(chave) usa o dict do contexto se existir
- (grava_estado) [[fn_services.calcular_saldo_mensal-ab5b8|services.calcular_saldo_mensal]] memoriza resultado no cache do contexto atual
- (le_estado) [[fn_services.calcular_caixa_por_conta_mes-3f8f8|services.calcular_caixa_por_conta_mes]] _consulta_cache(chave) usa o dict do contexto se existir
- (grava_estado) [[fn_services.calcular_caixa_por_conta_mes-3f8f8|services.calcular_caixa_por_conta_mes]] memoriza resultado no cache do contexto atual
- (grava_estado) [[fn_telegram_experiencia.render-aa635|telegram_experiencia.render]] contexto_consulta(): cache efêmero só durante a renderização
- (grava_estado) [[fn_consulta_cache.contexto_consulta-9f519|consulta_cache.contexto_consulta]] set/reset do ContextVar
- (le_estado) [[fn_consulta_cache.obter_ou_calcular-f179b|consulta_cache.obter_ou_calcular]] 
- (grava_estado) [[fn_consulta_cache.obter_ou_calcular-f179b|consulta_cache.obter_ou_calcular]] cache[chave] = copia
