"""Pasta de aventuras: um arquivo SQLite por aventura importada, ao lado do arquivo original."""

from __future__ import annotations

import sqlite3
from importlib import resources
from pathlib import Path

from narrador import banco

SEMENTE_PORAO = "porao_da_taverna.sql"


def criar(caminho: str | Path = banco.EM_MEMORIA) -> sqlite3.Connection:
    """Abre o arquivo da aventura e aplica as migrações que faltam."""
    con = banco.abrir(caminho)
    banco.migrar(con, banco.migracoes_do_pacote("narrador.modulo"))
    return con


def aplicar_semente(con: sqlite3.Connection, nome: str = SEMENTE_PORAO) -> None:
    """Aplica a aventura original mínima do projeto, já no formato canônico, versão 1 publicada."""
    sql = (resources.files("narrador.modulo") / "semente" / nome).read_text(encoding="utf-8")
    # Em transação: ou a semente inteira entra, ou nada entra.
    con.executescript("\n".join(["begin;", sql, "commit;"]))
