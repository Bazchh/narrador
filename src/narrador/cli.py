"""O programa de terminal: versão, semente, sobre, e (card N-12) novo, jogar e demo."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from narrador import __version__

ARQUIVO_SEMENTE = "porao-da-taverna.sqlite"
NOME_CAMPANHA_DEMO = "O Porão da Taverna"


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="narrador",
        description="Mestre de D&D 5e (regras de 2024, SRD 5.2) por inteligência artificial.",
    )
    parser.add_argument("--versao", action="store_true", help="mostra a versão e sai")
    sub = parser.add_subparsers(dest="comando")
    semente = sub.add_parser(
        "semente", help="cria a aventura original mínima (O Porão da Taverna) numa pasta"
    )
    semente.add_argument(
        "pasta", type=Path, help=f"pasta de aventuras; o arquivo {ARQUIVO_SEMENTE} é criado nela"
    )
    sub.add_parser("sobre", help="versão, licença do SRD e a atribuição exigida")
    novo = sub.add_parser("novo", help="cria uma campanha da aventura semente com a personagem pré-gerada")
    novo.add_argument("pasta", type=Path, help="pasta de campanhas; o arquivo da campanha é criado nela")
    novo.add_argument("--nome", default=NOME_CAMPANHA_DEMO, help="nome da campanha")
    jogar = sub.add_parser("jogar", help="abre uma campanha no terminal")
    jogar.add_argument("campanha", type=Path, help="arquivo .sqlite da campanha")
    jogar.add_argument("--aventura", type=Path, required=True, help="arquivo .sqlite da aventura")
    jogar.add_argument(
        "--mestre", choices=["roteiro"], default="roteiro", help="provedor do mestre (fase 1: só o roteiro)"
    )
    demo = sub.add_parser("demo", help="comando único: cria a semente e a campanha numa pasta e joga")
    demo.add_argument("pasta", type=Path, help="pasta da demonstração (criada se não existir)")
    demo.add_argument("--so-preparar", action="store_true", help="cria os arquivos e sai, sem abrir a tela")
    return parser


def _comando_sobre() -> int:
    from narrador.srd.atribuicao import texto_sobre
    from narrador.srd.modelo import VERSAO_SRD

    print(texto_sobre(__version__, VERSAO_SRD))
    return 0


def _criar_semente(caminho: Path) -> None:
    from narrador.modulo import banco as modulo

    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = modulo.criar(caminho)
    modulo.aplicar_semente(con)
    con.close()


def _comando_semente(pasta: Path) -> int:
    caminho = pasta / ARQUIVO_SEMENTE
    if caminho.exists():
        print(f"já existe: {caminho}")
        return 1
    _criar_semente(caminho)
    print(f"semente aplicada: {caminho}")
    return 0


def _comando_novo(pasta: Path, nome: str) -> int:
    from narrador.mestre.jogo import criar_campanha_da_semente

    try:
        criada = criar_campanha_da_semente(pasta, nome)
    except FileExistsError as ex:
        print(f"já existe: {ex}")
        return 1
    print(f"campanha criada: {criada.caminho}")
    return 0


def _jogar(campanha: Path, aventura: Path) -> int:
    from narrador.campanha import sessoes
    from narrador.mestre.jogo import Jogo
    from narrador.mestre.roteiros import RoteiroDoPorao

    jogo = Jogo(campanha, aventura, RoteiroDoPorao())
    try:
        iniciais = jogo.abrir()
    except sessoes.CampanhaTravadaError as ex:
        print(f"não abriu: {ex}")
        return 2
    except sessoes.CampanhaInconsistenteError as ex:
        print(f"campanha inconsistente, aberta só em leitura: {ex}")
        return 3
    from narrador.terminal import Terminal

    Terminal(jogo, iniciais).run()
    if not jogo.encerrado:
        for m in jogo.encerrar():
            print(m.texto)
    return 0


def _comando_demo(pasta: Path, so_preparar: bool) -> int:
    from narrador.mestre.jogo import criar_campanha_da_semente

    aventura = pasta / "aventuras" / ARQUIVO_SEMENTE
    if not aventura.exists():
        _criar_semente(aventura)
        print(f"semente aplicada: {aventura}")
    pasta_campanhas = pasta / "campanhas"
    try:
        campanha = criar_campanha_da_semente(pasta_campanhas, NOME_CAMPANHA_DEMO).caminho
        print(f"campanha criada: {campanha}")
    except FileExistsError as ex:
        campanha = Path(str(ex))
        print(f"campanha existente, retomando: {campanha}")
    if so_preparar:
        return 0
    return _jogar(campanha, aventura)


def principal(argv: Sequence[str] | None = None) -> int:
    args = montar_parser().parse_args(argv)
    if args.versao:
        print(f"narrador {__version__}")
        return 0
    if args.comando == "semente":
        return _comando_semente(args.pasta)
    if args.comando == "sobre":
        return _comando_sobre()
    if args.comando == "novo":
        return _comando_novo(args.pasta, args.nome)
    if args.comando == "jogar":
        return _jogar(args.campanha, args.aventura)
    if args.comando == "demo":
        return _comando_demo(args.pasta, args.so_preparar)
    montar_parser().print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(principal())
