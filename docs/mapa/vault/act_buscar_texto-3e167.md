---
tipo: action
arquivo: telegram_experiencia.py
linha: 2969
---
# buscar_texto

Texto "buscar/procurar/pesquisar <termo> [período]": busca em todos os meses (busca_lancamentos).

`act:buscar_texto`

## Vai para
- (chama) [[fn_busca_lancamentos.dispatch-39750|busca_lancamentos.dispatch]] 
- (chama) [[fn_ux._apply_privacy-1d25f|ux._apply_privacy]] 
- (grava_estado) [[state_Session.search-c5f30|Session.search]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (chama) [[fn_ux._rota_frase_natural-c0a82|ux._rota_frase_natural]] buscar <termo>
