"""O programa de terminal. Na fundação (card N-01) só responde com a versão."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from narrador import __version__


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
        "pasta", type=Path, help="pasta de aventuras; o arquivo porao-da-taverna.sqlite é criado nela"
    )
    sub.add_parser("sobre", help="versão, licença do SRD e a atribuição exigida")
    return parser


def _comando_sobre() -> int:
    from narrador.srd.atribuicao import texto_sobre
    from narrador.srd.modelo import VERSAO_SRD

    print(texto_sobre(__version__, VERSAO_SRD))
    return 0


def _comando_semente(pasta: Path) -> int:
    from narrador.modulo import banco as modulo

    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / "porao-da-taverna.sqlite"
    if caminho.exists():
        print(f"já existe: {caminho}")
        return 1
    con = modulo.criar(caminho)
    modulo.aplicar_semente(con)
    con.close()
    print(f"semente aplicada: {caminho}")
    return 0


def principal(argv: Sequence[str] | None = None) -> int:
    args = montar_parser().parse_args(argv)
    if args.versao:
        print(f"narrador {__version__}")
        return 0
    if args.comando == "semente":
        return _comando_semente(args.pasta)
    if args.comando == "sobre":
        return _comando_sobre()
    montar_parser().print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(principal())
