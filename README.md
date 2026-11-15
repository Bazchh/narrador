# Crônica

RPG de mesa online, de fantasia clássica, em que **as regras valem de verdade e a IA só narra**.
O mestre por IA propõe; um motor de regras confere, rola os dados e registra.

Estado: protótipo jogável e testado. Ainda sem servidor próprio, login ou pagamento.

## Regra central (não mudar)

A IA nunca rola dados nem altera o estado do jogo. Ela devolve uma proposta em JSON; o motor
valida contra as regras e contra o material da aventura, aplica o que tem base e recusa o resto.
Todo o código que conversa com a IA está em `motor/40-mesa.js` (`promptIA`, `aplicarIA`) e, para
as campanhas em kit, em `motor/37-kit.js` (`promptKit`, `aplicarEfeitos`).

## Como rodar

Não há dependências para jogar. O jogo é um único arquivo HTML.

```sh
python3 montar.py        # gera dist/index.html (jogo) e dist/teste.html (versão de teste)
```

Abra `dist/index.html` no navegador.

## Como testar

```sh
./testar.sh
```

- Testes do motor: Node 18 ou mais novo, sem pacotes.
- Testes de navegador: Python 3 com `playwright` e um Chrome instalado. O caminho do Chrome está
  fixo em `/usr/bin/google-chrome` dentro de `testes/nav*.py`; ajuste se for outro.

## Estrutura

```
motor/            regras e aventuras; roda sozinho em Node, sem tela
  10-base.js        tabelas (espécies, classes, magias, inimigos), ficha, dados, testes de perícia
  20-combate.js     combate por zonas, turnos, descansos, luta contra pessoas da cena
  30-sino.js        aventura "O Sino de Pedra-Funda" (formato antigo: roteiro)
  35-treino.js      aventura "O Pátio de Treino" (formato antigo) e o registro de aventuras
  37-kit.js         campanha como kit de mestre + a aventura "A Ponte do Corvo"
  40-mesa.js        ciclo da mesa: ações, texto livre, modos, pedido à IA, validação, exportar
tela/             interface; só fala com o motor pela API `window.Cronica`
  shell.html        esqueleto da página, com três marcadores que montar.py preenche
  style.css         visual
  ui/00-servicos.js ENCAIXES: único arquivo que sabe quem atende a IA e quem guarda as mesas
  ui/01-base.js     utilidades, armazenamento local, elenco, rotas
  ui/02-paginas.js  início, aventuras, regras
  ui/03-jogar.js    abrir e entrar em mesas
  ui/04-herois.js   criação e edição de personagem
  ui/05-mesa.js     tela de jogo
  ui/06-online.js   mesa compartilhada
  ui/07-mapa-dados.js mapa da cena e dado 3D
  ui/09-inicio.js   ligações de eventos e partida
testes/           t*.js (motor) e nav*.py (navegador); servidor_falso.py simula o servidor próprio
montar.py         junta tudo em dist/
testar.sh         monta e roda todos os testes
```

Os arquivos de `motor/` e de `tela/ui/` são concatenados em ordem alfabética dentro de uma única
função. Por isso os números nos nomes importam, e não há `import`/`export`.

## Os dois formatos de aventura

- **Roteiro** (Sino, Treino): cenas e ações escritas à mão. A IA só interpreta o que foge do previsto.
- **Kit de mestre** (Ponte do Corvo): lugares, pessoas, segredos, grupos hostis, uma ameaça que
  avança, marcas e finais, tudo como dados em `KIT_PONTE`. O motor gera as cenas a partir do kit.
  A IA conduz e muda o jogo só por efeitos de uma lista fechada: `revelar`, `marca`, `atitude`,
  `relogio`, `final`, e `luta`.

Aventura nova = kit novo. O plano é converter as duas antigas e remover o formato de roteiro.

## Encaixes (onde o jogo roda)

`tela/ui/00-servicos.js` escolhe entre três situações:

1. `ENDERECO_DO_SERVIDOR` preenchido: fala com um servidor próprio por HTTP. A lista dos dez
   endereços que o servidor precisa atender está no comentário do arquivo.
2. Página publicada no Claude: usa os serviços da própria página.
3. Nenhum dos dois: joga sem IA e sem mesa compartilhada.

`MODO_TESTE` liga o seletor de modelo e o medidor de custo; `montar.py` gera `dist/teste.html` com ele ligado.

## Dívidas conhecidas

- Arquivos grandes (`20-combate.js`, `05-mesa.js`).
- Textos das aventuras misturados ao código.
- Sem verificação de tipos nem padronização automática de código. Os testes rodam a cada envio
  pelo `.github/workflows/ci.yml` (o mesmo `testar.sh`).
- Fichas de inimigos e regras escritas de memória das regras abertas, não conferidas linha a linha.
- No servidor próprio, o jogador é reconhecido por um código do aparelho, não por conta.

## Conteúdo e licença

As regras usam apenas material do SRD 5.2.1 (Wizards of the Coast), sob Creative Commons
Atribuição 4.0. O texto de atribuição exigido está em `ATRIBUICAO`, em `motor/10-base.js`, e
aparece na página de regras. Não usar a marca "Dungeons & Dragons" nem conteúdo de outros livros.
A licença do código deste repositório ainda não foi escolhida.

## Plano

O plano do projeto (etapas, login, planos de assinatura, custos) é o documento `cronica/plano-do-projeto.md`, guardado na pasta do projeto no Claude. Ao criar o repositório, salve uma cópia dele em `docs/plano-do-projeto.md`.

## Antes do Crônica

Este repositório abrigou o projeto anterior, um mestre de D&D 5e para terminal em Python, com o
Mapa do Projeto, os Casos de Uso e o Blueprint Técnico. Ele foi encerrado e substituído pelo
Crônica. Tudo dele continua no histórico do git, na etiqueta `narrador-final`.
