"""Rolagem de dados determinística (caso de uso E01, regra RN-06).

Todo número aleatório do produto sai daqui. A rolagem de número N numa campanha é sempre
a mesma, porque o gerador é inicializado com a semente da campanha e o contador da
rolagem: não depende da ordem nem do histórico, o que torna qualquer rolagem reproduzível
isoladamente (caso de uso E06).

Sem banco, sem rede, sem relógio: só entrada e saída.
"""

from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass, field
from typing import Literal

Modo = Literal["normal", "vantagem", "desvantagem"]
MODOS: tuple[Modo, ...] = ("normal", "vantagem", "desvantagem")
FACES_PERMITIDAS = (4, 6, 8, 10, 12, 20, 100)
QUANTIDADE_MAXIMA = 100

_EXPRESSAO = re.compile(r"^\s*(?P<n>\d*)d(?P<m>\d+)\s*(?:(?P<sinal>[+-])\s*(?P<k>\d+))?\s*$", re.IGNORECASE)


class ExpressaoInvalidaError(ValueError):
    """Expressão de dados fora do formato NdM, NdM+K ou NdM-K."""


class ModoInvalidoError(ValueError):
    """Vantagem e desvantagem só existem para um único d20."""


@dataclass(frozen=True)
class Expressao:
    quantidade: int
    faces: int
    modificador: int = 0

    @classmethod
    def analisar(cls, texto: str) -> Expressao:
        m = _EXPRESSAO.match(texto)
        if not m:
            raise ExpressaoInvalidaError(f"expressão inválida: {texto!r}; use NdM, NdM+K ou NdM-K")
        quantidade = int(m.group("n") or 1)
        faces = int(m.group("m"))
        if faces not in FACES_PERMITIDAS:
            raise ExpressaoInvalidaError(f"dado d{faces} não existe; faces permitidas: {FACES_PERMITIDAS}")
        if not 1 <= quantidade <= QUANTIDADE_MAXIMA:
            raise ExpressaoInvalidaError(f"quantidade de dados fora de 1 a {QUANTIDADE_MAXIMA}: {quantidade}")
        k = int(m.group("k") or 0)
        modificador = -k if m.group("sinal") == "-" else k
        return cls(quantidade, faces, modificador)

    def __str__(self) -> str:
        base = f"{self.quantidade}d{self.faces}"
        if self.modificador > 0:
            return f"{base}+{self.modificador}"
        if self.modificador < 0:
            return f"{base}{self.modificador}"
        return base


@dataclass(frozen=True)
class Rolagem:
    semente: str
    contador: int
    expressao: Expressao
    modo: Modo
    dados: tuple[int, ...]
    descartados: tuple[int, ...]
    modificadores: dict[str, int] = field(default_factory=dict)

    @property
    def soma_dos_dados(self) -> int:
        return sum(self.dados)

    @property
    def total(self) -> int:
        return self.soma_dos_dados + self.expressao.modificador + sum(self.modificadores.values())

    def composicao(self) -> str:
        """Texto que o jogador vê: d20 (14) + 3 = 17."""
        partes = [f"d{self.expressao.faces} ({', '.join(map(str, self.dados))})"]
        if self.descartados:
            partes[0] += f" [descartado {', '.join(map(str, self.descartados))}]"
        if self.expressao.modificador:
            partes.append(f"{self.expressao.modificador:+d}")
        for nome, valor in self.modificadores.items():
            partes.append(f"{valor:+d} {nome}")
        return " ".join(partes).replace(" +", " + ").replace(" -", " - ") + f" = {self.total}"


def _gerador(semente: str, contador: int) -> random.Random:
    resumo = hashlib.sha256(f"{semente}:{contador}".encode()).digest()
    return random.Random(int.from_bytes(resumo[:8], "big"))


def rolar(
    semente: str,
    contador: int,
    expressao: Expressao | str,
    modo: Modo = "normal",
    modificadores: dict[str, int] | None = None,
) -> Rolagem:
    """Rola a expressão na posição `contador` do gerador da campanha `semente`."""
    exp = Expressao.analisar(expressao) if isinstance(expressao, str) else expressao
    if modo not in MODOS:
        raise ModoInvalidoError(f"modo desconhecido: {modo!r}")
    if modo != "normal" and (exp.quantidade, exp.faces) != (1, 20):
        raise ModoInvalidoError("vantagem e desvantagem só valem para 1d20")
    if contador < 1:
        raise ValueError("contador começa em 1")
    gerador = _gerador(semente, contador)
    if modo == "normal":
        dados = tuple(gerador.randint(1, exp.faces) for _ in range(exp.quantidade))
        descartados: tuple[int, ...] = ()
    else:
        a, b = gerador.randint(1, 20), gerador.randint(1, 20)
        escolhido = max(a, b) if modo == "vantagem" else min(a, b)
        dados, descartados = (escolhido,), (a if escolhido == b else b,)
    return Rolagem(semente, contador, exp, modo, dados, descartados, dict(modificadores or {}))
