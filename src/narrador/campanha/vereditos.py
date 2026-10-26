"""O registro de vereditos no diário (casos de uso C04, C05, G04).

Toda tentativa e toda pergunta deixam um registro comparável, para a consistência entre
sessões e para a revisão do dono da mesa.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from narrador.motor.veredito import VereditoAnterior, VereditoValidado


@dataclass(frozen=True)
class VereditoRegistrado:
    seq: int
    tipo: str
    situacao: str
    pericia: str | None
    dificuldade: int | None
    pergunta: bool
    rolagem_seq: int | None
    divergiu_de: int | None


def registrar(
    con: sqlite3.Connection,
    campanha_id: str,
    sessao_id: str | None,
    origem: str,
    veredito: VereditoValidado,
    tentativa: str,
    pergunta: bool = False,
    rolagem_seq: int | None = None,
    divergiu_de: int | None = None,
    motivo_divergencia: str | None = None,
) -> VereditoRegistrado:
    dados = {
        "tentativa": tentativa,
        "situacao": veredito.situacao,
        "tipo": veredito.tipo,
        "pericia": veredito.teste.chave if veredito.teste else None,
        "dificuldade": veredito.dificuldade,
        "modo": veredito.modo,
        "pergunta": pergunta,
        "rolagem_seq": rolagem_seq,
        "divergiu_de": divergiu_de,
        "motivo_divergencia": motivo_divergencia,
    }
    con.execute("begin")
    try:
        cur = con.execute(
            "insert into diario (campanha_id, sessao_id, tipo, origem, dados) values (?, ?, 'veredito', ?, ?)",
            (campanha_id, sessao_id, origem, json.dumps(dados, ensure_ascii=False)),
        )
        seq = cur.lastrowid
        assert seq is not None
        con.execute(
            "insert into veredito (seq, campanha_id, situacao, tipo, pericia, dificuldade, pergunta, rolagem_seq, divergiu_de, motivo_divergencia)"
            " values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                seq,
                campanha_id,
                veredito.situacao,
                veredito.tipo,
                veredito.teste.chave if veredito.teste else None,
                veredito.dificuldade,
                int(pergunta),
                rolagem_seq,
                divergiu_de,
                motivo_divergencia,
            ),
        )
        con.execute("commit")
    except Exception:
        con.execute("rollback")
        raise
    return VereditoRegistrado(
        seq,
        veredito.tipo,
        veredito.situacao,
        veredito.teste.chave if veredito.teste else None,
        veredito.dificuldade,
        pergunta,
        rolagem_seq,
        divergiu_de,
    )


def anteriores(con: sqlite3.Connection, campanha_id: str) -> list[VereditoAnterior]:
    """Os vereditos de AÇÃO já dados na campanha (perguntas não criam precedente)."""
    return [
        VereditoAnterior(seq, situacao, tipo, pericia, dificuldade)
        for seq, situacao, tipo, pericia, dificuldade in con.execute(
            "select seq, situacao, tipo, pericia, dificuldade from veredito where campanha_id = ? and pergunta = 0 order by seq",
            (campanha_id,),
        )
    ]


def listar(con: sqlite3.Connection, campanha_id: str) -> list[VereditoRegistrado]:
    return [
        VereditoRegistrado(
            seq, tipo, situacao, pericia, dificuldade, bool(pergunta), rolagem_seq, divergiu_de
        )
        for seq, tipo, situacao, pericia, dificuldade, pergunta, rolagem_seq, divergiu_de in con.execute(
            "select seq, tipo, situacao, pericia, dificuldade, pergunta, rolagem_seq, divergiu_de from veredito where campanha_id = ? order by seq",
            (campanha_id,),
        )
    ]
