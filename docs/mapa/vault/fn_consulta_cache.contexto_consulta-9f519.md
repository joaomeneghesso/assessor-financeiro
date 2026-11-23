---
tipo: service
arquivo: consulta_cache.py
linha: 16
---
# consulta_cache.contexto_consulta

Context manager: cria dict de cache se não houver; reset ao sair. Aninhado reutiliza o externo.

`fn:consulta_cache.contexto_consulta`

## Vai para
- (grava_estado) [[state_CONTEXTO_CONSULTA-83d77|CONTEXTO_CONSULTA]] set/reset do ContextVar

## Vem de
- (chama) [[mod_consulta_cache.py-c7d10|consulta_cache.py]] 
- (chama) [[fn_telegram_experiencia.render-aa635|telegram_experiencia.render]] telegram_experiencia.py:601
- (chama) [[fn_dashboard_metricas.enriquecer-42163|dashboard_metricas.enriquecer]] 21
- (chama) [[fn_telegram_recursos.dispatch-a2ef9|telegram_recursos.dispatch]] 69, 108
