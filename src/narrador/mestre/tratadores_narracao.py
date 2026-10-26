"""Narrar com verificação e registrar fato (card N-10; casos C03, F01, G03)."""

from __future__ import annotations

import json
from typing import Any

from narrador.campanha import fatos
from narrador.mestre.protocolo import (
    Contexto,
    ErroDeFerramentaError,
    Estrita,
    FatoNovo,
    Narrar,
    RegistrarFato,
    Tratador,
)
from narrador.modulo import canonico
from narrador.motor import verificacao


def _modulo(ctx: Contexto) -> canonico.ModuloCanonico:
    modulo = ctx.extras.get("modulo")
    if modulo is None:
        raise ErroDeFerramentaError("entrada_invalida", "sem módulo canônico na mesa")
    assert isinstance(modulo, canonico.ModuloCanonico)
    return modulo


def _nomes(modulo: canonico.ModuloCanonico) -> dict[str, str]:
    return {i.id: i.nome for i in modulo.itens.values()}


def segredos_pendentes(ctx: Contexto) -> list[verificacao.Segredo]:
    modulo = _modulo(ctx)
    descobertos = fatos.segredos_descobertos(ctx.con, ctx.campanha_id) | set(
        ctx.extras.get("segredos_descobertos", ())
    )
    return [
        verificacao.Segredo(
            s.id,
            s.nome,
            str(s.dados.get("texto", "")),
            tuple(s.dados.get("palavras_chave", ())),
            s.condicao_descoberta or "",
        )
        for s in modulo.segredos()
        if s.id not in descobertos
    ]


def vocabulario_da_cena(ctx: Contexto) -> list[str]:
    """Palavras que a cena atual já expõe ao jogador: não contam como vazamento."""
    modulo = _modulo(ctx)
    cena_id = ctx.extras.get("cena_atual")
    if not cena_id or cena_id not in modulo.itens:
        return []
    recorte = canonico.recortar(modulo, cena_id)
    return [json.dumps(recorte.narravel(), ensure_ascii=False)]


def verificar_texto(ctx: Contexto, texto: str, novos: list[FatoNovo]) -> verificacao.Verificacao:
    modulo = _modulo(ctx)
    declarados = [verificacao.FatoDeclarado(f.tipo, f.referencia, f.resumo) for f in novos]
    ativos = fatos.ativos(ctx.con, ctx.campanha_id, _nomes(modulo))
    # Um fato de conhecimento sobre um segredo É a descoberta dele: não conta como vazamento.
    descobrindo = {
        f.referencia
        for f in novos
        if f.tipo == "conhecimento" and f.conhecimento == "conhecido" and f.referencia
    }
    segredos = [s for s in segredos_pendentes(ctx) if s.id not in descobrindo]
    return verificacao.verificar(texto, declarados, segredos, ativos, vocabulario_da_cena(ctx))


def _registrar_verificacao(ctx: Contexto, resultado: verificacao.Verificacao, texto: str) -> int:
    dados = {
        "aprovado": resultado.aprovado,
        "violacoes": [v.__dict__ for v in resultado.violacoes],
        "conferido": resultado.conferido,
        "texto": texto[:400],
    }
    cur = ctx.con.execute(
        "insert into diario (campanha_id, sessao_id, tipo, origem, dados) values (?, ?, ?, 'G03', ?)",
        (
            ctx.campanha_id,
            ctx.sessao_id,
            "verificacao" if resultado.aprovado else "ocorrencia",
            json.dumps(dados, ensure_ascii=False),
        ),
    )
    assert cur.lastrowid is not None
    return int(cur.lastrowid)


def _conferir_referencia(ctx: Contexto, referencia: str | None) -> None:
    if (
        referencia is not None
        and referencia not in _modulo(ctx).itens
        and referencia != ctx.extras.get("personagem_id")
    ):
        raise ErroDeFerramentaError(
            "identificador_inexistente", f"referência desconhecida no módulo: {referencia}"
        )


def narrar(entrada: Estrita, ctx: Contexto) -> dict[str, Any]:
    """Saída final do turno: texto mais fatos novos. Só chega à tela se a verificação aprovar."""
    assert isinstance(entrada, Narrar)
    if not entrada.texto.strip():
        raise ErroDeFerramentaError("entrada_invalida", "narração vazia")
    for f in entrada.fatos:
        _conferir_referencia(ctx, f.referencia)
    resultado = verificar_texto(ctx, entrada.texto, list(entrada.fatos))
    registro = _registrar_verificacao(ctx, resultado, entrada.texto)
    if not resultado.aprovado:
        primeira = resultado.violacoes[0]
        raise ErroDeFerramentaError(
            primeira.codigo,
            "; ".join(v.detalhe for v in resultado.violacoes),
            {
                "violacoes": [v.__dict__ for v in resultado.violacoes],
                "verificacao": registro,
                "instrucao": "narre de novo sem o que foi apontado",
            },
        )
    gravados = [
        fatos.registrar(
            ctx.con,
            ctx.campanha_id,
            ctx.sessao_id,
            "C03",
            f.tipo,
            f.resumo,
            f.referencia,
            f.conhecimento,
            cena_id=ctx.extras.get("cena_atual"),
        ).seq
        for f in entrada.fatos
    ]
    return {
        "aprovado": True,
        "texto": entrada.texto,
        "fatos": [
            {**f.model_dump(), "registro": seq} for f, seq in zip(entrada.fatos, gravados, strict=True)
        ],
        "desvios": [d.model_dump() for d in entrada.desvios],
        "verificacao": registro,
    }


def registrar_fato(entrada: Estrita, ctx: Contexto) -> dict[str, Any]:
    assert isinstance(entrada, RegistrarFato)
    f = entrada.fato
    _conferir_referencia(ctx, f.referencia)
    resultado = verificar_texto(ctx, "", [f])
    if not resultado.aprovado:
        raise ErroDeFerramentaError(
            resultado.violacoes[0].codigo, "; ".join(v.detalhe for v in resultado.violacoes)
        )
    gravado = fatos.registrar(
        ctx.con,
        ctx.campanha_id,
        ctx.sessao_id,
        "F01",
        f.tipo,
        f.resumo,
        f.referencia,
        f.conhecimento,
        cena_id=ctx.extras.get("cena_atual"),
    )
    return {"registro": gravado.seq, **f.model_dump()}


def texto_literal_da_cena(ctx: Contexto) -> str:
    """A alternativa mecânica quando o mestre falha duas vezes (C03 E1): a descrição do módulo, como está."""
    modulo = _modulo(ctx)
    cena_id = ctx.extras.get("cena_atual")
    if not cena_id or cena_id not in modulo.itens:
        return ""
    return str(modulo.itens[cena_id].dados.get("descricao", modulo.itens[cena_id].nome))


TRATADORES: dict[str, Tratador] = {"narrar": narrar, "registrar_fato": registrar_fato}
