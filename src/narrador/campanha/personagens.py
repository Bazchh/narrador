"""Fichas na campanha viva, versionadas (casos de uso B02, B03, B04).

Cada gravação é uma versão nova; a anterior fica. A consulta devolve a versão mais recente
com os derivados calculados pelo motor e a origem de cada número.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass

from narrador.motor import ficha as motor_ficha
from narrador.srd import catalogo
from narrador.srd.modelo import Srd


class PersonagemInexistenteError(LookupError):
    """Personagem não encontrado na campanha."""


@dataclass(frozen=True)
class FichaGravada:
    personagem_id: str
    versao: int
    ficha: motor_ficha.Ficha


def gravar(
    con: sqlite3.Connection,
    campanha_id: str,
    ficha: motor_ficha.Ficha,
    personagem_id: str | None = None,
    srd: Srd | None = None,
) -> FichaGravada:
    """Valida contra o SRD e grava como nova versão; a anterior é preservada."""
    srd = srd or catalogo.carregar()
    motor_ficha.validar(ficha, srd)
    pid = personagem_id or f"pj-{uuid.uuid4().hex[:12]}"
    (ultima,) = con.execute(
        "select coalesce(max(versao), 0) from personagem where id = ? and campanha_id = ?", (pid, campanha_id)
    ).fetchone()
    versao = int(ultima) + 1
    con.execute(
        "insert into personagem (id, versao, campanha_id, nome, origem, ficha, srd_versao) values (?, ?, ?, ?, ?, ?, ?)",
        (pid, versao, campanha_id, ficha.nome, ficha.origem, ficha.model_dump_json(), ficha.srd_versao),
    )
    return FichaGravada(pid, versao, ficha)


def carregar(
    con: sqlite3.Connection, campanha_id: str, personagem_id: str, versao: int | None = None
) -> FichaGravada:
    if versao is None:
        linha = con.execute(
            "select versao, ficha from personagem where id = ? and campanha_id = ? order by versao desc limit 1",
            (personagem_id, campanha_id),
        ).fetchone()
    else:
        linha = con.execute(
            "select versao, ficha from personagem where id = ? and campanha_id = ? and versao = ?",
            (personagem_id, campanha_id, versao),
        ).fetchone()
    if linha is None:
        raise PersonagemInexistenteError(personagem_id)
    return FichaGravada(personagem_id, int(linha[0]), motor_ficha.Ficha.model_validate_json(linha[1]))


def consultar(
    con: sqlite3.Connection, campanha_id: str, personagem_id: str, srd: Srd | None = None
) -> tuple[FichaGravada, motor_ficha.Derivados]:
    """A ficha mais recente com os derivados e a composição de cada número (B03)."""
    gravada = carregar(con, campanha_id, personagem_id)
    return gravada, motor_ficha.calcular(gravada.ficha, srd)


def versoes(con: sqlite3.Connection, campanha_id: str, personagem_id: str) -> list[int]:
    return [
        int(v)
        for (v,) in con.execute(
            "select versao from personagem where id = ? and campanha_id = ? order by versao",
            (personagem_id, campanha_id),
        )
    ]
