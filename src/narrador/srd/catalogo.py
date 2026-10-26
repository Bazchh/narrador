"""O catálogo do SRD carregado do pacote, com busca por nome (caso de uso E03).

Busca por identificador, nome exato em inglês ou português (sem distinguir maiúsculas
nem acentos) e nome aproximado. O que não é encontrado volta como `ForaDoSrd`, nunca
como invenção.
"""

from __future__ import annotations

import difflib
import unicodedata
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Literal, TypeVar

from narrador.srd.modelo import Arma, Armadura, Classe, Condicao, Criatura, Especie, Pericia, Registro, Srd

Tipo = Literal["criatura", "arma", "armadura", "pericia", "condicao", "especie", "classe"]
TIPOS: tuple[Tipo, ...] = ("criatura", "arma", "armadura", "pericia", "condicao", "especie", "classe")
ARQUIVO_PADRAO = "esqueleto.json"

R = TypeVar("R", bound=Registro)


class ForaDoSrdError(LookupError):
    """O nome pedido não existe no SRD carregado; pode haver candidatos aproximados."""

    def __init__(self, tipo: Tipo, nome: str, candidatos: list[Registro]):
        self.tipo, self.nome, self.candidatos = tipo, nome, candidatos
        extra = f"; parecidos: {', '.join(c.nome_pt for c in candidatos)}" if candidatos else ""
        super().__init__(f"fora do SRD: {tipo} {nome!r}{extra}")


@dataclass(frozen=True)
class Resultado:
    registro: Registro
    exato: bool


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())


@cache
def carregar(arquivo: str = ARQUIVO_PADRAO) -> Srd:
    """Lê o catálogo embutido no pacote (gerado por ferramentas/carregar_srd.py)."""
    texto = (resources.files("narrador.srd") / "dados" / arquivo).read_text(encoding="utf-8")
    return Srd.model_validate_json(texto)


def _lista(srd: Srd, tipo: Tipo) -> list[Registro]:
    por_tipo: dict[Tipo, list[Registro]] = {
        "criatura": list(srd.criaturas),
        "arma": list(srd.armas),
        "armadura": list(srd.armaduras),
        "pericia": list(srd.pericias),
        "condicao": list(srd.condicoes),
        "especie": list(srd.especies),
        "classe": list(srd.classes),
    }
    return por_tipo[tipo]


def buscar(tipo: Tipo, nome: str, srd: Srd | None = None, limiar: float = 0.75) -> Resultado:
    """Identificador, nome exato (inglês ou português) ou aproximado; senão ForaDoSrdError."""
    srd = srd or carregar()
    itens = _lista(srd, tipo)
    chave = normalizar(nome)
    for r in itens:
        if r.id == nome or normalizar(r.nome) == chave or normalizar(r.nome_pt) == chave:
            return Resultado(r, exato=True)
    nomes: dict[str, Registro] = {}
    for r in itens:
        nomes.setdefault(normalizar(r.nome), r)
        nomes.setdefault(normalizar(r.nome_pt), r)
    parecidos = difflib.get_close_matches(chave, list(nomes), n=5, cutoff=limiar)
    candidatos: list[Registro] = []
    for p in parecidos:
        if nomes[p] not in candidatos:
            candidatos.append(nomes[p])
    if len(candidatos) == 1:
        return Resultado(candidatos[0], exato=False)
    raise ForaDoSrdError(tipo, nome, candidatos)


def criatura(nome: str, srd: Srd | None = None) -> Criatura:
    r = buscar("criatura", nome, srd).registro
    assert isinstance(r, Criatura)
    return r


def arma(nome: str, srd: Srd | None = None) -> Arma:
    r = buscar("arma", nome, srd).registro
    assert isinstance(r, Arma)
    return r


def armadura(nome: str, srd: Srd | None = None) -> Armadura:
    r = buscar("armadura", nome, srd).registro
    assert isinstance(r, Armadura)
    return r


def pericia(nome: str, srd: Srd | None = None) -> Pericia:
    r = buscar("pericia", nome, srd).registro
    assert isinstance(r, Pericia)
    return r


def condicao(nome: str, srd: Srd | None = None) -> Condicao:
    r = buscar("condicao", nome, srd).registro
    assert isinstance(r, Condicao)
    return r


def especie(nome: str, srd: Srd | None = None) -> Especie:
    r = buscar("especie", nome, srd).registro
    assert isinstance(r, Especie)
    return r


def classe(nome: str, srd: Srd | None = None) -> Classe:
    r = buscar("classe", nome, srd).registro
    assert isinstance(r, Classe)
    return r


def todos(srd: Srd | None = None) -> list[Registro]:
    srd = srd or carregar()
    saida: list[Registro] = []
    for t in TIPOS:
        saida.extend(_lista(srd, t))
    return saida
