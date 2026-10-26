"""O diário de rolagens (casos de uso E01 e E06): grava cada rolagem com semente, contador,
dados, composição e motivo, e reproduz qualquer uma a partir do registro.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from narrador.motor import dados as motor


class CampanhaInexistenteError(LookupError):
    """Campanha não encontrada no arquivo."""


@dataclass(frozen=True)
class RolagemRegistrada:
    seq: int
    contador: int | None
    expressao: str
    modo: motor.Modo
    dados: tuple[int, ...]
    descartados: tuple[int, ...]
    modificadores: dict[str, int]
    total: int
    motivo: str
    informada: bool

    @property
    def composicao(self) -> str:
        if self.informada:
            return f"informada: {', '.join(map(str, self.dados))} = {self.total}"
        rol = motor.Rolagem(
            "",
            self.contador or 0,
            motor.Expressao.analisar(self.expressao),
            self.modo,
            self.dados,
            self.descartados,
            self.modificadores,
        )
        return rol.composicao()


@dataclass(frozen=True)
class Comparacao:
    seq: int
    contador: int
    registrado: tuple[int, ...]
    reproduzido: tuple[int, ...]
    total_registrado: int
    total_reproduzido: int

    @property
    def igual(self) -> bool:
        return self.registrado == self.reproduzido and self.total_registrado == self.total_reproduzido


def _semente(con: sqlite3.Connection, campanha_id: str) -> str:
    linha = con.execute("select semente from campanha where id = ?", (campanha_id,)).fetchone()
    if linha is None:
        raise CampanhaInexistenteError(campanha_id)
    semente: str = linha[0]
    return semente


def _proximo_contador(con: sqlite3.Connection, campanha_id: str) -> int:
    (maior,) = con.execute(
        "select coalesce(max(contador), 0) from rolagem where campanha_id = ?", (campanha_id,)
    ).fetchone()
    return int(maior) + 1


def _gravar(
    con: sqlite3.Connection,
    campanha_id: str,
    sessao_id: str | None,
    origem: str,
    contador: int | None,
    expressao: str,
    modo: motor.Modo,
    dados: tuple[int, ...],
    descartados: tuple[int, ...],
    modificadores: dict[str, int],
    total: int,
    motivo: str,
    informada: bool,
) -> RolagemRegistrada:
    registro = {
        "contador": contador,
        "expressao": expressao,
        "modo": modo,
        "dados": list(dados),
        "descartados": list(descartados),
        "modificadores": modificadores,
        "total": total,
        "motivo": motivo,
        "informada": informada,
    }
    con.execute("begin")
    try:
        cur = con.execute(
            "insert into diario (campanha_id, sessao_id, tipo, origem, dados) values (?, ?, 'rolagem', ?, ?)",
            (campanha_id, sessao_id, origem, json.dumps(registro, ensure_ascii=False)),
        )
        seq = cur.lastrowid
        assert seq is not None
        con.execute(
            "insert into rolagem (seq, campanha_id, contador, expressao, modo, dados, modificadores, total, motivo, informada)"
            " values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                seq,
                campanha_id,
                contador,
                expressao,
                modo,
                json.dumps({"dados": list(dados), "descartados": list(descartados)}),
                json.dumps(modificadores, ensure_ascii=False),
                total,
                motivo,
                int(informada),
            ),
        )
        con.execute("commit")
    except Exception:
        con.execute("rollback")
        raise
    return RolagemRegistrada(
        seq, contador, expressao, modo, dados, descartados, modificadores, total, motivo, informada
    )


def rolar(
    con: sqlite3.Connection,
    campanha_id: str,
    sessao_id: str | None,
    origem: str,
    expressao: str,
    motivo: str,
    modo: motor.Modo = "normal",
    modificadores: dict[str, int] | None = None,
) -> RolagemRegistrada:
    """Rola pelo motor na próxima posição do gerador da campanha e grava no diário."""
    exp = motor.Expressao.analisar(expressao)
    contador = _proximo_contador(con, campanha_id)
    rol = motor.rolar(_semente(con, campanha_id), contador, exp, modo, modificadores)
    return _gravar(
        con,
        campanha_id,
        sessao_id,
        origem,
        contador,
        str(exp),
        modo,
        rol.dados,
        rol.descartados,
        rol.modificadores,
        rol.total,
        motivo,
        False,
    )


def informar(
    con: sqlite3.Connection,
    campanha_id: str,
    sessao_id: str | None,
    origem: str,
    expressao: str,
    dados: tuple[int, ...],
    motivo: str,
    modificadores: dict[str, int] | None = None,
) -> RolagemRegistrada:
    """Grava uma rolagem feita em dado físico: sem contador, marcada como informada."""
    exp = motor.Expressao.analisar(expressao)
    if len(dados) != exp.quantidade or any(not 1 <= d <= exp.faces for d in dados):
        raise motor.ExpressaoInvalidaError(f"dados informados {dados} não cabem em {exp}")
    _semente(con, campanha_id)
    mods = dict(modificadores or {})
    total = sum(dados) + exp.modificador + sum(mods.values())
    return _gravar(
        con, campanha_id, sessao_id, origem, None, str(exp), "normal", dados, (), mods, total, motivo, True
    )


def listar(con: sqlite3.Connection, campanha_id: str) -> list[RolagemRegistrada]:
    linhas = con.execute(
        "select seq, contador, expressao, modo, dados, modificadores, total, motivo, informada"
        " from rolagem where campanha_id = ? order by seq",
        (campanha_id,),
    ).fetchall()
    saida = []
    for seq, contador, expressao, modo, dados_json, mods_json, total, motivo, informada in linhas:
        d = json.loads(dados_json)
        saida.append(
            RolagemRegistrada(
                seq,
                contador,
                expressao,
                modo,
                tuple(d["dados"]),
                tuple(d["descartados"]),
                json.loads(mods_json),
                total,
                motivo,
                bool(informada),
            )
        )
    return saida


def reproduzir(
    con: sqlite3.Connection, campanha_id: str, de: int | None = None, ate: int | None = None
) -> list[Comparacao]:
    """Refaz cada rolagem com contador a partir da semente e compara dado a dado (E06).

    Rolagens informadas não entram: dado físico não é reproduzível.
    """
    semente = _semente(con, campanha_id)
    comparacoes = []
    for r in listar(con, campanha_id):
        if r.informada or r.contador is None:
            continue
        if (de is not None and r.contador < de) or (ate is not None and r.contador > ate):
            continue
        refeita = motor.rolar(semente, r.contador, r.expressao, r.modo, r.modificadores)
        comparacoes.append(Comparacao(r.seq, r.contador, r.dados, refeita.dados, r.total, refeita.total))
    return comparacoes
