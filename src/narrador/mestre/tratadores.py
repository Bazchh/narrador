"""Os tratadores das ferramentas já cobertas pelos cards anteriores (N-04, N-05, N-06).

Cada card seguinte acrescenta os seus. `narrar` entra aqui só com o contrato; a
verificação de segredo e fato (G03) é o card N-10.
"""

from __future__ import annotations

from typing import Any

from narrador.campanha import personagens
from narrador.mestre.protocolo import (
    ConsultarCena,
    ConsultarFicha,
    ConsultarSrd,
    Contexto,
    ErroDeFerramentaError,
    Estrita,
    Narrar,
    Tratador,
)
from narrador.modulo import canonico
from narrador.srd import catalogo


def consultar_cena(entrada: Estrita, ctx: Contexto) -> dict[str, Any]:
    assert isinstance(entrada, ConsultarCena)
    modulo: canonico.ModuloCanonico = ctx.extras["modulo"]
    cena_atual: str | None = ctx.extras.get("cena_atual")
    cena_id = entrada.cena_id or cena_atual
    if cena_id is None:
        raise ErroDeFerramentaError("entrada_invalida", "sem cena atual; informe cena_id")
    try:
        recorte = canonico.recortar(
            modulo,
            cena_id,
            fatos_por_item=ctx.extras.get("fatos_por_item"),
            segredos_descobertos=ctx.extras.get("segredos_descobertos", ()),
            cena_atual=cena_atual,
        )
    except canonico.CenaInexistenteError as ex:
        raise ErroDeFerramentaError(
            "identificador_inexistente",
            str(ex),
            {"vizinhas": [{"id": v.id, "nome": v.nome} for v in ex.vizinhas]},
        ) from ex
    return {
        **recorte.narravel(),
        "nao_narrar": [
            {
                "id": s.item.id,
                "marca": s.marca,
                "condicao_descoberta": s.condicao_descoberta,
                "ligado_a_cena": s.ligado_a_cena,
            }
            for s in recorte.segredos
        ],
    }


def consultar_ficha(entrada: Estrita, ctx: Contexto) -> dict[str, Any]:
    assert isinstance(entrada, ConsultarFicha)
    personagem_id: str | None = ctx.extras.get("personagem_id")
    if personagem_id is None:
        raise ErroDeFerramentaError("identificador_inexistente", "a campanha não tem personagem vinculado")
    gravada, d = personagens.consultar(ctx.con, ctx.campanha_id, personagem_id)
    ficha = gravada.ficha
    tudo = {
        "nome": ficha.nome,
        "especie": d.especie.nome_pt,
        "classe": d.classe.nome_pt,
        "nivel": ficha.nivel,
        "vida": {"maximo": d.pontos_de_vida_maximos.total, "composicao": d.pontos_de_vida_maximos.partes},
        "classe_armadura": {"total": d.classe_armadura.total, "composicao": d.classe_armadura.partes},
        "iniciativa": d.iniciativa.total,
        "velocidade_pes": d.velocidade_pes,
        "salvaguardas": {k: v.total for k, v in d.salvaguardas.items()},
        "pericias": {k.rsplit(":", 1)[1]: v.total for k, v in d.pericias.items()},
        "percepcao_passiva": d.percepcao_passiva.total,
        "ataques": [
            {
                "arma": a.arma.nome_pt,
                "bonus": a.bonus_ataque.total,
                "dano": f"{a.dano_dados}+{a.bonus_dano.total}",
                "tipo": a.dano_tipo,
            }
            for a in d.ataques
        ],
        "inventario": {
            "armadura": d.armadura.nome_pt if d.armadura else None,
            "escudo": ficha.escudo,
            "armas": [a.arma.nome_pt for a in d.ataques],
        },
    }
    secoes = {
        "tudo": tudo,
        "vida": {"vida": tudo["vida"]},
        "ataques": {"ataques": tudo["ataques"]},
        "pericias": {"pericias": tudo["pericias"]},
        "salvaguardas": {"salvaguardas": tudo["salvaguardas"]},
        "inventario": {"inventario": tudo["inventario"]},
        "combate": {
            "classe_armadura": tudo["classe_armadura"],
            "iniciativa": tudo["iniciativa"],
            "ataques": tudo["ataques"],
        },
    }
    return secoes[entrada.secao]


def consultar_srd(entrada: Estrita, ctx: Contexto) -> dict[str, Any]:
    assert isinstance(entrada, ConsultarSrd)
    try:
        r = catalogo.buscar(entrada.tipo, entrada.nome)
    except catalogo.ForaDoSrdError as ex:
        raise ErroDeFerramentaError(
            "fora_do_srd",
            str(ex),
            {"parecidos": [{"id": c.id, "nome_pt": c.nome_pt} for c in ex.candidatos]},
        ) from ex
    return {
        "exato": r.exato,
        **r.registro.model_dump(),
        "atribuicao": "SRD 5.2.1, Wizards of the Coast LLC, CC-BY-4.0",
    }


def narrar(entrada: Estrita, ctx: Contexto) -> dict[str, Any]:
    """Contrato da narração. A verificação de segredo e fato entra no card N-10."""
    assert isinstance(entrada, Narrar)
    if not entrada.texto.strip():
        raise ErroDeFerramentaError("entrada_invalida", "narração vazia")
    return {
        "aprovado": True,
        "texto": entrada.texto,
        "fatos": [f.model_dump() for f in entrada.fatos],
        "desvios": [d.model_dump() for d in entrada.desvios],
    }


TRATADORES: dict[str, Tratador] = {
    "consultar_cena": consultar_cena,
    "consultar_ficha": consultar_ficha,
    "consultar_srd": consultar_srd,
    "narrar": narrar,
}
