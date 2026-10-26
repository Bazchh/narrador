"""O combate na campanha viva: rolagens pelo diário, combatentes a partir das fichas e do
SRD, e o estado gravado a cada mudança para a retomada (casos D01 a D08, F05)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from typing import Any

from narrador.campanha import personagens, rolagens
from narrador.motor import combate
from narrador.motor.combate import Ataque, Combatente, EstadoCombate, Rolagem, Zona
from narrador.srd import catalogo
from narrador.srd.modelo import Criatura, Srd


def rolador(con: sqlite3.Connection, campanha_id: str, sessao_id: str | None, origem: str) -> combate.Rolador:
    """Um Rolador do motor que grava cada rolagem no diário da campanha."""

    def rolar(expressao: str, modo: combate.Modo, motivo: str, modificadores: dict[str, int]) -> Rolagem:
        r = rolagens.rolar(con, campanha_id, sessao_id, origem, expressao, motivo, modo, modificadores)
        return Rolagem(r.dados, r.total, r.seq)

    return rolar


def combatente_do_jogador(
    con: sqlite3.Connection,
    campanha_id: str,
    personagem_id: str,
    pv_atual: int | None = None,
    srd: Srd | None = None,
) -> Combatente:
    gravada, d = personagens.consultar(con, campanha_id, personagem_id, srd)
    ataques = tuple(
        Ataque(
            nome=a.arma.nome_pt,
            bonus=a.bonus_ataque.total,
            dano_dados=a.dano_dados,
            bonus_dano=a.bonus_dano.total,
            dano_tipo=a.dano_tipo,
            alcance_pes=a.arma.alcance_pes or 5,
            a_distancia=a.arma.alcance_pes > 0 and "Thrown" not in a.arma.propriedades,
        )
        for a in d.ataques
    )
    pv_max = d.pontos_de_vida_maximos.total
    return Combatente(
        id=personagem_id,
        nome=gravada.ficha.nome,
        lado="jogador",
        classe_armadura=d.classe_armadura.total,
        pontos_de_vida_maximos=pv_max,
        pontos_de_vida=pv_max if pv_atual is None else pv_atual,
        bonus_iniciativa=d.iniciativa.total,
        ataques=ataques,
    )


def combatente_da_criatura(
    instancia_id: str,
    criatura: Criatura,
    zona: Zona = "perto",
    percebeu: bool = True,
    nome: str | None = None,
) -> Combatente:
    ataques = tuple(
        Ataque(
            a.nome,
            a.bonus,
            a.dano_dados.split("+")[0].split("-")[0],
            _bonus_do_dano(a.dano_dados),
            a.dano_tipo,
            a.alcance_pes,
            a.tipo == "distancia",
        )
        for a in criatura.ataques
    )
    return Combatente(
        id=instancia_id,
        nome=nome or criatura.nome_pt,
        lado="hostil",
        classe_armadura=criatura.classe_armadura,
        pontos_de_vida_maximos=criatura.pontos_de_vida,
        pontos_de_vida=criatura.pontos_de_vida,
        bonus_iniciativa=criatura.bonus_iniciativa,
        ataques=ataques,
        zona=zona,
        surpreso=not percebeu,
        nivel_de_desafio=criatura.nivel_de_desafio,
        pontos_de_experiencia=criatura.pontos_de_experiencia,
    )


def _bonus_do_dano(expressao: str) -> int:
    for sinal in ("+", "-"):
        if sinal in expressao:
            _base, k = expressao.split(sinal, 1)
            return int(k) if sinal == "+" else -int(k)
    return 0


def criatura_do_srd(srd_id: str, srd: Srd | None = None) -> Criatura:
    return catalogo.criatura(srd_id, srd)


# ---------------------------------------------------------------- persistência do estado


def _serializar(estado: EstadoCombate) -> str:
    bruto = asdict(estado)
    for c in bruto["combatentes"].values():
        for campo in ("resistencias", "vulnerabilidades", "imunidades", "condicoes"):
            c[campo] = sorted(c[campo])
    return json.dumps(bruto, ensure_ascii=False)


def _desserializar(texto: str) -> EstadoCombate:
    bruto = json.loads(texto)
    combatentes = {}
    for cid, c in bruto["combatentes"].items():
        c["ataques"] = tuple(Ataque(**a) for a in c["ataques"])
        for campo in ("resistencias", "vulnerabilidades", "imunidades", "condicoes"):
            c[campo] = frozenset(c[campo])
        combatentes[cid] = Combatente(**c)
    return EstadoCombate(
        estado=bruto["estado"],
        combatentes=combatentes,
        ordem=tuple(bruto["ordem"]),
        indice=bruto["indice"],
        rodada=bruto["rodada"],
        economia=combate.Economia(**bruto["economia"]),
        rodadas_sem_dano=bruto["rodadas_sem_dano"],
        houve_dano_na_rodada=bruto["houve_dano_na_rodada"],
        aguardando_mestre=bruto["aguardando_mestre"],
        eventos=tuple(combate.Evento(**e) for e in bruto["eventos"]),
    )


def gravar(
    con: sqlite3.Connection,
    campanha_id: str,
    sessao_id: str | None,
    estado: EstadoCombate,
    origem: str = "D01",
) -> int:
    """Grava o estado inteiro como fato de evento: é o ponto de retomada (F05)."""
    ultimo = estado.eventos[-1].texto if estado.eventos else "combate"
    dados: dict[str, Any] = {"combate": json.loads(_serializar(estado))}
    con.execute("begin")
    try:
        cur = con.execute(
            "insert into diario (campanha_id, sessao_id, tipo, origem, dados) values (?, ?, 'fato', ?, ?)",
            (campanha_id, sessao_id, origem, json.dumps(dados, ensure_ascii=False)),
        )
        seq = cur.lastrowid
        assert seq is not None
        con.execute(
            "insert into fato (seq, campanha_id, tipo_fato, referencia, conhecimento, resumo) values (?, ?, 'evento', 'combate', 'conhecido', ?)",
            (seq, campanha_id, f"combate (rodada {estado.rodada}, {estado.estado}): {ultimo}"),
        )
        con.execute("commit")
    except Exception:
        con.execute("rollback")
        raise
    return int(seq)


def carregar_ultimo(con: sqlite3.Connection, campanha_id: str) -> EstadoCombate | None:
    linha = con.execute(
        "select d.dados from diario d join fato f on f.seq = d.seq"
        " where d.campanha_id = ? and f.referencia = 'combate' order by d.seq desc limit 1",
        (campanha_id,),
    ).fetchone()
    if linha is None:
        return None
    return _desserializar(json.dumps(json.loads(linha[0])["combate"]))
