"""Tratadores do veredito, da pergunta e do esclarecimento (card N-08; casos C04, C05, E02, E04, G04)."""

from __future__ import annotations

from typing import Any

from narrador.campanha import personagens, rolagens, vereditos
from narrador.mestre.protocolo import (
    Contexto,
    DarVeredito,
    ErroDeFerramentaError,
    Estrita,
    PerguntarAoJogador,
    ResponderPergunta,
    Tratador,
    VereditoProposto,
)
from narrador.motor import veredito as motor_veredito
from narrador.srd.modelo import ATRIBUTO_PT


def _validar(proposto: VereditoProposto, tentativa: str) -> motor_veredito.VereditoValidado:
    try:
        return motor_veredito.validar(
            proposto.tipo, tentativa, proposto.pericia, proposto.dificuldade, proposto.modo
        )
    except motor_veredito.VereditoInvalidoError as ex:
        raise ErroDeFerramentaError(ex.codigo, ex.mensagem, ex.alternativa) from ex


def _modificadores(ctx: Contexto, teste: motor_veredito.Teste) -> dict[str, int]:
    """A composição do modificador vem da ficha: atributo e, se houver, proficiência."""
    personagem_id: str | None = ctx.extras.get("personagem_id")
    if personagem_id is None:
        return {}
    _, d = personagens.consultar(ctx.con, ctx.campanha_id, personagem_id)
    if teste.chave.startswith("atributo:"):
        return {ATRIBUTO_PT[teste.atributo]: d.modificadores[teste.atributo]}
    return dict(d.pericias[teste.chave].partes)


def dar_veredito(entrada: Estrita, ctx: Contexto) -> dict[str, Any]:
    assert isinstance(entrada, DarVeredito)
    validado = _validar(entrada.veredito, entrada.tentativa)
    consistencia = motor_veredito.comparar(validado, vereditos.anteriores(ctx.con, ctx.campanha_id))
    divergiu_de = None
    if not consistencia.coerente:
        assert consistencia.anterior is not None
        if not entrada.motivo_divergencia:
            raise ErroDeFerramentaError(
                "veredito_divergente",
                consistencia.motivo() or "veredito diverge de um anterior",
                {
                    "manter": {
                        "tipo": consistencia.anterior.tipo,
                        "pericia": consistencia.anterior.pericia,
                        "dificuldade": consistencia.anterior.dificuldade,
                    },
                    "ou_informar": "motivo_divergencia: o que mudou na cena",
                },
            )
        divergiu_de = consistencia.anterior.seq

    saida: dict[str, Any] = {
        "veredito": {
            "tipo": validado.tipo,
            "pericia": validado.teste.nome_pt if validado.teste else None,
            "dificuldade": validado.dificuldade,
        },
        "consistencia": {
            "anterior": consistencia.anterior.seq if consistencia.anterior else None,
            "coerente": consistencia.coerente,
            "justificada": divergiu_de is not None,
        },
    }
    rolagem_seq = None
    if validado.tipo == "teste":
        assert validado.teste is not None and validado.dificuldade is not None
        mods = _modificadores(ctx, validado.teste)
        rol = rolagens.rolar(
            ctx.con,
            ctx.campanha_id,
            ctx.sessao_id,
            "C05",
            "1d20",
            f"{validado.teste.nome_pt} contra {validado.dificuldade}: {entrada.tentativa}",
            validado.modo,
            mods,
        )
        rolagem_seq = rol.seq
        sucesso = rol.total >= validado.dificuldade
        saida["rolagem"] = {
            "registro": rol.seq,
            "contador": rol.contador,
            "dados": list(rol.dados),
            "descartados": list(rol.descartados),
            "modificadores": mods,
            "total": rol.total,
        }
        saida["resultado"] = {"sucesso": sucesso, "margem": rol.total - validado.dificuldade}
        saida["mostrar_ao_jogador"] = (
            f"{validado.teste.nome_pt}: {rol.composicao} contra {validado.dificuldade}. {'Sucesso' if sucesso else 'Falha'}."
        )
    elif validado.tipo == "de_cara":
        saida["mostrar_ao_jogador"] = "Consegue, sem teste."
    else:
        saida["mostrar_ao_jogador"] = (
            f"Impossível aqui{': ' + entrada.veredito.motivo if entrada.veredito.motivo else ''}."
        )
    registro = vereditos.registrar(
        ctx.con,
        ctx.campanha_id,
        ctx.sessao_id,
        "C05",
        validado,
        entrada.tentativa,
        rolagem_seq=rolagem_seq,
        divergiu_de=divergiu_de,
        motivo_divergencia=entrada.motivo_divergencia,
    )
    saida["veredito"]["registro"] = registro.seq
    return saida


def responder_pergunta(entrada: Estrita, ctx: Contexto) -> dict[str, Any]:
    """'E se eu fizer?': nenhum dado, nenhum fato, só o registro da consulta."""
    assert isinstance(entrada, ResponderPergunta)
    validado = _validar(entrada.veredito_provavel, entrada.pergunta)
    registro = vereditos.registrar(
        ctx.con, ctx.campanha_id, ctx.sessao_id, "C04", validado, entrada.pergunta, pergunta=True
    )
    return {
        "registro": registro.seq,
        "resposta": entrada.resposta,
        "veredito_provavel": {
            "tipo": validado.tipo,
            "pericia": validado.teste.nome_pt if validado.teste else None,
            "dificuldade": validado.dificuldade,
        },
        "rolou": False,
        "gravou_fato": False,
    }


def perguntar_ao_jogador(entrada: Estrita, ctx: Contexto) -> dict[str, Any]:
    """Esclarecimento: a plataforma pergunta ao jogador e devolve a resposta; sem jogador presente, fica pendente."""
    assert isinstance(entrada, PerguntarAoJogador)
    responder = ctx.extras.get("responder_ao_mestre")
    if responder is None:
        return {"pendente": True, "pergunta": entrada.pergunta, "opcoes": entrada.opcoes}
    resposta = responder(entrada.pergunta, entrada.opcoes)
    return {"pendente": False, "pergunta": entrada.pergunta, "resposta": resposta}


TRATADORES: dict[str, Tratador] = {
    "dar_veredito": dar_veredito,
    "responder_pergunta": responder_pergunta,
    "perguntar_ao_jogador": perguntar_ao_jogador,
}
