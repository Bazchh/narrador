"""Tratadores do combate (card N-09; casos D01, D03, D08). O estado vivo fica em
ctx.extras["combate"] e é gravado no diário a cada mudança."""

from __future__ import annotations

from typing import Any

from narrador.campanha import combate as campanha_combate
from narrador.mestre.protocolo import (
    AgirComoCriatura,
    Contexto,
    DeclararFimDoCombate,
    ErroDeFerramentaError,
    Estrita,
    IniciarCombate,
    Tratador,
)
from narrador.modulo import canonico
from narrador.motor import combate as motor
from narrador.srd import catalogo

ACOES_DA_CRIATURA = ("atacar", "mover", "esquivar", "desengajar", "fugir", "encerrar")


def _estado(ctx: Contexto) -> motor.EstadoCombate:
    estado = ctx.extras.get("combate")
    if estado is None:
        raise ErroDeFerramentaError("acao_nao_permitida", "não há combate em andamento")
    assert isinstance(estado, motor.EstadoCombate)
    return estado


def _guardar(ctx: Contexto, estado: motor.EstadoCombate, origem: str) -> None:
    ctx.extras["combate"] = estado
    campanha_combate.gravar(ctx.con, ctx.campanha_id, ctx.sessao_id, estado, origem)


def _resumo(estado: motor.EstadoCombate, desde: int = 0) -> dict[str, Any]:
    atual = estado.atual
    return {
        "estado": estado.estado,
        "rodada": estado.rodada,
        "turno_de": atual.id if atual else None,
        "ordem": list(estado.ordem),
        "combatentes": [
            {
                "id": c.id,
                "nome": c.nome,
                "lado": c.lado,
                "pv": c.pontos_de_vida,
                "pv_max": c.pontos_de_vida_maximos,
                "zona": c.zona,
                "condicoes": sorted(c.condicoes),
                "fugiu": c.fugiu,
            }
            for c in estado.combatentes.values()
        ],
        "eventos": [{"tipo": e.tipo, "texto": e.texto} for e in estado.eventos[desde:]],
        "aguardando_mestre": estado.aguardando_mestre,
    }


def iniciar_combate(entrada: Estrita, ctx: Contexto) -> dict[str, Any]:
    assert isinstance(entrada, IniciarCombate)
    if ctx.extras.get("combate") is not None and ctx.extras["combate"].estado != "encerrado":
        raise ErroDeFerramentaError("acao_nao_permitida", "já há combate em andamento")
    modulo: canonico.ModuloCanonico = ctx.extras["modulo"]
    personagem_id: str | None = ctx.extras.get("personagem_id")
    if personagem_id is None:
        raise ErroDeFerramentaError("identificador_inexistente", "a campanha não tem personagem vinculado")
    combatentes = [
        campanha_combate.combatente_do_jogador(
            ctx.con, ctx.campanha_id, personagem_id, ctx.extras.get("pv_atual")
        )
    ]
    for p in entrada.participantes:
        if p.id == personagem_id:
            continue
        item = modulo.itens.get(p.id)
        if item is None or item.tipo not in ("criatura", "personagem"):
            raise ErroDeFerramentaError(
                "identificador_inexistente", f"participante desconhecido no módulo: {p.id}"
            )
        mapeamento = modulo.mapeamentos.get(p.id)
        if mapeamento is None or mapeamento.pendente or mapeamento.srd_id is None:
            motor.conferir_transicao("montando", "criatura_pendente")
            raise ErroDeFerramentaError(
                "acao_nao_permitida",
                f"{item.nome} está sem ficha mapeada: o combate fica bloqueado até o dono da mesa resolver (A04)",
                {"item": p.id},
            )
        try:
            criatura = catalogo.criatura(mapeamento.srd_id)
        except catalogo.ForaDoSrdError as ex:
            raise ErroDeFerramentaError("fora_do_srd", str(ex)) from ex
        combatentes.append(
            campanha_combate.combatente_da_criatura(p.id, criatura, p.zona, p.percebeu, nome=item.nome)
        )
    if len(combatentes) < 2:
        raise ErroDeFerramentaError(
            "entrada_invalida", "o combate precisa de pelo menos uma criatura além do personagem"
        )
    rolar = campanha_combate.rolador(ctx.con, ctx.campanha_id, ctx.sessao_id, "D01")
    estado = motor.montar(combatentes, rolar).anotar("situacao", entrada.situacao)
    _guardar(ctx, estado, "D01")
    return _resumo(estado)


def agir_como_criatura(entrada: Estrita, ctx: Contexto) -> dict[str, Any]:
    assert isinstance(entrada, AgirComoCriatura)
    estado = _estado(ctx)
    atual = estado.atual
    if estado.estado != "turno_cri" or atual is None or atual.id != entrada.criatura_id:
        raise ErroDeFerramentaError(
            "acao_nao_permitida",
            f"não é o turno de {entrada.criatura_id}",
            {"turno_de": atual.id if atual else None, "estado": estado.estado},
        )
    acao = (entrada.acao or "atacar").lower()
    if acao not in ACOES_DA_CRIATURA:
        motor.conferir_transicao("turno_cri", "intencao_impossivel")
        raise ErroDeFerramentaError(
            "acao_nao_permitida",
            f"ação desconhecida: {acao}",
            {"acoes": list(ACOES_DA_CRIATURA), "padrao": "atacar o personagem"},
        )
    rolar = campanha_combate.rolador(ctx.con, ctx.campanha_id, ctx.sessao_id, "D03")
    antes = len(estado.eventos)
    try:
        if acao == "atacar":
            alvo = entrada.alvo_id or estado.jogador.id
            # Um turno real é movimento mais ação: fora do corpo a corpo, aproxima-se antes de morder.
            so_corpo_a_corpo = not any(a.a_distancia for a in atual.ataques)
            if so_corpo_a_corpo and atual.zona != "perto" and estado.economia.movimento:
                estado = motor.agir(estado, atual.id, motor.Declaracao("mover", direcao="aproximar"), rolar)
            decl = motor.Declaracao("atacar", alvo=alvo)
        elif acao == "mover":
            decl = motor.Declaracao("mover", direcao="aproximar")
        else:
            decl = motor.Declaracao(acao)  # type: ignore[arg-type]
        estado = motor.agir(estado, atual.id, decl, rolar)
    except motor.AcaoNaoPermitidaError as ex:
        motor.conferir_transicao("turno_cri", "intencao_impossivel")
        raise ErroDeFerramentaError(
            "acao_nao_permitida",
            ex.mensagem,
            {**(ex.alternativa or {}), "padrao": "atacar o personagem, aproximando-se se preciso"},
        ) from ex
    estado = estado.anotar("intencao", entrada.intencao, id=atual.id)
    if (
        estado.estado == "turno_cri"
        and estado.atual is not None
        and estado.atual.id == atual.id
        and not estado.economia.acao
    ):
        estado = motor.encerrar_turno(estado)
    _guardar(ctx, estado, "D03")
    return _resumo(estado, antes)


def declarar_fim_do_combate(entrada: Estrita, ctx: Contexto) -> dict[str, Any]:
    assert isinstance(entrada, DeclararFimDoCombate)
    estado = _estado(ctx)
    try:
        estado, recompensa = motor.encerrar(estado, f"{entrada.motivo}: {entrada.descricao}")
    except motor.TransicaoInvalidaError as ex:
        raise ErroDeFerramentaError("acao_nao_permitida", str(ex)) from ex
    _guardar(ctx, estado, "D08")
    return {
        **_resumo(estado),
        "recompensa": {
            "pontos_de_experiencia": recompensa.pontos_de_experiencia,
            "derrotados": list(recompensa.derrotados),
            "fugidos": list(recompensa.fugidos),
        },
    }


TRATADORES: dict[str, Tratador] = {
    "iniciar_combate": iniciar_combate,
    "agir_como_criatura": agir_como_criatura,
    "declarar_fim_do_combate": declarar_fim_do_combate,
}
