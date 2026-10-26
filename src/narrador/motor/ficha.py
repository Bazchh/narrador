"""A ficha do personagem e os valores derivados (casos de uso B02, B03, E05).

A ficha guarda só escolhas e estado; tudo que é conta (modificadores, proficiência, pontos
de vida, classe de armadura, iniciativa, salvaguardas, ataques) é calculado pelo motor a
partir do SRD, com a composição de cada número gravada para o jogador ver de onde veio.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from narrador.srd import catalogo
from narrador.srd.modelo import ATRIBUTO_PT, ATRIBUTOS, Arma, Armadura, Atributo, Classe, Especie, Srd

Origem = Literal["criado", "pre_gerado"]


class FichaInvalidaError(ValueError):
    """A ficha contradiz o SRD ou a si mesma."""


class Ficha(BaseModel):
    """Escolhas e estado permanente do personagem. Valores derivados não moram aqui."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    nome: str
    origem: Origem
    especie_id: str
    classe_id: str
    nivel: int = Field(ge=1, le=20)
    atributos: dict[Atributo, int]
    metodo_atributos: Literal["padrao", "compra", "rolados", "informados"]
    pericias_proficientes: list[str] = Field(default_factory=list)
    armadura_id: str | None = None
    escudo: bool = False
    armas_ids: list[str] = Field(default_factory=list)
    pontos_de_vida_maximos: int = Field(ge=1)
    aparencia: str = ""
    personalidade: str = ""
    srd_versao: str


class Valor(BaseModel):
    """Um número derivado e a composição que o explica: CA 18 = 16 da armadura + 2 do escudo."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    total: int
    partes: dict[str, int]

    def explicar(self) -> str:
        soma = " + ".join(f"{v} ({k})" if v >= 0 else f"- {abs(v)} ({k})" for k, v in self.partes.items())
        return f"{self.total} = {soma}".replace("+ -", "- ")


class AtaqueDerivado(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    arma: Arma
    atributo: Atributo
    bonus_ataque: Valor
    dano_dados: str
    bonus_dano: Valor
    dano_tipo: str


class Derivados(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    especie: Especie
    classe: Classe
    armadura: Armadura | None
    modificadores: dict[Atributo, int]
    bonus_proficiencia: int
    pontos_de_vida_maximos: Valor
    classe_armadura: Valor
    iniciativa: Valor
    velocidade_pes: int
    salvaguardas: dict[Atributo, Valor]
    pericias: dict[str, Valor]
    percepcao_passiva: Valor
    ataques: list[AtaqueDerivado]


def modificador(valor: int) -> int:
    return (valor - 10) // 2


def bonus_proficiencia(nivel: int) -> int:
    return 2 + (nivel - 1) // 4


def dado_de_vida_maximo(dado: str) -> int:
    return int(dado.lstrip("dD"))


def validar(ficha: Ficha, srd: Srd | None = None) -> None:
    """Confere a ficha contra o SRD: tudo que ela cita existe e os números cabem nas regras."""
    srd = srd or catalogo.carregar()
    if set(ficha.atributos) != set(ATRIBUTOS):
        raise FichaInvalidaError("a ficha precisa dos seis atributos")
    if any(not 1 <= v <= 30 for v in ficha.atributos.values()):
        raise FichaInvalidaError("atributo fora de 1 a 30")
    especie, classe = catalogo.especie(ficha.especie_id, srd), catalogo.classe(ficha.classe_id, srd)
    for p in ficha.pericias_proficientes:
        catalogo.pericia(p, srd)
    if len(set(ficha.pericias_proficientes)) != len(ficha.pericias_proficientes):
        raise FichaInvalidaError("perícia repetida")
    if ficha.armadura_id is not None:
        armadura = catalogo.armadura(ficha.armadura_id, srd)
        if armadura.categoria == "escudo":
            raise FichaInvalidaError("escudo não é armadura; use o campo escudo")
    for a in ficha.armas_ids:
        catalogo.arma(a, srd)
    teto = dado_de_vida_maximo(classe.dado_de_vida) + modificador(ficha.atributos["con"])
    if ficha.nivel == 1 and ficha.pontos_de_vida_maximos > max(1, teto):
        raise FichaInvalidaError(f"pontos de vida acima do máximo do nível 1 ({teto})")
    _ = especie


def calcular(ficha: Ficha, srd: Srd | None = None) -> Derivados:
    """Calcula todos os derivados pelas fórmulas do SRD, com a composição de cada um."""
    srd = srd or catalogo.carregar()
    validar(ficha, srd)
    especie, classe = catalogo.especie(ficha.especie_id, srd), catalogo.classe(ficha.classe_id, srd)
    mods = {a: modificador(ficha.atributos[a]) for a in ATRIBUTOS}
    prof = bonus_proficiencia(ficha.nivel)
    armadura = catalogo.armadura(ficha.armadura_id, srd) if ficha.armadura_id else None

    partes_ca: dict[str, int] = {}
    if armadura is None:
        partes_ca["base"] = 10
        partes_ca[ATRIBUTO_PT["dex"]] = mods["dex"]
    else:
        partes_ca[armadura.nome_pt] = armadura.classe_armadura_base
        if armadura.soma_destreza:
            dex = mods["dex"] if armadura.teto_destreza is None else min(mods["dex"], armadura.teto_destreza)
            partes_ca[ATRIBUTO_PT["dex"]] = dex
    if ficha.escudo:
        partes_ca["escudo"] = catalogo.armadura("Shield", srd).classe_armadura_base
    ca = Valor(total=sum(partes_ca.values()), partes=partes_ca)

    pv = Valor(
        total=ficha.pontos_de_vida_maximos, partes={"registrado na ficha": ficha.pontos_de_vida_maximos}
    )
    iniciativa = Valor(total=mods["dex"], partes={ATRIBUTO_PT["dex"]: mods["dex"]})

    salvaguardas = {}
    for a in ATRIBUTOS:
        partes = {ATRIBUTO_PT[a]: mods[a]}
        if a in classe.salvaguardas:
            partes["proficiência"] = prof
        salvaguardas[a] = Valor(total=sum(partes.values()), partes=partes)

    pericias = {}
    for p in srd.pericias:
        partes = {ATRIBUTO_PT[p.atributo]: mods[p.atributo]}
        if (
            p.id in ficha.pericias_proficientes
            or p.nome in ficha.pericias_proficientes
            or p.nome_pt in ficha.pericias_proficientes
        ):
            partes["proficiência"] = prof
        pericias[p.id] = Valor(total=sum(partes.values()), partes=partes)
    percepcao = pericias["srd:pericia:perception"]
    passiva = Valor(total=10 + percepcao.total, partes={"base": 10, **percepcao.partes})

    ataques = []
    for arma_id in ficha.armas_ids:
        arma = catalogo.arma(arma_id, srd)
        a_distancia = arma.alcance_pes > 0 and "Thrown" not in arma.propriedades
        if a_distancia:
            atributo: Atributo = "dex"
        elif "Finesse" in arma.propriedades:
            atributo = max(("str", "dex"), key=lambda x: mods[x])
        else:
            atributo = "str"
        partes_at = {ATRIBUTO_PT[atributo]: mods[atributo], "proficiência": prof}
        partes_dano = {ATRIBUTO_PT[atributo]: mods[atributo]}
        ataques.append(
            AtaqueDerivado(
                arma=arma,
                atributo=atributo,
                bonus_ataque=Valor(total=sum(partes_at.values()), partes=partes_at),
                dano_dados=arma.dano_dados,
                bonus_dano=Valor(total=sum(partes_dano.values()), partes=partes_dano),
                dano_tipo=arma.dano_tipo,
            )
        )

    return Derivados(
        especie=especie,
        classe=classe,
        armadura=armadura,
        modificadores=mods,
        bonus_proficiencia=prof,
        pontos_de_vida_maximos=pv,
        classe_armadura=ca,
        iniciativa=iniciativa,
        velocidade_pes=especie.velocidade_pes,
        salvaguardas=salvaguardas,
        pericias=pericias,
        percepcao_passiva=passiva,
        ataques=ataques,
    )


# ---------------------------------------------------------------- pré-gerados (só conteúdo do SRD)


def pre_gerados(srd: Srd | None = None) -> list[Ficha]:
    """Os personagens prontos do produto. Só conteúdo do SRD; revalidados contra a versão carregada."""
    srd = srd or catalogo.carregar()
    con = 14
    guerreira = Ficha(
        nome="Brenna",
        origem="pre_gerado",
        especie_id="srd:especie:human",
        classe_id="srd:classe:fighter",
        nivel=1,
        atributos={"str": 16, "dex": 12, "con": con, "int": 10, "wis": 13, "cha": 8},
        metodo_atributos="padrao",
        pericias_proficientes=["srd:pericia:athletics", "srd:pericia:perception"],
        armadura_id="srd:armadura:chain-mail",
        escudo=True,
        armas_ids=["srd:arma:longsword", "srd:arma:javelin"],
        pontos_de_vida_maximos=10 + modificador(con),
        aparencia="Alta, cicatriz no queixo, cota de malha gasta e um escudo pintado com um cavalo manco.",
        personalidade="Direta, protege quem está ao lado, desconfia de quem fala demais.",
        srd_versao=srd.versao,
    )
    validar(guerreira, srd)
    return [guerreira]
