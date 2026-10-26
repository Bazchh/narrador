"""O formato estruturado do SRD 5.2 (Blueprint, capítulo 2, pacote srd; card N-04).

Cada registro tem identificador estável, nome em inglês (como no documento), nome em
português e a página do PDF oficial de onde veio. O que não está aqui não está no SRD:
o motor nunca inventa dado de regra (regra RN-08).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

VERSAO_SRD = "5.2.1"

Atributo = Literal["str", "dex", "con", "int", "wis", "cha"]
ATRIBUTOS: tuple[Atributo, ...] = ("str", "dex", "con", "int", "wis", "cha")
ATRIBUTO_PT: dict[Atributo, str] = {
    "str": "Força",
    "dex": "Destreza",
    "con": "Constituição",
    "int": "Inteligência",
    "wis": "Sabedoria",
    "cha": "Carisma",
}


class Registro(BaseModel):
    """Base de todo item do SRD: identificador, nomes e origem no PDF."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^srd:[a-z-]+:[a-z0-9-]+$")
    nome: str
    nome_pt: str
    pagina: int = Field(ge=1)


class Traco(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    nome: str
    descricao: str


class Ataque(BaseModel):
    """Um ataque de criatura, já separado em números para o motor (caso de uso D04)."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    nome: str
    tipo: Literal["corpo_a_corpo", "distancia"]
    bonus: int
    alcance_pes: int
    dano_dados: str
    dano_tipo: str
    descricao: str


class Criatura(Registro):
    tamanho: str
    tipo: str
    tendencia: str
    classe_armadura: int
    pontos_de_vida: int
    dados_de_vida: str
    velocidade_pes: int
    velocidades_extras: dict[str, int] = Field(default_factory=dict)
    atributos: dict[Atributo, int]
    bonus_iniciativa: int
    percepcao_passiva: int
    nivel_de_desafio: str
    pontos_de_experiencia: int
    bonus_proficiencia: int
    tracos: list[Traco] = Field(default_factory=list)
    ataques: list[Ataque] = Field(default_factory=list)
    acoes_texto: list[Traco] = Field(default_factory=list)


class Arma(Registro):
    simples: bool
    dano_dados: str
    dano_tipo: str
    propriedades: list[str] = Field(default_factory=list)
    maestria: str | None = None
    alcance_pes: int = 0
    alcance_longo_pes: int = 0


class Armadura(Registro):
    categoria: Literal["leve", "media", "pesada", "escudo"]
    classe_armadura_base: int
    soma_destreza: bool
    teto_destreza: int | None = None
    forca_minima: int | None = None
    desvantagem_furtividade: bool = False


class Pericia(Registro):
    atributo: Atributo
    descricao: str


class Condicao(Registro):
    descricao: str


class Especie(Registro):
    tamanho: str
    velocidade_pes: int
    tracos: list[Traco] = Field(default_factory=list)


class Classe(Registro):
    dado_de_vida: str
    salvaguardas: list[Atributo]
    atributos_primarios: list[Atributo]
    tracos_basicos: str
    tracos_nivel_1: list[Traco] = Field(default_factory=list)


class Srd(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    versao: str
    pdf_sha256: str
    paginas_pdf: int
    criaturas: list[Criatura] = Field(default_factory=list)
    armas: list[Arma] = Field(default_factory=list)
    armaduras: list[Armadura] = Field(default_factory=list)
    pericias: list[Pericia] = Field(default_factory=list)
    condicoes: list[Condicao] = Field(default_factory=list)
    especies: list[Especie] = Field(default_factory=list)
    classes: list[Classe] = Field(default_factory=list)
