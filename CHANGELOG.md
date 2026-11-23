# Não lançado (branch nuvem) — Servidor no Google Cloud e fixo de valor variável

## "Quanto vou pagar de X" e Fixos por categoria (19/11/2026)

- "quanto vou pagar de cartão" (ou "de cartão de crédito", "de faturas"): soma das faturas de todos os cartões no mês — cada cartão com vencimento, o que falta e o já pago, com botão para a fatura. "quanto vou pagar de moradia" (ou qualquer categoria): contas da categoria (condomínio, IPTU, IPTV, internet, luz ≈ estimada), total, já pago e falta; fixos da categoria no crédito aparecem à parte (já estão na fatura; não somados de novo).
- Períodos: "em dezembro", "em janeiro" (= o próximo janeiro), "nos próximos 3 meses". "quanto vou pagar" sozinho e "no Itaú" seguem para as telas de antes.
- Tela Fixos: resumo por categoria no mês (total, quantidade, quantos no cartão) e botão para filtrar; na categoria filtrada, atalho "A pagar desta categoria".
- Mesma fonte da tela A pagar (os totais batem); pagos vêm das baixas (vínculos). Só leitura. `consultas_pagar.py`; `telegram_experiencia.py` não cresceu.
- Testes: `tests/test_pagar_categoria.py`. Gate oficial (Windows): 1390/1390 hoje e em 01/01/2027.

## Efeito no dinheiro na baixa e nos registros (19/11/2026)

- A prévia da baixa mostra "🏦 Ao salvar: Banco X R$ 1.000,00 → R$ 966,55"; a confirmação ("✅ Registro salvo") traz "Efeito no seu dinheiro": saldo da conta antes → depois e a sobra prevista ("sem mudança — já estava reservado em A pagar" na baixa de um fixo; antes → depois num gasto comum). Crédito: aviso de que não sai do saldo agora (vai para a fatura).
- Motivo: na baixa do iCloud (19/11) o saldo do Mercado Pago caiu corretamente (10.000,00 → 9.966,55), mas a sobra prevista não muda — o valor já estava reservado — e isso pareceu erro. Cálculos inalterados; só exibição. `efeito_baixa.py`; falha no cálculo nunca impede o registro.
- Testes: `tests/test_efeito_baixa.py` (caso de exemplo do iCloud, gasto comum, entrada, crédito, falha, privacidade). Gate oficial (Windows): 1381/1381 hoje e em 01/01/2027.

## Fixo de valor variável — conta de luz (18/11/2026)

- Um fixo pode ser marcado como "valor varia todo mês" (tela do fixo ou logo após cadastrar). A previsão (A pagar, Início, herança) passa a usar a **média dos 3 últimos meses pagos** antes do mês, mostrada com "≈"; sem histórico, o valor cadastrado.
- Ao ativar, o bot sugere como histórico os lançamentos antigos com o nome do fixo (ex.: as contas de luz lançadas como gasto comum de junho a outubro) — eles só entram na média, nada neles muda.
- Na baixa, o bot pergunta quanto veio a conta; **qualquer valor fecha o mês** (menor não deixa resto, maior não é recusado) e entra na média seguinte. Segunda baixa no mesmo mês é recusada. Fixos no crédito não podem ser variáveis (o valor real já vai pela fatura).
- Estado em `auditoria_eventos` (entidade `fixo_variavel`), sem migration. Módulos `fixos_variaveis` (regras puras), `fixos_variaveis_acoes` e ajustes pontuais em `conciliacao`; `telegram_experiencia.py` e `services.py` não cresceram; nenhum ciclo de import novo. Fixos comuns idênticos (teste de equivalência da Onda 2 sem diferença).
- `deploy/publicar.ps1`: gate → backup do banco no servidor → envio → reinício → conferência, com volta automática à versão anterior se o bot não subir (`-Desfazer` volta manualmente).
- Gate oficial (Windows): 1375/1375 hoje e em 01/01/2027. Publicado no servidor em 18/11/2026.

## Assessor no Google Cloud (14/11/2026)

- Versão portável para Linux (chave local no lugar do DPAPI, Tesseract, whisper-cli, rclone) e instalação em e2-micro gratuito (`deploy/`); gate Linux 1366/1366; migração feita em 14/11/2026 (detalhes em `deploy/RELATORIO_NOITE_14-11-2026.md`).

# 4.2.0 — Profissionalização, Telegram só e backup fora do computador (13/11/2026)

Resumo da versão (detalhes nas seções abaixo, da mais recente à mais antiga):
- Reavaliação completa e Ondas 1 a 3 (etapa 1): gravação sempre com prévia e confirmação, furos de PIN fechados, herança de saldo só com o realizado, jornadas de ponta a ponta, mapa de rotas, configuração e relógio únicos.
- O assessor passa a ser só o bot Telegram (painel web removido).
- Consultas por categoria e período, busca em todos os meses com troca de categoria em lote, contas desativáveis e ajuste de saldo por conta.
- Backup diário criptografado fora do computador (OneDrive), com banco, código e configuração.
- Gate oficial: 1355/1355 testes hoje e em 29/02/2028 (versão 4.2.0).

## Backup externo criptografado no OneDrive (13/11/2026)

- Depois do backup diário local, o bot grava em `%USERPROFILE%\OneDrive\Backups\Assessor` (ou `ASSESSOR_BACKUP_EXTERNO_DIR`) um pacote `.assessor-bkp` com o banco, o repositório git inteiro (`git bundle`) e o `.env`, cifrado com AES-256-GCM (chave scrypt da senha do titular). Sem a senha, nem o OneDrive lê o arquivo.
- Cada cópia é relida, decifrada e conferida (SHA-256 do manifesto e `quick_check` do banco) antes de entrar no lugar: a restauração é testada todo dia. Mantém as 30 mais recentes. Falha na cópia externa nunca derruba o backup local; aparece no log e na resposta do comando `backup`.
- Ativação no terminal do titular: `.\.venv\Scripts\python.exe backup_externo_cli.py configurar` (a senha fica neste PC só protegida pelo DPAPI; o titular a guarda no gerenciador de senhas). Também: `agora`, `status`, `verificar`, `restaurar <arquivo> <pasta-nova>`. O `LEIA-ME.txt` da pasta traz um script de 6 linhas para abrir o pacote num computador novo, sem o projeto.
- Nova dependência fixada: `cryptography==50.0.2` (com `cffi` e `pycparser`).
- Histórico do git: limpeza do commit `63d2be6` adiada por decisão do titular (sem remoto; o pacote é cifrado). Continua pré-requisito de qualquer push.
- Testes: `tests/test_backup_externo.py` (cifra, senha errada, adulteração, receita do LEIA-ME executada de verdade, rotação, restauração, falha no destino, git bundle real, integração com o backup automático).

## Busca em todos os meses e troca de categoria em lote (13/11/2026)

- "buscar bruno" (ou procurar/pesquisar) passa a procurar em TODOS os meses, do mais recente ao mais antigo; antes olhava só o mês atual. Aceita os períodos das consultas ("buscar bruno nos últimos 3 meses", "de julho a novembro", "em 2025"). A tela mostra quantidade, total de saídas e entradas, categorias encontradas, 8 lançamentos por página (cada um abre o detalhe) e o atalho para o Histórico do mês.
- Novo botão "🏷 Mudar categoria de todos (N)": escolhe a categoria, mostra a prévia antes → depois e só grava com "Confirmar alteração". Só saídas mudam; parcelamentos mudam inteiros; valores, datas e contas não mudam. Grava numa transação só (`database.atualizar_categoria_em_lote`), audita item a item e falha fechado se algo mudou desde a prévia (toque duplo não grava de novo).
- Depois de confirmar, o bot oferece aprender "bruno → Lazer" para os próximos lançamentos (regras pessoais de categoria já existentes).
- Código em `busca_lancamentos.py`, que monta as telas com os utilitários do motor sem importá-lo (sem novo ciclo de import). `telegram_experiencia.py` e `database.py` não cresceram.
- Testes: `tests/test_busca_lancamentos.py` (interpretação, busca, prévia, gravação, prévia desatualizada, parcelamento, regra, privacidade e caminho real do `dispatch_text`).
- Gate oficial: 1343/1343 testes hoje e em 15/01/2027.

## Paginação de "ultimas" e "buscar" pelo botão (13/11/2026)

- Corrigido: em "ultimas", o botão "Próxima ▶️" reenviava "ultimas pagina 2" pelo motor novo, que lia isso como lançamento de R$ 2,00 ("ultimas pagina") e abria "Como foi pago?". Em "buscar ...", o mesmo botão abria o Histórico procurando "compra pagina 2" e mostrava "Nenhum lançamento".
- Os botões "◀️ Anterior" e "Próxima ▶️" das listas paginadas do legado passam a ir direto ao assessor (prefixo `__legado__:`, como confirmar/cancelar); rótulo e cor iguais. Nada era gravado sem confirmação, mas o formulário confundia.
- Teste: `tests/test_paginacao_ultimas_botao.py` (motor novo real, toque no botão).
- Gate oficial: 1328/1328 testes.

## Consultas de gasto por período (13/11/2026)

- Perguntas no Telegram passam a entender período: "quanto gastei de viagem nos últimos 3 meses" (mês atual até hoje e os 2 anteriores), "quanto gastei com alimentação de julho a novembro" (sem ano = ano corrente; "de novembro a fevereiro" começa no ano anterior), "entre julho e setembro", "julho até setembro de 2025", "em julho de 2025", "em 2025" e "ano passado". A categoria aceita "com", "em" e "de".
- Corrigido: "quanto gastei com alimentação de julho a novembro" (ou "em julho") procurava a categoria "alimentacao de julho a novembro", olhava só julho e respondia "não encontrei".
- Em intervalos a resposta mostra o total de cada mês e o rótulo "Julho 2026 a Novembro 2026 (até 13/11/2026)". Lançamentos com data futura continuam fora. Tudo determinístico (`consultas_rapidas.py`), sem IA local; dia a dia, semana e filtro por conta/cartão seguem fora desta camada.
- `telegram_experiencia.py` não cresceu: a tabela de meses passou a ser única (`consultas_rapidas.MESES`).
- Testes: `tests/test_consultas_periodo.py` (interpretador, motor com banco temporário e caminho real do `dispatch_text`).
- Gate oficial: 1326/1326 testes hoje e em 15/01/2027.

## Painel web removido (13/11/2026)

- A pedido do titular, o assessor passa a ser só o bot Telegram. Saíram `web_app.py`, `web/static/`, `iniciar_site_assessor.bat`, os 12 contratos JavaScript do gate (e a exigência de Node), as variáveis `ASSESSOR_WEB_*` e os testes que cobriam só o painel (login, rotas HTTP, política de loopback, totais do dashboard web).
- `iniciar_assessor_completo.bat` agora só inicia o bot. Textos do bot deixaram de citar o "painel web local"; o painel em imagem (`painel`/`/dashboard`) continua.
- Cálculos, banco e migrations inalterados. O código antigo continua recuperável pelo histórico do git.
- Gate oficial: 1310/1310 testes hoje e em 01/12/2026 (eram 1338: saíram 28 testes que só cobriam o painel); sem contratos JavaScript.

## Onda 3, etapa 1: higiene, configuração e relógio únicos (12/11/2026)

- Sem mudança de comportamento para o titular (máquina em UTC-3, `.env` na pasta do projeto).
- `config.py` centraliza a leitura de ambiente (eram 53 leituras em 13 módulos); `.env.example` cobre as variáveis realmente usadas; pastas de backups, exportações, painéis e importações ancoradas no projeto.
- `relogio.py` (UTC-3) passa a ser a fonte de "hoje" e "agora": usos diretos caíram de 181 para 21.
- 33 símbolos sem referência removidos (cerca de 340 linhas), entre eles as 3 rotinas antigas de alerta nunca agendadas.
- `tests/test_arquitetura_linha_de_base.py` trava tamanho de módulos, funções gigantes, ciclos de import e usos espalhados de data e ambiente: só podem diminuir.
- Gate oficial: 1338/1338 testes hoje e em 25/11/2026, 01/12/2026, 01/01/2027 e 29/02/2028; contratos web: 12/12.

## Onda 2 de profissionalização (12/11/2026)

- Inventário de gravação do caminho antigo (docs/reavaliacao/07) com teste que falha se surgir comando de escrita sem prévia; passam a pedir confirmação: ajustar saldo por texto, vencimento de fatura, data de pagamento, correção de movimento de fatura, transferência e lançamento por texto livre que chegue ao núcleo. Marcar pago/pendente no checklist segue direto, agora auditado.
- "Comando não reconhecido" sugere comandos parecidos com o que foi digitado.
- Telas: A pagar e Quanto vou pagar dizem o que cada total inclui; transferências e pagamentos de fatura aparecem no Histórico como "não é gasto"; "Dashboard" virou "Painel"; códigos internos saem do texto principal; datas dd/mm/aaaa e valores com milhar em toda parte; rodapé único Voltar · Início · Menu; telas vazias e primeiro uso conduzidos; botão "Valores nos avisos"; painel em imagem legível no celular.
- Desempenho: cálculo de herança com uma conexão por consulta (de ~5.300 para 1) e sem deepcopy; cálculo do mês com 12 meses de cadeia de ~19 s para ~0,3 s no cenário de teste.
- Correção: o cache de consulta ignorava o corte da conciliação e o resultado de um mês dependia da ordem das consultas na tela (item pago e vinculado no mês seguinte reaparecia como pendência herdada).
- Correção: `vencimento fatura <cartão> dia N` sem mês configurava só se o cartão tivesse fatura no mês corrente.
- Testes: relógio falso no gate (`--data AAAA-MM-DD`), 15 jornadas de ponta a ponta conferidas contra conta à mão, equivalência dos cálculos contra valores de referência, mapa de rotas regenerado com verificador de defasagem.
- Gate oficial: 1325/1325 testes hoje e em 25/11/2026, 01/12/2026, 01/01/2027 e 29/02/2028; contratos web: 12/12.

## Reavaliação e Onda 1 de profissionalização (09/11/2026)

- Reavaliação completa por cinco frentes (docs/reavaliacao): veredito de não recriar e profissionalizar por partes.
- PIN: o gate enxerga o mesmo texto que o núcleo executa (espaços, sinônimos) e vale no fluxo guiado; backup e CSV só saem com PIN válido; limitador de tentativas sobrevive a reinício.
- Nada grava sem prévia: `mudar`, `corrigir valor|conta|forma`, `meta`, edições de fixo, pausar/reativar, `apagar transferencia caixa` e `resetar checklist` pedem confirmação; "sim" solto não confirma exclusão; conta/forma de parcela isolada bloqueada.
- Privacidade: Ocultar virou preferência persistente e vale nas respostas do caminho antigo; mensagens com valores, fotos e documentos saem protegidas contra encaminhamento.
- Herança de saldo: o mês seguinte herda só o realizado; receita prevista não recebida aparece separada e entra na previsão uma vez só.
- Pagamento de fatura afeta o caixa do mês em que o dinheiro saiu; cartão sem vencimento configurado não aparece como "vence hoje"; "quanto vou pagar em janeiro" aponta para o próximo janeiro; "quanto gastei" ignora lançamentos futuros, como o Fechamento.
- Banco recusa valores inválidos (infinito, texto, acima do teto; transação > 0); formatador único de dinheiro com arredondamento HALF_UP.
- Jornadas: "nova entrada prevista" não vira despesa; aviso de limite ao salvar; corrigir a data de um lançamento; limite e mês por botões; frases naturais (extrato, faturas, buscar, contas, limites) levam à tela certa; sessão expirada com mensagem clara; telas com números mais rápidas.
- Operação: trava de instância única, tratamento global de erro com aviso ao titular, README, dependências sem uso removidas.
- Testes: 54 testes para os mutantes que sobreviviam, erros de falha-fechado da conciliação cobertos, execução de tests/ isolada do banco real, relógio fixável, gate com `--workers` e `--timeout`.

## Ajustar saldo por conta e conta de fixos (29/10/2026)

- Ajustar saldo abre um seletor com todas as contas e o saldo calculado hoje; o titular toca na conta, digita o saldo do banco e confirma (só ela muda). "Todas em sequência" e "Outra conta" continuam disponíveis; contas desativadas não aparecem; modo Ocultar mascara os saldos; paginação acima de 8 contas.
- Após ajustar, botão "Ajustar outra conta". Detalhe de conta sem movimento ganha botão Início.
- `alterar conta fixo N para X` no editor de fixos (caminho real do Telegram) passa a valer também em fixos com conciliações; valor, forma e datas continuam protegidos.
- Gate oficial: 1032/1032 testes; contratos web: 12/12.

## Gerenciar contas (29/10/2026)

- Nome que só existe como destino (ex.: Lia no iCloud) deixa de aparecer como conta: a lista ignora o campo antigo de pagamento quando o fixo tem conta de origem.
- Conta de pagamento de fixo com conciliações pode ser alterada (`alterar conta fixo N para ...`); valor, período e forma continuam protegidos.
- Nova tela Mais recursos → Gerenciar contas: desativar/reativar conta sem apagar histórico, relatórios, exportações nem backup. Desativar é recusado se a conta tem saldo ou contas em aberto no mês; registrar em conta desativada avisa; consultas por nome continuam achando a conta. Auditado, sem migration.
- Teste de PIN errado deixa de ser intermitente (pares do teclado fixos; antes falhava ~1 em 315 rodadas).
- Gate oficial: 1021/1021 testes; contratos web: 12/12.

## Conta de pagamento dos fixos (29/10/2026)

- Baixa de fixo (Registrar pagamento/recebimento) passa a perguntar de qual conta saiu o dinheiro; a conta cadastrada no fixo aparece primeiro como padrão (✦), sem ser assumida.
- Confirmação de despesa que sai do caixa avisa quando o saldo da conta ficaria negativo (só para quem acompanha saldos por conta; não bloqueia).
- Caso de origem: 7 Pix de fixos baixados no Itaú, que começava outubro com R$ 0,00 e não recebeu entradas, deixaram a conta negativa.
- Gate oficial: 1010/1010 testes; contratos web: 12/12.

## Fase 2 de lançamento e condução (29/10/2026)

- Lançamento rápido: conta, forma e categoria sugeridas pelo histórico (✦, editáveis), "Repetir último" e "Frequentes", contas por uso; "foi parcelada?" só no crédito e data padrão = hoje. "gastei 45 no mercado" com histórico: 2 ações.
- Parser tolerante: valor em qualquer posição, datas curtas ("15/10", "dia 15", "segunda"), "1,5k", apelidos de conta, erros claros, e recusa de várias linhas/lançamentos numa mensagem.
- Pós-salvar: Desfazer (o existente), Categoria (com prévia, confirmação e auditoria) e Repetir; aviso de duplicata com #id e janela de ±1 dia, sem bloquear.
- Limites com barra, ritmo e margem por dia; "o que cresceu" por categoria; "Posso comprar?" com "Deve sobrar" antes e depois, usando o mesmo cálculo do Início e sem recomendar.
- Rodapé de navegação compacto, com mês avançando direto em mais telas; A pagar em tabela agrupada por urgência.
- Testes antigos ajustados ao novo fluxo (parcelas só no crédito; "dia 15" entendido).
- Gate oficial: 1005/1005 testes; contratos web: 12/12.

## Fase 1 de design e condução (29/10/2026)

- Modo ocultar vale em todas as telas (A pagar, Histórico, Fechamento, Análises, Agenda, Atenção, Categorias, Limites, Quanto vou pagar, saldos por conta), inclusive tabelas e rótulos de botão.
- Formatação: −R$ para negativos, percentual com vírgula, plurais corretos no lugar de "(s)" e chip de vencimento.
- Botões com rótulos específicos ("Ver 3 vencidas", "Energia · R$ 210,00") e ícones coerentes entre texto e tabela; formas de pagamento com ícones próprios.
- Texto sem verbo ("mercado 45"), "novo fixo ..." e "transferi ..." abrem a prévia de confirmação em vez de gravar direto; transferência não cria mais destino "O Nubank".
- Início: linha "Hoje" (contas vencidas, que vencem hoje ou amanhã, só contagens) com botão para A pagar; "Deve faltar no fim do mês" quando a projeção é negativa.
- Avisos: manhã com contagem de contas, noite só quando há algo a dizer, domingo sem prometer revisão inexistente; preferência `alerta_valores` (desligada por padrão) para incluir total.
- Novos testes: privacidade/formatação (24), legado com prévia (14), avisos (11), Início/Hoje (7).
- Gate oficial: 906/906 testes; contratos web: 12/12.

## Correções pós-auditoria (28/10/2026)

- Início e /menu abrem sempre o mês vigente; consultas como "quanto vou pagar em novembro" não prendem mais o mês.
- Início ganha Mês anterior / Próximo mês / Mês atual para ver projeções; Atualizar em Detalhes mantém o mês projetado.
- Segurança: o prefixo interno de exclusão digitado no chat é recusado; exportar a base inteira ou mais de 366 dias exige PIN.
- PIN: a ação bloqueada é refeita após o desbloqueio; reset por texto com limite de tentativas e auditoria; pendências de reset/exclusão expiram; botões de confirmação vinculados à pendência; `desbloquear <PIN>` apagado do chat.
- Texto livre: valor ("iphone 15 por 5000", "3 mil e 500"), data (dd/mm/aa, dd-mm-aaaa; "amanhã" recusado), categoria explícita respeitada, dois valores recusados e menos falsos positivos de comando.
- Total a pagar avisa quando uma conta não pôde ser calculada; "alterar conta" passa a gravar conta_origem; valores NaN/infinito rejeitados; data de cartões novos configurável (`ASSESSOR_CARTAO_NOVO_INICIO`).
- Remove gatilhos inalcançáveis e funções sem uso de services.py; "quanto vou pagar este mês" funciona.
- Novo: mapa de rotas (docs/mapa), suíte de percurso de botões (173 telas, 749 botões) e testes de regressão por correção.
- Teste de parser deixa de depender da data de hoje.
- Gate oficial: 850/850 testes; contratos web: 12/12.

# 4.1.3 — Confiabilidade, saúde e aprendizado pessoal (08/10/2026)

- Preserva por até dez minutos os fluxos, rascunhos e callbacks da interface moderna após reinício do processo.
- Preserva por até 24 horas os comandos de botões legados recentes, mantendo as validações e confirmações existentes.
- Protege os arquivos efêmeros com Windows DPAPI; bloquear o assessor continua invalidando a sessão financeira ativa.
- Acrescenta aprendizado explícito de categoria após uma correção: nada é aprendido sem confirmação do titular.
- Aplica a mesma preferência pessoal a texto e áudio, sem reclassificar lançamentos anteriores.
- Permite consultar e remover regras em Mais recursos → Meus dados → Categorias aprendidas.
- Amplia `status` para mostrar integridade somente leitura, tempo ligado, backup, espaço, áudio, OCR, IA local e regras pessoais.
- Protege o comando `status` e o botão Saúde do assessor com a sessão reforçada por PIN já existente.
- Mantém banco, schema, migrations, cálculos financeiros, faturas, saldos e checklist inalterados.
- Gate oficial: 539/539 testes; contratos web: 12/12.

# 4.1.2 — Dashboard com métricas e contexto (30/09/2026)

- Enriquece exclusivamente os painéis do Telegram: visão do mês, evolução e diagnóstico.
- Mantém saldo, reserva e sobra do motor existente; acrescenta entradas/gastos registrados, obrigações e recebimentos esperados.
- Mostra concentração de categorias, variação de gastos, pendências no corte e limites próximos/atingidos.
- Compara o mês em andamento com a mesma quantidade de dias no anterior, inclusive em meses de durações diferentes.
- Separa meses encerrados, parciais e futuros; não inventa variações sem base nem compara projeção com realizado.
- Apresenta evolução dos últimos três meses com gráficos, métricas e legenda de competência.
- Preserva privacidade, rascunhos, navegação de mês e atualização; não grava finanças nem exige contratação.

# 4.1.1 — Novidades sem cobranças (30/09/2026)

- Retira o Mini App externo, seus endpoints, autenticação e biometria; preserva o dashboard e o painel web local.
- Retira criação e orientação de ativação de tópicos privados, seus botões e comando do menu.
- Recoloca o menu de comandos habitual no próximo início, sem configurar hospedagem externa.
- Preserva origem dos valores, composição de faturas, exercícios, mídia revisada e lembretes.
- Mensagens enriquecidas proíbem explicitamente envio com cobrança (`allow_paid_broadcast=false`).
- Não usa APIs pagas de transcrição/OCR nem pagamentos comerciais do Telegram.
- Mantém código financeiro e dados pessoais intactos; configuração real não é editada.

# 4.1.0 — Recursos úteis do Telegram (30/09/2026)

- Explica a origem do saldo, da reserva e da previsão; pagina compras e movimentos na composição da fatura.
- Acrescenta exercícios às 15 aulas, mantendo exemplos sem execução financeira.
- Recebe fotos e áudios para revisão e formulário, com limites, descarte de temporários e proteção contra duplicidade de fatura.
- Acrescenta ações aos lembretes e adiamento idempotente, preservando cadastros em andamento.
- Prepara tópicos privados com formulários e callbacks isolados por tópico.
- Prepara Mini App de consulta, com cinco áreas, tema Telegram, privacidade, assinatura de abertura, PIN e biometria opcional.
- Oferece mensagens enriquecidas com fallback em rejeição explícita, perfil e comandos atualizados ao reiniciar.
- Mantém motor financeiro, migrations e dados pessoais intactos. HTTPS e configuração no BotFather continuam etapas de ativação do titular.

# 4.0.7 — Ajuda, aprendizado e painel (30/09/2026)

- Organiza /help por objetivos, com exemplos, conferência e guia do dashboard.
- Oferece /aprender nativo com 15 aulas, catálogo paginado e navegação sequencial.
- Mantém os exemplos didáticos sem execução e preserva rascunhos ao abrir orientação.
- Explica o corte configurável dos cartões, sem alterar sua regra.
- Simplifica o dashboard em saldo, reservas e sobra prevista; detalhes ficam acessíveis por botões.
- Acrescenta navegação de competência e atualização; alerta para base estimada e revisão de conciliação.
- Renderiza painéis menores, com cores suaves e categorias sem colisão de rótulos e valores.
- Mantém motor financeiro, migrations e dados pessoais intactos.

# 4.0.6 — Apresentação Telegram (30/09/2026)

- Padroniza títulos, períodos, ícones e destaque de valores nos resultados de comandos e botões.
- Recupera contexto e próximos passos em Início, Saldo, A pagar, Histórico, contas e faturas.
- Enriquece menus, cadastros de fixos, ajuda, confirmações, avisos e etapas do registro.
- Decora botões somente no envio, preservando callbacks e entradas digitadas; mantém cores por função.
- Protege HTML, paginação UTF-16, caracteres especiais e privacidade.
- Mantém regras financeiras, integrações e dados pessoais intactos.

# 4.0.5 — Auditoria de encerramento (30/09/2026)

- Mantém as correções de vigência, saldo atual, reservas por cartão e dashboard.
- Corrige desconexões HTTP, encerramento de sessão com falha e acesso por teclado aos atalhos web.
- Amplia a regressão para 410 testes e 12 contratos JavaScript; valida 106 tipos de ação Telegram.
- Acrescenta validação isolada reproduzível e percursos até confirmações/cancelamentos.
- Atualiza Pillow, AnyIO, urllib3, pip e setuptools após consulta de segurança por versão.
- Acrescenta inicializador conjunto Telegram/web e modelo de configuração sem PIN/chave conhecidos.
- Não altera saldos pessoais nem registra pagamentos como parte desta auditoria.

# RC1.5.11 — Fonte única para faturas

- Faturas passam a usar uma única fonte de verdade por competência.
- Quando existem lançamentos reais de cartão, compromissos recorrentes no crédito deixam de ser somados novamente.
- Quando ainda não existem lançamentos reais, os recorrentes continuam formando a fatura prevista.
- Checklist, alerta, detalhamento e comandos “quanto vou pagar” usam o mesmo saldo canônico.
- Faturas exibem indicação `realizada` ou `prevista`.
- Fixos via Pix, empréstimos e demais compromissos continuam separados.
- Nenhuma migration e nenhuma alteração automática no banco.
- Regressão completa: 140 testes aprovados.

## RC1.5.10 — Correção do valor líquido da fatura e total do checklist

- Corrige a validação da RC1.5.9: o valor exibido já é o saldo líquido da fatura após créditos/estornos.
- Garante que o checklist use esse saldo líquido, sem somar fixos e empréstimos dentro de B1.
- Garante que o total pendente seja recalculado com o novo valor de B1.
- No exemplo de julho/2026, o total passa a refletir só os itens da competência, mantendo os demais itens inalterados.
- Nenhuma migration e nenhuma alteração de dados.

# RC1.5.7 — checklist compacto

- O comando `checklist` passa a exibir somente itens pendentes por padrão.
- Transações automáticas já pagas deixam de ocupar a visualização principal.
- Adicionado `checklist completo` para recuperar a visualização com pagos e pendentes.
- Mantidos `checklist pagos`, `checklist pendentes`, `checklist fixos` e filtros de faturas.
- Adicionados os aliases `checklist faturas`, `checklist geral` e `checklist todos`.
- Removido o bloco repetitivo `Ações:` da listagem principal.
- Nenhum dado, valor, status, pagamento ou schema foi alterado.
- Suíte final: 126 testes aprovados.

# RC1.5.5 — preparação aditiva do modelo de pagamento

- Adicionada migration `0002_campos_pagamento_canonicos`, limitada à tabela `compromissos`, sem backfill ou reinterpretação de dados legados.
- Adicionados `conta_origem` e `destino_pagamento` opcionais; `forma_pagamento`, já existente e opcional, foi preservado integralmente.
- Mantido `conta_pagamento` sem remoção, renomeação, limpeza ou conversão automática de Pix, Lia e bancos.
- Adicionada camada pura de leitura canônica em sombra, sem integração com parser, cálculos ou comandos Telegram.
- Adicionada validação do hash de schema resultante antes do commit de migrations que executam DDL.
- Bancos novos, que já nascem com o schema final, podem registrar 0001/0002 sem duplicar colunas por meio de validação explícita do hash preaplicado.
- Rollback SQL da migration 0002 declarado como não suportado; reversão operacional por backup validado.
- Nenhuma migration aplicada ao banco real e nenhuma alteração funcional visível.

# RC1.5.4A — consolidação arquitetural do framework de migrations

- Oficializada a arquitetura híbrida: `PRAGMA user_version` representa a versão corrente e `schema_migrations` mantém histórico, checksum, data, duração, sucesso e suporte a rollback.
- Documentado que `schema_migrations` somente pode ser criada por `migrate`; `status`, `validate` e `dry-run` permanecem somente leitura e não criam objetos de schema.
- Corrigida a descrição do dry run: o banco principal não é alterado, mas o SQLite em modo WAL pode criar ou atualizar sidecars `-wal` e `-shm` durante conexões somente leitura.
- Adicionada decisão arquitetural e fluxo operacional oficial do framework.
- Nenhuma migration aplicada e nenhuma alteração funcional ou financeira.

# RC1.5.4 — framework seguro de migrations

- Adicionado runner isolado `migrations.py`, sem integração automática com o bot ou módulos financeiros.
- Adicionada descoberta ordenada de migrations, checksum imutável, validação de integridade/schema e versionamento híbrido por `PRAGMA user_version` + `schema_migrations`.
- Adicionada migration `0001_baseline`, intencionalmente no-op sobre todas as tabelas funcionais.
- Adicionados backup SQLite online com SHA-256/metadados, auditoria JSONL, dry run e rollback por backup ou por migration.
- Adicionados comandos `status`, `validate`, `dry-run`, `migrate` e `rollback`.
- Adicionados 13 testes isolados; 74 testes legados e 87 testes totais aprovados.
- Nenhuma migration foi aplicada ao banco de produção nesta entrega.

# RC1.5.3 — baseline de regressão e compatibilidade legada

- Restaurada a classificação compatível de faturas/cartões legados, incluindo formas vazias ou não informadas para bancos conhecidos, sem tratar Pix ou empréstimos como fatura.
- Empréstimos passam a ter grupo visual próprio em `Quanto vou pagar`, preservando exatamente o total financeiro consolidado.
- Centralizada a elegibilidade do checklist: pendentes contêm apenas obrigações que exigem ação; transações imediatas realizadas continuam acessíveis na visão geral como concluídas.
- Valores zero/negativos e movimentos internos de fatura não viram tarefas genéricas.
- Corrigido o isolamento de `DB_PATH` e substituída a fixture Linux fixa por uma fixture SQLite temporária e portátil.
- Adicionadas regressões dos contratos RC1.5.3; suíte final com 74 testes, sem falhas, erros ou testes ignorados.

# RC1.5.1 — correção mínima do checklist

- Remove do checklist tarefas individuais originadas de movimentos de fatura, incluindo estornos, créditos, pagamentos e ajustes.
- Mantém esses movimentos no cálculo consolidado da fatura e no detalhamento.
- Preserva integralmente a lógica da RC1.5 para Itaú, Mercado Pago, Nubank, conta Pix, compromissos e transações legadas.
- Adiciona regressão com cópia do banco recuperado de produção.

# Changelog

## RC1 — 2026-07-17

### Corrigido

- Fechamento determinístico das conexões SQLite usadas com `with`.
- Eliminação dos `ResourceWarning` observados na regressão de faturas.
- Fechamento explícito das conexões auxiliares de status, histórico e backup.
- Validação automatizada de que conexões não permanecem utilizáveis após o contexto.

### Consolidado dos lotes anteriores

- Parser monetário centralizado e validação de formatos ambíguos.
- Validações estruturais dos movimentos de fatura.
- Importação atômica com rollback.
- Backup SQLite validado e com nomes únicos.
- Pendências de importação e exportação isoladas por usuário e chat.
- Proteção contra fórmulas em CSV e colisão de nomes de exportação.
- Transporte de saldo credor entre competências.
- Bloqueio de pagamentos em faturas zeradas ou credoras.
- Proteção concorrente para pagamento total.
- Confirmação de exclusões, edição segura e trilha de auditoria.
- Limite e bloqueio temporário de tentativas de PIN e recuperação.
- Bloqueio de grupos por padrão.

### Qualidade

- 31 testes automatizados executados com sucesso.
- Todos os módulos principais compilados com `py_compile`.

## RC1.1 - Correção do comando "quanto vou pagar"

- Fixos, parcelamentos e compromissos projetados passam a entrar no resumo da conta mesmo quando a forma de pagamento cadastrada é Pix, débito ou transferência.
- Lançamentos imediatos já realizados continuam fora do resumo para evitar dupla contagem.
- Adicionados testes de regressão para fixo projetado, Pix realizado e compra no crédito.

## RC1.2 - Resumo objetivo de "quanto vou pagar"

- Simplificado o retorno do comando para exibir apenas fatura/cartão, fixos, compromissos e total a pagar.
- Removidos do retorno principal: categorias, itens detalhados, critérios internos e lançamentos ignorados.
- Créditos, estornos e pagamentos agora abatem somente a fatura/cartão, sem reduzir fixos ou compromissos.
- Adicionados testes de regressão para consolidação e saldo credor.

## RC1.3

- Adicionada consulta consolidada `quanto vou pagar no mês`.
- Adicionados comandos `quanto vou pagar em julho`, `quanto vou pagar em julho/2026` e `quanto vou pagar em 2026-07`.
- O consolidado reúne faturas, fixos e compromissos pendentes de todas as contas.
- Pix, débito, dinheiro e transferências já realizados continuam excluídos do valor a pagar.
- Padronização do texto sem o termo "ainda".
- Adicionados 4 testes de regressão; suíte total com 41 testes.

## RC1.4
- Corrigido o reconhecimento de "quanto vou pagar no mês" e "quanto vou pagar no mês de julho".
- Corrigida a interpretação incorreta de "mês de julho" como nome de banco/conta.
- Tornada a consolidação mensal resiliente a registros legados ou contas com valores malformados.
- Adicionados testes de regressão para os comandos mensais e registros inconsistentes.

## RC1.5

- O resumo `quanto vou pagar no BANCO` agora exibe o botão **Ver detalhes**.
- O botão detalha exatamente os lançamentos que formam fatura/cartão, fixos e compromissos.
- Créditos, estornos, pagamentos e ajustes de fatura aparecem no detalhamento para reconciliar o total.
- Novo comando direto: `detalhar quanto vou pagar no Itaú em 2026-07`.

## RC1.5.2 - Auditoria do resultado mensal

- Adicionada auditoria item a item do Resultado operacional do comando `Meu mês`.
- Novos comandos: `auditar mês`, `auditar mês 2026-07`, `auditar resultado 2026-07` e `por que meu resultado está estranho`.
- A auditoria separa entradas recebidas, entradas previstas, saídas imediatas, pagamentos de fatura, crédito lançado e valores ainda esperados.
- Incluída reconciliação automática com o mesmo cálculo do Resultado operacional.
- Incluídos alertas de itens negativos em valores esperados e possíveis duplicidades entre grupos.
- A consulta é somente leitura e não altera lançamentos, compromissos, faturas ou checklist.

## RC1.5.6 — Normalização funcional de pagamentos

- Adicionada migration `0003_normalizacao_pagamentos_historicos`.
- Sete compromissos legados com `conta_pagamento=Pix` passam a usar `conta_origem=Itaú`.
- O compromisso iCloud preserva `forma_pagamento=crédito`, passa a usar `conta_origem=Itaú` e `destino_pagamento=Lia`.
- `conta_pagamento` legado é preservado para compatibilidade e auditoria.
- A projeção de compromissos e o checklist usam a conta canônica com fallback legado.
- A listagem de fixos separa Conta, Forma e Destino.
- Nenhum valor, vencimento, status ou transação é alterado.
- Suíte ampliada para 122 testes.

## RC1.5.8 — Vencimento e alerta de faturas

- Adicionado cadastro recorrente de vencimento pelo nome do cartão.
- Novos comandos: `vencimento fatura Itaú dia 10` e `vencimento fatura Nubank 2026-08 dia 20`.
- O vencimento recorrente usa uma chave estável por cartão (`B_<NOME>`), sem depender da numeração visual B1/B2/B3.
- O checklist compacto passa a exibir o vencimento de cada fatura.
- O alerta diário das 10h passa a separar compromissos e faturas vencendo no dia.
- Faturas pagas, zeradas ou sem saldo não geram alerta.
- Dias 29, 30 e 31 são ajustados automaticamente ao último dia válido do mês.
- Nenhuma migration e nenhuma alteração automática em dados existentes.

## RC1.5.9 — Hotfix de composição das faturas

- Corrige o cálculo da fatura para considerar somente compras e parcelas de cartão.
- Compromissos fixos, empréstimos e pagamentos por Pix vinculados à mesma conta bancária continuam no resumo geral da conta, mas deixam de inflar a fatura no checklist.
- Créditos, estornos e pagamentos parciais continuam sendo aplicados somente à fatura correspondente.
- Nenhuma migration e nenhuma alteração automática de dados.

## RC1.5.12 — Checklist com composição da fatura

- Restaura a composição correta da fatura do cartão: lançamentos, parcelamentos e compromissos fixos no crédito continuam somados no total do banco.
- Mantém o comando "quanto vou pagar no banco" com os componentes separados.
- Exibe no checklist, abaixo de cada banco, a decomposição do valor agregado:
  - Cartão e parcelas
  - Fixos no crédito
  - Empréstimos, quando houver
  - Outros compromissos, quando houver
- Remove a regra incorreta da RC1.5.11 que tratava compromissos recorrentes no crédito apenas como previsão quando já existiam lançamentos reais.
- Não altera banco de dados e não cria migration.

## RC1.5.14 — Ajuste pontual da fatura Itaú

- Adicionado `ajustar_fatura_itau.py` para tratar a mudança excepcional de fechamento/vencimento da fatura Itaú.
- Lançamentos e parcelamentos no crédito Itaú a partir de julho/2026 são postergados em um mês.
- Fixos recorrentes não são deslocados: a ocorrência de julho é duplicada em agosto, mantendo a recorrência normal de agosto em diante.
- Créditos, estornos e ajustes em `fatura_movimentos` acompanham a competência postergada.
- Pix, débito, transferência, dinheiro, empréstimos e outras contas ficam fora do ajuste.
- Backup automático e trava de idempotência impedem execução dupla.
- Adicionados 4 testes de regressão específicos do ajuste Itaú.
