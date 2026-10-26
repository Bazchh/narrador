"""O módulo canônico publicado e o recorte da cena (caso de uso A05, regras RN-01, RN-05).

O recorte é o que o mestre recebe: a cena, as ligações, quem está presente, os itens, os
ganchos e, separados e marcados "não narrar", os segredos ainda não descobertos. O estado
da campanha viva entra por cima do canônico como fatos ligados a cada item.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TipoItem = Literal["cena", "local", "personagem", "criatura", "item", "gancho", "segredo"]
TipoLigacao = Literal["leva_a", "contem", "sabe_de", "possui", "gatilho"]
NAO_NARRAR = "não narrar"


class ModuloNaoPublicadoError(LookupError):
    """A versão pedida não existe ou ainda é rascunho."""


class CenaInexistenteError(LookupError):
    """A cena pedida não existe nesta versão; `vizinhas` traz as candidatas."""

    def __init__(self, cena_id: str, vizinhas: list[ItemCanonico]):
        self.cena_id, self.vizinhas = cena_id, vizinhas
        nomes = ", ".join(f"{v.id} ({v.nome})" for v in vizinhas)
        super().__init__(f"cena inexistente: {cena_id!r}; candidatas: {nomes}")


class ItemCanonico(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    tipo: TipoItem
    nome: str
    dados: dict[str, Any] = Field(default_factory=dict)
    pagina_origem: int | None = None
    incerto: bool = False
    segredo: bool = False
    condicao_descoberta: str | None = None


class Ligacao(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    de: str
    para: str
    tipo: TipoLigacao
    caminho_critico: bool = False


class Mapeamento(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    item_id: str
    srd_id: str | None = None
    srd_versao: str
    ficha_propria: dict[str, Any] | None = None
    pendente: bool = False
    fora_da_escala: bool = False


class ModuloCanonico(BaseModel):
    """Uma versão publicada: imutável por construção e por gatilho no banco."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    aventura_id: str
    versao: int
    origem: str
    itens: dict[str, ItemCanonico]
    ligacoes: list[Ligacao]
    mapeamentos: dict[str, Mapeamento]

    def cenas(self) -> list[ItemCanonico]:
        return [i for i in self.itens.values() if i.tipo == "cena"]

    def saidas(self, item_id: str) -> list[Ligacao]:
        return [li for li in self.ligacoes if li.de == item_id]

    def entradas(self, item_id: str) -> list[Ligacao]:
        return [li for li in self.ligacoes if li.para == item_id]

    def segredos(self) -> list[ItemCanonico]:
        return [i for i in self.itens.values() if i.segredo]

    def caminho_critico(self, inicio: str) -> list[str]:
        """Percorre as ligações marcadas como caminho crítico a partir de uma cena."""
        caminho, atual = [inicio], inicio
        while True:
            proximas = [li.para for li in self.saidas(atual) if li.caminho_critico]
            if not proximas or proximas[0] in caminho:
                return caminho
            atual = proximas[0]
            caminho.append(atual)


def carregar(con: sqlite3.Connection, aventura_id: str, versao: int) -> ModuloCanonico:
    """Lê uma versão PUBLICADA do módulo; rascunho ou versão inexistente é erro."""
    linha = con.execute(
        "select origem, publicada_em from modulo_versao where aventura_id = ? and versao = ?",
        (aventura_id, versao),
    ).fetchone()
    if linha is None or linha[1] is None:
        raise ModuloNaoPublicadoError(f"{aventura_id} v{versao}")
    itens = {}
    for id_, tipo, nome, dados, pagina, incerto, segredo, condicao in con.execute(
        "select id, tipo, nome, dados, pagina_origem, incerto, segredo, condicao_descoberta"
        " from item_canonico where aventura_id = ? and versao = ?",
        (aventura_id, versao),
    ):
        itens[id_] = ItemCanonico(
            id=id_,
            tipo=tipo,
            nome=nome,
            dados=json.loads(dados),
            pagina_origem=pagina,
            incerto=bool(incerto),
            segredo=bool(segredo),
            condicao_descoberta=condicao,
        )
    ligacoes = [
        Ligacao(de=de, para=para, tipo=tipo, caminho_critico=bool(cc))
        for de, para, tipo, cc in con.execute(
            "select de_item, para_item, tipo, caminho_critico from ligacao where aventura_id = ? and versao = ?",
            (aventura_id, versao),
        )
    ]
    mapeamentos = {}
    for item_id, srd_id, srd_versao, ficha, pendente, fora in con.execute(
        "select item_id, srd_id, srd_versao, ficha_propria, pendente, fora_da_escala"
        " from mapeamento_srd where aventura_id = ? and versao = ?",
        (aventura_id, versao),
    ):
        mapeamentos[item_id] = Mapeamento(
            item_id=item_id,
            srd_id=srd_id,
            srd_versao=srd_versao,
            ficha_propria=json.loads(ficha) if ficha else None,
            pendente=bool(pendente),
            fora_da_escala=bool(fora),
        )
    return ModuloCanonico(
        aventura_id=aventura_id,
        versao=versao,
        origem=linha[0],
        itens=itens,
        ligacoes=ligacoes,
        mapeamentos=mapeamentos,
    )


# ---------------------------------------------------------------- recorte


class Presenca(BaseModel):
    """Um personagem, criatura ou item presente na cena, com o mapeamento para o SRD se houver."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    item: ItemCanonico
    mapeamento: Mapeamento | None = None
    fatos: list[str] = Field(default_factory=list)


class SegredoMarcado(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    item: ItemCanonico
    marca: str = NAO_NARRAR
    condicao_descoberta: str
    ligado_a_cena: bool


class Recorte(BaseModel):
    """O que o mestre recebe sobre uma cena. Segredos vêm separados, nunca no corpo."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    cena: ItemCanonico
    fatos_da_cena: list[str]
    ligacoes_saida: list[Ligacao]
    ligacoes_entrada: list[Ligacao]
    no_caminho_critico: bool
    presentes: list[Presenca]
    itens: list[Presenca]
    ganchos: list[ItemCanonico]
    segredos: list[SegredoMarcado]
    vizinhas: list[ItemCanonico]

    def narravel(self) -> dict[str, Any]:
        """A parte que pode ir ao mestre como contexto; os segredos ficam fora deste dicionário."""
        return {
            "cena": {"id": self.cena.id, "nome": self.cena.nome, **self.cena.dados},
            "fatos": self.fatos_da_cena,
            "presentes": [
                {"id": p.item.id, "nome": p.item.nome, **p.item.dados, "fatos": p.fatos}
                for p in self.presentes
            ],
            "itens": [
                {"id": p.item.id, "nome": p.item.nome, **p.item.dados, "fatos": p.fatos} for p in self.itens
            ],
            "ganchos": [{"id": g.id, "nome": g.nome, **g.dados} for g in self.ganchos],
            "saidas": [{"para": li.para, "tipo": li.tipo} for li in self.ligacoes_saida],
        }


def _presentes(modulo: ModuloCanonico, cena: ItemCanonico) -> list[ItemCanonico]:
    ids: list[str] = []
    for li in modulo.saidas(cena.id):
        if (
            li.tipo == "contem"
            and li.para in modulo.itens
            and modulo.itens[li.para].tipo in ("personagem", "criatura")
        ):
            ids.append(li.para)
    for ref in cena.dados.get("encontro", []):
        if ref in modulo.itens and ref not in ids:
            ids.append(ref)
    return [modulo.itens[i] for i in ids]


def recortar(
    modulo: ModuloCanonico,
    cena_id: str,
    fatos_por_item: Mapping[str, Iterable[str]] | None = None,
    segredos_descobertos: Iterable[str] = (),
    cena_atual: str | None = None,
) -> Recorte:
    """Monta o recorte da cena `cena_id` com os fatos da campanha viva por cima do canônico.

    `fatos_por_item` liga identificadores canônicos aos fatos já estabelecidos (F01);
    `segredos_descobertos` traz os segredos que o personagem já conhece (F04).
    """
    fatos = {k: list(v) for k, v in (fatos_por_item or {}).items()}
    descobertos = set(segredos_descobertos)
    cena = modulo.itens.get(cena_id)
    if cena is None or cena.tipo != "cena":
        if cena_atual and cena_atual in modulo.itens:
            vizinhas = [
                modulo.itens[li.para]
                for li in modulo.saidas(cena_atual)
                if modulo.itens[li.para].tipo == "cena"
            ]
            vizinhas += [
                modulo.itens[li.de]
                for li in modulo.entradas(cena_atual)
                if modulo.itens[li.de].tipo == "cena"
            ]
        else:
            vizinhas = modulo.cenas()
        raise CenaInexistenteError(cena_id, vizinhas)
    presentes = [
        Presenca(item=i, mapeamento=modulo.mapeamentos.get(i.id), fatos=fatos.get(i.id, []))
        for i in _presentes(modulo, cena)
    ]
    itens = [
        Presenca(
            item=modulo.itens[li.para],
            mapeamento=modulo.mapeamentos.get(li.para),
            fatos=fatos.get(li.para, []),
        )
        for li in modulo.saidas(cena.id)
        if li.tipo == "contem" and modulo.itens[li.para].tipo == "item"
    ]
    ganchos = [
        modulo.itens[li.para] for li in modulo.saidas(cena.id) if modulo.itens[li.para].tipo == "gancho"
    ]
    ganchos += [
        g
        for g in modulo.itens.values()
        if g.tipo == "gancho" and g not in ganchos and cena.id in g.dados.get("cenas", [])
    ]
    ligados_a_cena = {li.para for li in modulo.saidas(cena.id)} | {
        li.para for p in presentes for li in modulo.saidas(p.item.id) if li.tipo == "sabe_de"
    }
    segredos = [
        SegredoMarcado(
            item=s, condicao_descoberta=s.condicao_descoberta or "", ligado_a_cena=s.id in ligados_a_cena
        )
        for s in modulo.segredos()
        if s.id not in descobertos
    ]
    saidas = modulo.saidas(cena.id)
    return Recorte(
        cena=cena,
        fatos_da_cena=fatos.get(cena.id, []),
        ligacoes_saida=saidas,
        ligacoes_entrada=modulo.entradas(cena.id),
        no_caminho_critico=any(li.caminho_critico for li in saidas)
        or any(li.caminho_critico for li in modulo.entradas(cena.id)),
        presentes=presentes,
        itens=itens,
        ganchos=ganchos,
        segredos=segredos,
        vizinhas=[modulo.itens[li.para] for li in saidas if modulo.itens[li.para].tipo == "cena"],
    )
