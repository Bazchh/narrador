"""Validação do veredito e consistência entre vereditos (casos de uso C05, E02, G04; regra RN-11).

O mestre propõe: de cara, impossível, ou teste com perícia e dificuldade. O motor confere
que a perícia existe, que a dificuldade está na escala do SRD e que o veredito é coerente
com os anteriores para a mesma situação. Nada aqui rola dado nem grava: é regra pura.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Literal

from narrador.srd import catalogo
from narrador.srd.catalogo import normalizar
from narrador.srd.modelo import ATRIBUTO_PT, ATRIBUTOS, Atributo, Srd

TipoVeredito = Literal["de_cara", "impossivel", "teste"]
Modo = Literal["normal", "vantagem", "desvantagem"]

DIFICULDADE_MINIMA, DIFICULDADE_MAXIMA = 5, 30
ESCALA = {  # chaves em texto: o envelope de erro vai ao diário como JSON
    "5": "muito fácil",
    "10": "fácil",
    "15": "médio",
    "20": "difícil",
    "25": "muito difícil",
    "30": "quase impossível",
}
FAIXA_COERENTE = 2  # diferença de dificuldade tolerada entre vereditos da mesma situação
SEMELHANCA_MINIMA = 0.8


class VereditoInvalidoError(ValueError):
    def __init__(
        self,
        codigo: Literal["entrada_invalida", "pericia_inexistente", "dificuldade_fora_da_escala"],
        mensagem: str,
        alternativa: dict[str, object] | None = None,
    ):
        self.codigo, self.mensagem, self.alternativa = codigo, mensagem, alternativa
        super().__init__(f"{codigo}: {mensagem}")


@dataclass(frozen=True)
class Teste:
    """Uma perícia (ou atributo puro) resolvida contra o SRD."""

    chave: str  # srd:pericia:athletics ou atributo:str
    nome_pt: str
    atributo: Atributo


@dataclass(frozen=True)
class VereditoValidado:
    tipo: TipoVeredito
    situacao: str
    teste: Teste | None = None
    dificuldade: int | None = None
    modo: Modo = "normal"


def resolver_teste(nome: str, srd: Srd | None = None) -> Teste:
    """Aceita perícia (Atletismo, athletics, srd:pericia:athletics) ou atributo (Força, str)."""
    srd = srd or catalogo.carregar()
    chave = normalizar(nome)
    for a in ATRIBUTOS:
        if chave in (a, normalizar(ATRIBUTO_PT[a]), f"atributo:{a}"):
            return Teste(f"atributo:{a}", ATRIBUTO_PT[a], a)
    try:
        p = catalogo.pericia(nome, srd)
    except catalogo.ForaDoSrdError as ex:
        raise VereditoInvalidoError(
            "pericia_inexistente",
            f"perícia desconhecida: {nome!r}",
            {"pericias": [x.nome_pt for x in srd.pericias], "atributos": list(ATRIBUTO_PT.values())},
        ) from ex
    return Teste(p.id, p.nome_pt, p.atributo)


def situacao_comparavel(tentativa: str) -> str:
    """Forma normalizada da tentativa para comparar vereditos entre sessões."""
    texto = normalizar(tentativa)
    texto = re.sub(
        r"\b(eu|tento|tentar|vou|quero|tentando|de|do|da|o|a|os|as|um|uma|no|na|pelo|pela)\b", " ", texto
    )
    return " ".join(texto.split())


def validar(
    tipo: TipoVeredito,
    tentativa: str,
    pericia: str | None = None,
    dificuldade: int | None = None,
    modo: Modo = "normal",
    srd: Srd | None = None,
) -> VereditoValidado:
    situacao = situacao_comparavel(tentativa)
    if not situacao:
        raise VereditoInvalidoError("entrada_invalida", "tentativa vazia")
    if tipo != "teste":
        if pericia is not None or dificuldade is not None:
            raise VereditoInvalidoError(
                "entrada_invalida", f"veredito '{tipo}' não leva perícia nem dificuldade"
            )
        return VereditoValidado(tipo, situacao)
    if pericia is None or dificuldade is None:
        raise VereditoInvalidoError("entrada_invalida", "teste exige perícia e dificuldade")
    if not DIFICULDADE_MINIMA <= dificuldade <= DIFICULDADE_MAXIMA:
        raise VereditoInvalidoError(
            "dificuldade_fora_da_escala",
            f"dificuldade {dificuldade} não existe no SRD; a escala vai de {DIFICULDADE_MINIMA} a {DIFICULDADE_MAXIMA}",
            {"escala": ESCALA},
        )
    return VereditoValidado("teste", situacao, resolver_teste(pericia, srd), dificuldade, modo)


@dataclass(frozen=True)
class VereditoAnterior:
    seq: int
    situacao: str
    tipo: TipoVeredito
    pericia: str | None
    dificuldade: int | None


@dataclass(frozen=True)
class Consistencia:
    anterior: VereditoAnterior | None
    semelhanca: float
    coerente: bool

    def motivo(self) -> str | None:
        if self.anterior is None or self.coerente:
            return None
        a = self.anterior
        if a.tipo != "teste":
            return f"antes foi '{a.tipo}' para a mesma situação (registro {a.seq})"
        return f"antes foi teste de {a.pericia} com dificuldade {a.dificuldade} (registro {a.seq})"


def comparar(novo: VereditoValidado, anteriores: list[VereditoAnterior]) -> Consistencia:
    """Procura o veredito anterior mais parecido e diz se o novo é coerente com ele."""
    melhor, melhor_semelhanca = None, 0.0
    for a in anteriores:
        s = difflib.SequenceMatcher(None, novo.situacao, a.situacao).ratio()
        if s > melhor_semelhanca:
            melhor, melhor_semelhanca = a, s
    if melhor is None or melhor_semelhanca < SEMELHANCA_MINIMA:
        return Consistencia(None, melhor_semelhanca, True)
    if novo.tipo != melhor.tipo:
        return Consistencia(melhor, melhor_semelhanca, False)
    if novo.tipo == "teste":
        assert novo.teste is not None and novo.dificuldade is not None
        mesma_pericia = melhor.pericia == novo.teste.chave
        mesma_faixa = (
            melhor.dificuldade is not None and abs(melhor.dificuldade - novo.dificuldade) <= FAIXA_COERENTE
        )
        return Consistencia(melhor, melhor_semelhanca, mesma_pericia and mesma_faixa)
    return Consistencia(melhor, melhor_semelhanca, True)
