# Narrador

Mestre de D&D 5e (regras de 2024, SRD 5.2) por inteligência artificial, no terminal, em português.

Os documentos que mandam no projeto estão em `docs/`: o Mapa do Projeto, os Casos de Uso e o
Blueprint Técnico. O código segue o roteiro em cards do capítulo 8 do Blueprint.

## Rodar

```
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest
narrador --versao
```

Nenhum teste chama a rede: o provedor falso cobre tudo. Nenhuma chave entra no repositório;
veja `.env.example`.

## Jogar

Um comando cria a aventura semente ("O Porão da Taverna"), a campanha com a personagem
pré-gerada e abre a tela de jogo. Na fase 1 o mestre é o roteiro embutido, sem custo:

```
narrador demo C:\jogos\narrador
```

Na tela: escreva o que a personagem faz ou pergunta; `/ficha`, `/cena`, `/ir <lugar>`, `/ajuda`,
`/sair`. Em combate: `ataco <alvo>`, `me aproximo de <alvo>`, `esquivo`, `fujo`, `passo`.
Rodar o mesmo comando de novo retoma a campanha de onde parou. Para começar do zero, apague a pasta.

## Licença de conteúdo

O único conteúdo de regras embutido é o System Reference Document 5.2, da Wizards of the Coast,
sob a licença Creative Commons Attribution 4.0. O texto de atribuição completo aparece na tela
"sobre" do produto e em toda exportação.
