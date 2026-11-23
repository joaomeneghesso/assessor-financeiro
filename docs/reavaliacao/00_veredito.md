# Reavaliação do assessor — veredito consolidado (09/11/2026)

Base: commit `c427341` (v4.1.3). Cinco frentes independentes, cada uma com relatório próprio nesta pasta:
`01_arquitetura.md`, `02_corretude_financeira.md`, `03_seguranca_privacidade.md`, `04_jornadas.md`, `05_testes_operacao.md`.
Os achados abaixo foram reproduzidos pelos agentes em banco temporário, salvo quando marcados como suspeita nos relatórios de origem.

## Veredito: não recriar; profissionalizar por partes

- **Recriar do zero não se justifica.** Os números batem com a conta à mão nos fluxos principais (≈95 cenários e ≈135 jornadas), o produto está em uso diário com dados reais, e a suíte (1.032 testes) não migraria para uma base nova.
- **Manter como está também não.** Três relatórios apontam a mesma raiz para boa parte dos defeitos: o **caminho legado de texto** (`services._processar_mensagem_core` + ramos de `app.py`), que grava sem prévia, ignora o modo Ocultar e permite contornar o PIN.
- **Caminho:** refatorar por estrangulamento, em etapas pequenas e reversíveis, com o gate verde em cada uma, **depois** de reforçar a rede de segurança (a mutação mostrou que ela é mais fraca do que parece).

## O que os números dizem

| Frente | Resultado |
|---|---|
| Corretude | Telas consistentes entre si e com a conta à mão; 13 divergências, 4 com efeito em reais |
| Segurança | 0 crítico, 2 altos (PIN contornável — **corrigidos em 09/11**), 8 médios, 14 baixos |
| Jornadas | 34 defeitos reproduzidos em ≈2.850 ações; nenhuma exceção ou jargão vazando em 493 telas |
| Testes | Cobertura 71% linhas / 60% ramos; mutação: só 9 de 20 mutantes mortos (45%) |
| Arquitetura | 5 arquivos = 74% do código; 2 ciclos de import; 2 motores de conversa |

## Ordem de execução

### Onda 1 — rede de segurança e defeitos que afetam dinheiro, privacidade ou gravação
1. **Rede de segurança dos testes** (05): testes para os 11 mutantes sobreviventes e para os erros de falha-fechado da conciliação; relógio da conciliação injetável (5 testes dependem da data real); `discover` fora do gate seguro (banco e `.runtime` temporários); gate com `--timeout`/`--workers` e mais rápido.
2. **Gravação sem confirmação e privacidade no legado** (03, 04): `apagar transferencia caixa`, `mudar/corrigir valor|conta|forma` por texto, `meta`, "nova entrada prevista" que vira despesa; "sim" solto confirmando exclusão; `protect_content` e Ocultar nas respostas do legado; Ocultar que se desliga sozinho.
3. **Corretude** (02, 04): receita prevista não recebida virando "saldo agora" no mês seguinte; pagamento de fatura em mês posterior alterando o saldo do mês da fatura; validação de valores na camada de banco; formatador único em Decimal HALF_UP; vencimento falso de cartão; "quanto vou pagar em janeiro" apontando para o passado; "quanto gastei" × Fechamento.
4. **Operação** (05): `add_error_handler` com aviso ao titular, trava de instância única, dependências sem uso fora do requirements, README/runbook.

### Onda 2 — experiência
Frases naturais que hoje caem em "Comando não reconhecido"; ≈1,8 s por toque (deepcopy em `compromissos.py`); números que não se explicam entre telas (A pagar × Quanto vou pagar; histórico sem transferências e pagamentos de fatura); visual (R$ 1500,00, datas ISO, ids internos); caminhos que faltam (corrigir data de lançamento, escolher categoria do limite por botão).

### Onda 3 — estrutura (strangler)
Config e relógio únicos; primitivas únicas (normalizador de conta, datas, formatador, backup); quebrar ciclos de import; fatiar `services.py` com reexport; drenar o legado comando a comando; fatiar `Experience`. Só depois: tabelas próprias para o estado que hoje vive em `auditoria_eventos` e, se ainda fizer sentido, centavos inteiros (hoje **não recomendado**: nenhum erro em valor gravado foi atribuído a float).

## Decisões que são do titular
- Mudar a regra de herança de saldo (item 3 da Onda 1) altera números exibidos em meses herdados sem base confirmada.
- Backup fora da máquina e criptografado (hoje fica no mesmo disco).
- Limpar do histórico git os 35 PNGs de dashboards do commit `63d2be6` antes de qualquer publicação.
