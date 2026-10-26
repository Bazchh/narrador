"""Campanha e sessão na campanha viva: criar, abrir, retomar, encerrar, instantâneo e a
trava de processo (casos C01, C02, C09, F05, G01).

Toda gravação já é atômica pelo SQLite (transação e diário só de inserção). O que este
módulo acrescenta é o estado consolidado para abrir rápido, a detecção de sessão não
encerrada e a trava que impede duas aberturas da mesma campanha.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import unicodedata
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from narrador.campanha import banco as campanha_banco
from narrador.campanha import combate as campanha_combate
from narrador.campanha import personagens
from narrador.motor import ficha as motor_ficha
from narrador.motor.combate import EstadoCombate

SUFIXO_TRAVA = ".trava"


class CampanhaTravadaError(RuntimeError):
    """Outra abertura da mesma campanha está ativa."""


class CampanhaInconsistenteError(RuntimeError):
    """O estado consolidado não bate com o diário; abrir só em leitura (C02 E2)."""


def _slug(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-") or "campanha"


@dataclass(frozen=True)
class Instantaneo:
    """Estado consolidado até um registro do diário (G01)."""

    ate_seq: int
    cena_atual: str | None
    relogio_minutos: int
    personagem_id: str | None
    sessao_numero: int
    pontos_de_vida: int | None = None
    extras: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------- trava de processo


_WINDOWS = sys.platform == "win32"  # em variável: o verificador de tipos não deve podar o outro ramo


def _processo_vivo(pid: int) -> bool:
    if pid == os.getpid():
        return True
    if _WINDOWS:
        import ctypes

        kernel32 = ctypes.CDLL(
            "kernel32"
        )  # CDLL existe em toda plataforma para o verificador; em x64 a convenção é a mesma
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        kernel32.CloseHandle(handle)
        return True
    return _vivo_posix(pid)


def _vivo_posix(pid: int) -> bool:  # pragma: no cover - só roda fora do Windows
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


class Trava:
    """Um arquivo ao lado da campanha com o pid de quem a segura. Trava velha (pid morto) é retomada."""

    def __init__(self, caminho_campanha: Path):
        self.caminho = Path(str(caminho_campanha) + SUFIXO_TRAVA)

    def adquirir(self) -> None:
        if self.caminho.exists():
            try:
                dono = json.loads(self.caminho.read_text(encoding="utf-8"))
                pid = int(dono.get("pid", 0))
            except (ValueError, OSError):
                pid = 0
            if pid and _processo_vivo(pid) and pid != os.getpid():
                raise CampanhaTravadaError(
                    f"campanha aberta por outro processo (pid {pid}); feche-o ou aguarde"
                )
            self.caminho.unlink(missing_ok=True)
        self.caminho.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")

    def liberar(self) -> None:
        self.caminho.unlink(missing_ok=True)


# ---------------------------------------------------------------- campanha


@dataclass(frozen=True)
class CampanhaCriada:
    caminho: Path
    campanha_id: str
    personagem_id: str


def criar_campanha(
    pasta: Path,
    nome: str,
    aventura_id: str,
    modulo_versao: int,
    ficha: motor_ficha.Ficha,
    cena_inicial: str,
    classificacao: str = "adulto",
    tom: str = "serio",
    configuracao: dict[str, Any] | None = None,
    semente: str | None = None,
) -> CampanhaCriada:
    """C01: arquivo novo, semente de rolagens gerada e gravada, personagem vinculado, primeiro registro.

    `semente` fixa o gerador de dados (roteiros de aceite); vazia, é sorteada."""
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{_slug(nome)}.sqlite"
    if caminho.exists():
        raise FileExistsError(caminho)
    con = campanha_banco.criar(caminho)
    campanha_id = f"cp-{uuid.uuid4().hex[:12]}"
    con.execute(
        "insert into campanha (id, nome, aventura_id, modulo_versao, semente, classificacao, tom, configuracao) values (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            campanha_id,
            nome,
            aventura_id,
            modulo_versao,
            semente or uuid.uuid4().hex,
            classificacao,
            tom,
            json.dumps(configuracao or {}, ensure_ascii=False),
        ),
    )
    pj = personagens.gravar(con, campanha_id, ficha)
    registrar_evento(
        con,
        campanha_id,
        None,
        "C01",
        "campanha criada",
        {"aventura_id": aventura_id, "modulo_versao": modulo_versao, "personagem_id": pj.personagem_id},
    )
    gravar_instantaneo(
        con, campanha_id, Instantaneo(ultimo_seq(con, campanha_id), cena_inicial, 0, pj.personagem_id, 0)
    )
    con.close()
    return CampanhaCriada(caminho, campanha_id, pj.personagem_id)


def registrar_evento(
    con: sqlite3.Connection,
    campanha_id: str,
    sessao_id: str | None,
    origem: str,
    evento: str,
    dados: dict[str, Any] | None = None,
) -> int:
    cur = con.execute(
        "insert into diario (campanha_id, sessao_id, tipo, origem, dados) values (?, ?, 'sessao', ?, ?)",
        (campanha_id, sessao_id, origem, json.dumps({"evento": evento, **(dados or {})}, ensure_ascii=False)),
    )
    assert cur.lastrowid is not None
    return int(cur.lastrowid)


def ultimo_seq(con: sqlite3.Connection, campanha_id: str) -> int:
    (seq,) = con.execute(
        "select coalesce(max(seq), 0) from diario where campanha_id = ?", (campanha_id,)
    ).fetchone()
    return int(seq)


def gravar_instantaneo(con: sqlite3.Connection, campanha_id: str, inst: Instantaneo) -> None:
    con.execute(
        "insert or replace into instantaneo (campanha_id, ate_seq, estado) values (?, ?, ?)",
        (campanha_id, inst.ate_seq, json.dumps(inst.__dict__, ensure_ascii=False)),
    )


def ultimo_instantaneo(con: sqlite3.Connection, campanha_id: str) -> Instantaneo | None:
    linha = con.execute(
        "select estado from instantaneo where campanha_id = ? order by ate_seq desc limit 1", (campanha_id,)
    ).fetchone()
    if linha is None:
        return None
    return Instantaneo(**json.loads(linha[0]))


def campanha_unica(con: sqlite3.Connection) -> str:
    ids = [i for (i,) in con.execute("select id from campanha")]
    if len(ids) != 1:
        raise CampanhaInconsistenteError(f"o arquivo deveria ter uma campanha; tem {len(ids)}")
    return str(ids[0])


# ---------------------------------------------------------------- sessão


@dataclass(frozen=True)
class SessaoAberta:
    sessao_id: str
    numero: int
    instantaneo: Instantaneo
    retomada_de: str | None  # id da sessão interrompida, se houver
    em_combate: bool
    combate: EstadoCombate | None
    narracao_pendente: bool


def _sessao_nao_encerrada(con: sqlite3.Connection, campanha_id: str) -> tuple[str, int] | None:
    linha = con.execute(
        "select id, numero from sessao where campanha_id = ? and encerrada_em is null order by numero desc limit 1",
        (campanha_id,),
    ).fetchone()
    return (linha[0], int(linha[1])) if linha else None


def _narracao_pendente(con: sqlite3.Connection, campanha_id: str, sessao_id: str) -> bool:
    """Houve rolagem ou ação depois da última narração aprovada nesta sessão?"""
    ultima_narracao = (
        con.execute(
            "select max(seq) from diario where campanha_id = ? and sessao_id = ? and tipo = 'consulta' and origem = 'narrar'"
            " and json_extract(dados, '$.erro') is null",
            (campanha_id, sessao_id),
        ).fetchone()[0]
        or 0
    )
    ultima_acao = (
        con.execute(
            "select max(seq) from diario where campanha_id = ? and sessao_id = ? and tipo in ('rolagem', 'veredito', 'fato')",
            (campanha_id, sessao_id),
        ).fetchone()[0]
        or 0
    )
    return int(ultima_acao) > int(ultima_narracao)


def abrir_sessao(con: sqlite3.Connection, campanha_id: str) -> SessaoAberta:
    """C02 e F05: abre a próxima sessão; se há uma não encerrada, marca como interrompida e retoma."""
    inst = ultimo_instantaneo(con, campanha_id)
    if inst is None:
        raise CampanhaInconsistenteError("campanha sem instantâneo")
    if inst.ate_seq > ultimo_seq(con, campanha_id):
        raise CampanhaInconsistenteError("instantâneo aponta para registro que não existe no diário")
    pendente = _sessao_nao_encerrada(con, campanha_id)
    combate = campanha_combate.carregar_ultimo(con, campanha_id)
    em_combate = combate is not None and combate.estado != "encerrado"
    narracao_pendente = False
    retomada_de = None
    con.execute("begin")
    try:
        if pendente is not None:
            retomada_de, numero_anterior = pendente
            narracao_pendente = _narracao_pendente(con, campanha_id, retomada_de)
            con.execute(
                "update sessao set encerrada_em = strftime('%Y-%m-%dT%H:%M:%fZ','now'), motivo_fim = 'interrompida' where id = ?",
                (retomada_de,),
            )
            numero = numero_anterior + 1
        else:
            (maior,) = con.execute(
                "select coalesce(max(numero), 0) from sessao where campanha_id = ?", (campanha_id,)
            ).fetchone()
            numero = int(maior) + 1
        sessao_id = f"s-{uuid.uuid4().hex[:10]}"
        con.execute(
            "insert into sessao (id, campanha_id, numero) values (?, ?, ?)", (sessao_id, campanha_id, numero)
        )
        evento = "sessão retomada" if retomada_de else "sessão aberta"
        registrar_evento(
            con,
            campanha_id,
            sessao_id,
            "C02",
            evento,
            {
                "numero": numero,
                "retomada_de": retomada_de,
                "em_combate": em_combate,
                "narracao_pendente": narracao_pendente,
            },
        )
        inst_novo = Instantaneo(
            ultimo_seq(con, campanha_id),
            inst.cena_atual,
            inst.relogio_minutos,
            inst.personagem_id,
            numero,
            inst.pontos_de_vida,
            inst.extras,
        )
        gravar_instantaneo(con, campanha_id, inst_novo)
        con.execute("commit")
    except Exception:
        con.execute("rollback")
        raise
    return SessaoAberta(
        sessao_id,
        numero,
        inst_novo,
        retomada_de,
        em_combate,
        combate if em_combate else None,
        narracao_pendente,
    )


def encerrar_sessao(
    con: sqlite3.Connection, campanha_id: str, sessao_id: str, pendencias: list[str] | None = None
) -> None:
    """C09: grava o fim com a cena atual e as pendências; o resumo (G02) é card posterior e fica pendente."""
    con.execute("begin")
    try:
        con.execute(
            "update sessao set encerrada_em = strftime('%Y-%m-%dT%H:%M:%fZ','now'), motivo_fim = 'encerrada' where id = ?",
            (sessao_id,),
        )
        inst = ultimo_instantaneo(con, campanha_id)
        registrar_evento(
            con,
            campanha_id,
            sessao_id,
            "C09",
            "sessão encerrada",
            {
                "cena_atual": inst.cena_atual if inst else None,
                "pendencias": [*(pendencias or []), "resumo da sessão"],
            },
        )
        if inst is not None:
            gravar_instantaneo(
                con,
                campanha_id,
                Instantaneo(
                    ultimo_seq(con, campanha_id),
                    inst.cena_atual,
                    inst.relogio_minutos,
                    inst.personagem_id,
                    inst.sessao_numero,
                    inst.pontos_de_vida,
                    inst.extras,
                ),
            )
        con.execute("commit")
    except Exception:
        con.execute("rollback")
        raise


def mudar_cena(
    con: sqlite3.Connection, campanha_id: str, sessao_id: str, cena_id: str, minutos: int = 0
) -> None:
    inst = ultimo_instantaneo(con, campanha_id)
    assert inst is not None
    registrar_evento(
        con,
        campanha_id,
        sessao_id,
        "C07",
        "cena atual",
        {"cena_id": cena_id, "relogio_minutos": inst.relogio_minutos + minutos},
    )
    gravar_instantaneo(
        con,
        campanha_id,
        Instantaneo(
            ultimo_seq(con, campanha_id),
            cena_id,
            inst.relogio_minutos + minutos,
            inst.personagem_id,
            inst.sessao_numero,
            inst.pontos_de_vida,
            inst.extras,
        ),
    )
