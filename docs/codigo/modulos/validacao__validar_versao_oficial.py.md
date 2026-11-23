---
tipo: modulo
grupo: Ferramentas e validação
linhas: 221
tags: [modulo, ferramentas-e-validacao]
aliases: [validacao/validar_versao_oficial.py]
---
# validacao/validar_versao_oficial.py

> Gate de release: código copiado, banco temporário e rede externa bloqueada.

**Grupo:** [[Ferramentas e validação]] · **Linhas:** 221 · **Funções:** 9 · **Classes:** 0

## Usa

- (nenhum módulo do projeto)

## Usado por

- (ninguém no código de produção; ponto de entrada ou script)

## Tudo que define

- `listar_modulos` (L62, 7 linhas) — Mesma lista que o discover do harness carregava: tests/, testes_v39/ e test_rc307_deduplicacao.
- `testes_do_modulo` (L74, 6 linhas) — Ids 'modulo.Classe.test_x' dos métodos definidos diretamente em cada classe (AST, sem importar).
- `dividir_pesados` (L81, 9 linhas) — Troca cada módulo de DIVIDIR_POR_TESTE por seus testes, repartindo o peso.
- `pesos_modulos` (L91, 7 linhas)
- `particionar` (L99, 6 linhas) — Guloso: do mais pesado ao mais leve, sempre no lote de menor carga. Retorna n listas (podem ficar vazias).
- `agregar` (L106, 13 linhas) — Soma os resultado.json dos workers; resultado ausente conta como erro.
- `matar_arvore` (L120, 9 linhas) — Encerra só o processo que este gate iniciou (e seus filhos), sempre pelo PID.
- `criar_parser` (L130, 9 linhas)
- `main` (L140, 80 linhas)

## Documentos que citam

- [[OPERACAO]]
- [[reavaliacao/01_arquitetura]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
