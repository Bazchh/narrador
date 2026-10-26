"""Fatos estabelecidos na campanha viva (casos de uso F01, F04; regra RN-01).

Fato é imutável: correção entra como fato novo que sucede o anterior (substitui_seq),
nunca como alteração. Fato ativo é o que não foi sucedido.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Literal

from narrador.motor.verificacao import FatoAtivo

TipoFato = Literal["estado_local", "estado_personagem", "posse", "relacao", "conhecimento", "evento"]
Conhecimento = Literal["conhecido", "oculto", "acredita"]


@dataclass(frozen=True)
class FatoRegistrado:
    seq: int
    tipo: TipoFato
    referencia: str | None
    conhecimento: Conhecimento
    resumo: str
    substitui_seq: int | None


def registrar(
    con: sqlite3.Connection,
    campanha_id: str,
    sessao_id: str | None,
    origem: str,
    tipo: TipoFato,
    resumo: str,
    referencia: str | None = None,
    conhecimento: Conhecimento = "conhecido",
    substitui_seq: int | None = None,
    cena_id: str | None = None,
) -> FatoRegistrado:
    dados = {
        "tipo": tipo,
        "referencia": referencia,
        "conhecimento": conhecimento,
        "resumo": resumo,
        "substitui_seq": substitui_seq,
    }
    con.execute("begin")
    try:
        cur = con.execute(
            "insert into diario (campanha_id, sessao_id, tipo, cena_id, origem, dados) values (?, ?, 'fato', ?, ?, ?)",
            (campanha_id, sessao_id, cena_id, origem, json.dumps(dados, ensure_ascii=False)),
        )
        seq = cur.lastrowid
        assert seq is not None
        con.execute(
            "insert into fato (seq, campanha_id, tipo_fato, referencia, conhecimento, substitui_seq, resumo) values (?, ?, ?, ?, ?, ?, ?)",
            (seq, campanha_id, tipo, referencia, conhecimento, substitui_seq, resumo),
        )
        con.execute("commit")
    except Exception:
        con.execute("rollback")
        raise
    return FatoRegistrado(int(seq), tipo, referencia, conhecimento, resumo, substitui_seq)


def ativos(con: sqlite3.Connection, campanha_id: str, nomes: dict[str, str] | None = None) -> list[FatoAtivo]:
    """Fatos não sucedidos por outro, na ordem; `nomes` liga referência canônica a nome para a verificação."""
    nomes = nomes or {}
    linhas = con.execute(
        "select f.seq, f.tipo_fato, f.referencia, f.resumo from fato f"
        " where f.campanha_id = ? and f.referencia is not 'combate'"
        " and not exists (select 1 from fato s where s.campanha_id = f.campanha_id and s.substitui_seq = f.seq)"
        " order by f.seq",
        (campanha_id,),
    ).fetchall()
    return [
        FatoAtivo(seq, tipo, ref, resumo, nomes.get(ref) if ref else None)
        for seq, tipo, ref, resumo in linhas
    ]


def por_item(con: sqlite3.Connection, campanha_id: str) -> dict[str, list[str]]:
    """Os fatos ativos agrupados por item canônico, para o recorte da cena (A05)."""
    saida: dict[str, list[str]] = {}
    for f in ativos(con, campanha_id):
        if f.referencia:
            saida.setdefault(f.referencia, []).append(f.resumo)
    return saida


def segredos_descobertos(con: sqlite3.Connection, campanha_id: str) -> set[str]:
    """Um segredo está descoberto quando há fato de conhecimento 'conhecido' apontando para ele (F04)."""
    return {
        ref
        for (ref,) in con.execute(
            "select referencia from fato where campanha_id = ? and tipo_fato = 'conhecimento' and conhecimento = 'conhecido' and referencia is not null",
            (campanha_id,),
        )
    }


def listar(con: sqlite3.Connection, campanha_id: str) -> list[FatoRegistrado]:
    return [
        FatoRegistrado(seq, tipo, ref, conh, resumo, sub)
        for seq, tipo, ref, conh, resumo, sub in con.execute(
            "select seq, tipo_fato, referencia, conhecimento, resumo, substitui_seq from fato where campanha_id = ? and referencia is not 'combate' order by seq",
            (campanha_id,),
        )
    ]
