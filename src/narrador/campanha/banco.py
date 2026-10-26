"""Campanha viva: um arquivo SQLite por campanha, criado a partir das migrações do pacote."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from narrador import banco


def criar(caminho: str | Path = banco.EM_MEMORIA) -> sqlite3.Connection:
    """Abre o arquivo da campanha e aplica as migrações que faltam."""
    con = banco.abrir(caminho)
    banco.migrar(con, banco.migracoes_do_pacote("narrador.campanha"))
    return con
