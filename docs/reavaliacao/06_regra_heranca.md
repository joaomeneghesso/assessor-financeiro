# Reavaliação 06 — Regra de herança de saldo (09/11/2026)

Decisão do titular, implementada na frente "Corretude financeira" (corrige D1 de `02_corretude_financeira.md`).

## Regra

Quando um mês não tem saldo confirmado pelo titular, ele começa com o que sobrou do mês anterior. Esse valor herdado mostra **só o que existe**:

- **Receita prevista e não recebida não vira saldo.** Antes, o "saldo livre provável" do mês anterior era herdado inteiro, e um freela previsto de R$ 400 que não chegou aparecia em "Saldo agora" do mês seguinte.
- Essa receita aparece **separada**, no Início e no Saldo: "⏳ Previsto de Outubro 2026 não recebido · R$ 400,00", com a orientação de registrar o recebimento vinculado à previsão ou encerrar a previsão. Nada é gravado sozinho.
- A projeção ("Deve sobrar") **continua contando** o que ainda é esperado, **uma vez só**. O "A receber" inclui esse valor (`a_receber_herdado` em `saldo_resumo.resumir_saldo`), de modo que saldo + a receber − reservas = previsão continua fechando.
- Quando o titular lança o recebimento:
  - **Com vínculo** à previsão: entra uma vez, como entrada realizada. O previsto herdado zera e não há mais compensação na herança.
  - **Sem vínculo**, com o mesmo nome e a mesma conta: fica no saldo, sai da projeção (para não contar em dobro) e vira uma revisão "Receita e previsão semelhantes" para o titular confirmar o vínculo ou manter separado.
- **Saldo confirmado pelo titular manda.** Num mês com base configurada, não há herança nem "previsto herdado".

## Despesa prevista não paga (avaliada, sem mudança)

Continua abatida na herança, que é o comportamento conservador. Aparece como pendência herdada e não é descontada de novo. Quando é paga com vínculo, a herança é compensada. O saldo herdado fica, portanto, **menor** que o do banco enquanto a despesa estiver em aberto; nunca maior.

Exemplo: fixo de R$ 300 não pago em outubro.
- Novembro mostra 1.000 − 300 = R$ 700 em "Saldo agora".
- O previsto de outubro (R$ 400) aparece à parte.
- A previsão de novembro é 700 + 400 = R$ 1.100.

Ver D2: uma despesa lançada sem vínculo continua contando em dobro na projeção até ser vinculada. É regra intencional.

## Onde

- `services._calcular_saldo_mensal_etapa`:
  - `saldo_herdavel` = projeção − receitas previstas do mês − receitas previstas herdadas;
  - `receitas_previstas_herdadas_*`.
- `services._receitas_previstas_herdadas`, `services._saldos_herdados_caixa_reconciliados` (o caixa por conta usa o mesmo valor) e `services._calcular_metricas_resultado_mes` (revisão `receita_sem_vinculo` entre meses).
- Testes: `tests/test_heranca_receita_prevista.py`.
