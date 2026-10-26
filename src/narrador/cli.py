"""O programa de terminal. Na fundação (card N-01) só responde com a versão."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from narrador import __version__


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="narrador",
        description="Mestre de D&D 5e (regras de 2024, SRD 5.2) por inteligência artificial.",
    )
    parser.add_argument("--versao", action="store_true", help="mostra a versão e sai")
    return parser


def principal(argv: Sequence[str] | None = None) -> int:
    args = montar_parser().parse_args(argv)
    if args.versao:
        print(f"narrador {__version__}")
        return 0
    montar_parser().print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(principal())
