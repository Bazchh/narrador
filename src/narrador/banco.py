"""Abertura de arquivos SQLite e aplicação de migrações, comum à campanha viva e à pasta
de aventuras (Blueprint, capítulo 3).

Regras: toda migração é um arquivo .sql numerado na pasta de migrações do pacote; cada
uma roda uma vez, em transação, e fica registrada na tabela `migracao`. Um arquivo já em
uso recebe só as migrações que ainda não tem, sem perder registro.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

EM_MEMORIA = ":memory:"


class MigracaoInvalidaError(RuntimeError):
    """Nome de arquivo de migração fora do padrão NNNN_nome.sql."""


def abrir(caminho: str | Path) -> sqlite3.Connection:
    """Abre (ou cria) o arquivo com chaves estrangeiras ligadas."""
    con = sqlite3.connect(str(caminho), isolation_level=None)
    con.execute("pragma foreign_keys = on")
    if str(caminho) != EM_MEMORIA:
        con.execute("pragma journal_mode = wal")
    return con


def _versao_de(nome: str) -> int:
    prefixo = nome.split("_", 1)[0]
    if not (nome.endswith(".sql") and prefixo.isdigit() and len(prefixo) == 4):
        raise MigracaoInvalidaError(f"migração fora do padrão NNNN_nome.sql: {nome}")
    return int(prefixo)


def listar_migracoes(pasta: Traversable) -> list[tuple[int, str, str]]:
    """(versão, nome, sql) em ordem crescente de versão."""
    itens = [
        (_versao_de(p.name), p.name, p.read_text(encoding="utf-8"))
        for p in pasta.iterdir()
        if p.name.endswith(".sql")
    ]
    itens.sort()
    versoes = [v for v, _, _ in itens]
    if len(set(versoes)) != len(versoes):
        raise MigracaoInvalidaError(f"versão repetida em {pasta}")
    return itens


def migrar(con: sqlite3.Connection, migracoes: Iterable[tuple[int, str, str]]) -> list[int]:
    """Aplica as migrações que faltam; devolve as versões aplicadas nesta chamada."""
    con.execute(
        "create table if not exists migracao (versao integer primary key, nome text not null,"
        " aplicada_em text not null default (strftime('%Y-%m-%dT%H:%M:%fZ','now')))"
    )
    aplicadas = {v for (v,) in con.execute("select versao from migracao")}
    novas: list[int] = []
    for versao, nome, sql in migracoes:
        if versao in aplicadas:
            continue
        # executescript fecha qualquer transação aberta antes de rodar e o script pode
        # conter pragmas que não aceitam transação; o registro em `migracao` só é gravado
        # se o script inteiro rodou sem erro.
        con.executescript(sql)
        con.execute("insert into migracao (versao, nome) values (?, ?)", (versao, nome))
        novas.append(versao)
    return novas


def migracoes_do_pacote(pacote: str) -> list[tuple[int, str, str]]:
    return listar_migracoes(resources.files(pacote) / "migracoes")


def tabelas(con: sqlite3.Connection) -> list[str]:
    return [
        n
        for (n,) in con.execute(
            "select name from sqlite_master where type = 'table' and name not like 'sqlite_%' and name <> 'migracao' order by name"
        )
    ]


def gatilhos(con: sqlite3.Connection) -> list[str]:
    return [n for (n,) in con.execute("select name from sqlite_master where type = 'trigger' order by name")]
