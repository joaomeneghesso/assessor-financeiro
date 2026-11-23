---
name: investigar-bug
description: Fluxo padrão para investigar um bug relatado: reproduzir, achar causa raiz, escrever teste e corrigir. Use quando o usuário descrever um sintoma do assessor (saldo errado, botão que falha, lançamento estranho).
---
# Investigar bug

Regra de ouro: **nenhuma correção antes de achar a causa raiz.** Corrigir o sintoma ("ajusta o número na tela") esconde o defeito e cria outro. Se faltar a causa, diga isso ao titular em vez de chutar.

## Fase 1 — Entender e reproduzir
1. Registre o sintoma, o esperado e como aconteceu: a mensagem exata do Telegram, os valores, as datas, o mês da tela e a conta, forma e cartão envolvidos.
2. Leia a mensagem de erro ou o log inteiro antes de supor qualquer coisa. No servidor: `journalctl -u assessor -n 100`, só leitura.
3. Reproduza em banco temporário. Nunca use `data/financeiro.db`. Para dado real, use o MCP `assessor-db` (só leitura) ou uma cópia temporária.
4. Se não reproduzir, não corrija. Junte mais dados (pergunte ao titular o passo a passo exato) até reproduzir.
5. Confira o que mudou por último: `git log -5 --stat` e o `CHANGELOG.md`. Bug novo costuma vir de mudança recente.

## Fase 2 — Comparar com o que funciona
6. Ache um caso parecido que funciona (outro cartão, outro mês, outra forma de pagamento) e liste as diferenças, sem descartar nenhuma como "irrelevante" de cara.
7. Consulte o mapa de rotas (`docs/mapa/`) e a nota do módulo em `docs/codigo/modulos/` para ver quem chama o quê. Nos pontos frágeis conhecidos (`Session.month`, competência de fatura com corte inclusivo, conta × forma × destino, conciliação que falha fechado, herança só do realizado), confira as regras no `CLAUDE.md`.
8. Para diagnóstico longo, delegue ao subagente `cacador-de-bugs` (ou `auditor-financeiro` / `auditor-telegram`, conforme a área), passando o sintoma e o que já foi descartado.

## Fase 3 — Hipótese e teste
9. Escreva **uma** hipótese por vez: "a causa é X porque Y".
10. Escreva o teste de regressão que reproduz o bug **e falha** (`tests/test_<tema>_<versao>.py`, com `tests/relogio_fixo.data_fixa` se depender de data). Rode-o e veja falhar pelo motivo certo.
11. Se a hipótese cair, volte à Fase 1 com o que aprendeu. Não empilhe correções.
12. **Três tentativas de correção sem sucesso = pare.** Provavelmente o problema é de desenho, não de linha. Explique ao titular o que foi visto e as opções antes de seguir.

## Fase 4 — Corrigir e provar
13. Corrija com a menor mudança, na causa raiz. Não refatore junto. Respeite a linha de base (`telegram_experiencia.py`, `services.py`, `database.py` e `app.py` não crescem).
14. Rode o teste novo (agora passa) e depois o gate inteiro (skill `rodar-gate`).
15. Antes de dizer "corrigido", siga a skill `verificar-antes-de-concluir`.
16. Se o bug revelou uma regra não óbvia, salve em memória (tipo project ou feedback). Anote no `CHANGELOG.md` ao fechar (skill `fechar-versao`).
