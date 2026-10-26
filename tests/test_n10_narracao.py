"""Card N-10: narração com verificação de segredo e fato.

Critério de aceite: dado o segredo do anel não descoberto, quando o provedor falso narra
mencionando o túnel atrás dos barris cavado pelo contrabandista, então a narração é
devolvida com segredo_bloqueado, a ocorrência é registrada e a segunda tentativa,
limpa, chega à tela.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest

from narrador.campanha import banco as campanha_banco
from narrador.campanha import fatos, personagens
from narrador.mestre import protocolo, registro, servico, tratadores_narracao
from narrador.modulo import banco as modulo_banco
from narrador.modulo import canonico
from narrador.motor import ficha as motor_ficha
from narrador.motor import verificacao


@pytest.fixture
def mesa() -> Iterator[protocolo.Contexto]:
    cv = campanha_banco.criar()
    cv.execute(
        "insert into campanha (id, nome, aventura_id, modulo_versao, semente, classificacao)"
        " values ('cp1','Teste','av-porao',1,'semente-abc','adulto')"
    )
    cv.execute("insert into sessao (id, campanha_id, numero) values ('s1','cp1',1)")
    av = modulo_banco.criar()
    modulo_banco.aplicar_semente(av)
    pj = personagens.gravar(cv, "cp1", motor_ficha.pre_gerados()[0])
    yield protocolo.Contexto(
        cv,
        "cp1",
        "s1",
        "t-1",
        {
            "modulo": canonico.carregar(av, "av-porao", 1),
            "cena_atual": "cena-porao",
            "personagem_id": pj.personagem_id,
        },
    )
    cv.close()
    av.close()


def chamada(ferramenta: str, entrada: dict[str, object]) -> protocolo.Chamada:
    return protocolo.Chamada("c", ferramenta, entrada, "t-1")


def ocorrencias(ctx: protocolo.Contexto) -> list[dict[str, object]]:
    return [
        json.loads(d)
        for (d,) in ctx.con.execute("select dados from diario where tipo = 'ocorrencia' order by seq")
    ]


# ---------------------------------------------------------------- aceite


def test_vazamento_e_devolvido_e_a_segunda_tentativa_chega_a_tela(mesa: protocolo.Contexto) -> None:
    ex = protocolo.Executor(mesa, registro.TODOS)
    roteiro = [
        [
            servico.Passo(
                "narrar",
                {
                    "texto": "Atrás dos barris há um túnel, cavado por um contrabandista que perdeu o anel numa aposta."
                },
            ),
            servico.Passo(
                "narrar", {"texto": "Atrás dos barris roídos, a parede cede para um túnel escuro e úmido."}
            ),
        ]
    ]
    turno = servico.ServicoFalso(roteiro).rodar_turno(
        servico.ContextoDoTurno("t-1", "", "", "", {}, {}, "olho atrás dos barris"),
        ex.disponiveis(),
        ex.executar,
    )
    primeira, segunda = turno.chamadas
    assert primeira.erro is not None and primeira.erro.codigo == "segredo_bloqueado"
    assert "contrabandista" in primeira.erro.mensagem
    assert primeira.erro.alternativa is not None and primeira.erro.alternativa["instrucao"].startswith(
        "narre de novo"
    )
    assert segunda.ok and turno.narracao is not None and "túnel escuro" in turno.narracao.texto
    assert (
        len(ocorrencias(mesa)) == 1 and ocorrencias(mesa)[0]["violacoes"][0]["codigo"] == "segredo_bloqueado"
    )  # type: ignore[index]
    assert mesa.con.execute("select count(*) from diario where tipo = 'verificacao'").fetchone() == (1,)


# ---------------------------------------------------------------- fatos


def test_narracao_aprovada_grava_os_fatos_e_o_recorte_os_mostra(mesa: protocolo.Contexto) -> None:
    ex = protocolo.Executor(mesa, registro.TODOS)
    r = ex.executar(
        chamada(
            "narrar",
            {
                "texto": "Você derruba a porta do alçapão com um chute.",
                "fatos": [
                    {
                        "tipo": "estado_local",
                        "referencia": "cena-porao",
                        "resumo": "a porta do alçapão está arrombada",
                    }
                ],
            },
        )
    )
    assert r.ok and r.saida is not None and r.saida["fatos"][0]["registro"] > 0
    assert [f.resumo for f in fatos.listar(mesa.con, "cp1")] == ["a porta do alçapão está arrombada"]
    recorte = ex.executar(chamada("consultar_cena", {}))
    assert (
        recorte.ok
        and recorte.saida is not None
        and recorte.saida["fatos"] == ["a porta do alçapão está arrombada"]
    )


def test_fato_sucedido_sai_dos_ativos_mas_nao_e_apagado(mesa: protocolo.Contexto) -> None:
    f1 = fatos.registrar(
        mesa.con, "cp1", "s1", "F01", "estado_local", "a porta está trancada", "cena-taverna"
    )
    fatos.registrar(
        mesa.con,
        "cp1",
        "s1",
        "F01",
        "estado_local",
        "a porta está aberta",
        "cena-taverna",
        substitui_seq=f1.seq,
    )
    assert [f.resumo for f in fatos.ativos(mesa.con, "cp1")] == ["a porta está aberta"]
    assert len(fatos.listar(mesa.con, "cp1")) == 2


def test_contradicao_com_fato_de_morte_e_barrada(mesa: protocolo.Contexto) -> None:
    fatos.registrar(
        mesa.con,
        "cp1",
        "s1",
        "F01",
        "estado_personagem",
        "o taverneiro foi morto pelos ratos",
        "np-taverneiro",
    )
    ex = protocolo.Executor(mesa, registro.TODOS)
    r = ex.executar(chamada("narrar", {"texto": "O Taverneiro sorri e oferece uma caneca."}))
    assert r.erro is not None and r.erro.codigo == "contradiz_fato" and "morto" in r.erro.mensagem
    r2 = ex.executar(
        chamada(
            "registrar_fato",
            {
                "fato": {
                    "tipo": "estado_personagem",
                    "referencia": "np-taverneiro",
                    "resumo": "está nervoso atrás do balcão",
                }
            },
        )
    )
    assert r2.erro is not None and r2.erro.codigo == "contradiz_fato"
    r3 = ex.executar(chamada("narrar", {"texto": "O corpo do taverneiro jaz atrás do balcão."}))
    assert r3.ok


def test_segredo_descoberto_pode_ser_narrado(mesa: protocolo.Contexto) -> None:
    ex = protocolo.Executor(mesa, registro.TODOS)
    r = ex.executar(
        chamada(
            "registrar_fato",
            {
                "fato": {
                    "tipo": "conhecimento",
                    "referencia": "seg-anel",
                    "resumo": "o personagem descobriu que o anel foi perdido numa aposta com o contrabandista",
                }
            },
        )
    )
    assert r.ok, r.erro  # o próprio fato de descoberta pode citar o segredo que descobre
    assert fatos.segredos_descobertos(mesa.con, "cp1") == {"seg-anel"}
    r2 = ex.executar(
        chamada("narrar", {"texto": "Agora faz sentido: o contrabandista levou o anel numa aposta."})
    )
    assert r2.ok
    recorte = ex.executar(chamada("consultar_cena", {}))
    assert recorte.ok and recorte.saida is not None and recorte.saida["nao_narrar"] == []


def test_referencia_desconhecida_e_recusada(mesa: protocolo.Contexto) -> None:
    r = protocolo.Executor(mesa, registro.TODOS).executar(
        chamada("registrar_fato", {"fato": {"tipo": "evento", "referencia": "np-dragao", "resumo": "x"}})
    )
    assert r.erro is not None and r.erro.codigo == "identificador_inexistente"


def test_texto_literal_da_cena(mesa: protocolo.Contexto) -> None:
    assert tratadores_narracao.texto_literal_da_cena(mesa).startswith("Escuro, úmido")


# ---------------------------------------------------------------- motor puro


def test_termos_do_segredo_ignoram_o_vocabulario_da_cena() -> None:
    s = verificacao.Segredo("s", "O cavador do túnel", "O túnel foi cavado por um contrabandista.")
    assert "contrabandista" in s.termos(excluir=["tunel"]) and "tunel" not in s.termos(excluir=["tunel"])


def test_verificacao_pura_sem_violacao() -> None:
    v = verificacao.verificar(
        "Você vê barris.", [], [verificacao.Segredo("s", "x", "y", ("contrabandista",))], []
    )
    assert v.aprovado and v.conferido["segredos"] == 1
