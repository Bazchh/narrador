"""Card N-08: veredito, teste e pergunta.

Critério de aceite: dado um veredito de teste de Atletismo 15 gravado na sessão 1, quando
o mestre dá Atletismo 25 para a mesma situação na sessão 2 sem motivo, então o motor
devolve veredito_divergente com o anterior, e uma pergunta "e se eu escalar?" não gera
rolagem nem fato.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from narrador.campanha import banco as campanha_banco
from narrador.campanha import personagens, vereditos
from narrador.mestre import protocolo, tratadores, tratadores_veredito
from narrador.modulo import banco as modulo_banco
from narrador.modulo import canonico
from narrador.motor import entrada, veredito
from narrador.motor import ficha as motor_ficha

TODOS = {**tratadores.TRATADORES, **tratadores_veredito.TRATADORES}


@pytest.fixture
def mesa() -> Iterator[protocolo.Contexto]:
    cv = campanha_banco.criar()
    cv.execute(
        "insert into campanha (id, nome, aventura_id, modulo_versao, semente, classificacao)"
        " values ('cp1','Teste','av-porao',1,'semente-abc','adulto')"
    )
    cv.execute("insert into sessao (id, campanha_id, numero) values ('s1','cp1',1)")
    cv.execute("insert into sessao (id, campanha_id, numero) values ('s2','cp1',2)")
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


def chamada(ferramenta: str, entrada: dict[str, object], turno: str = "t-1") -> protocolo.Chamada:
    return protocolo.Chamada("c", ferramenta, entrada, turno)


def pedido_teste(
    pericia: str, dificuldade: int, tentativa: str = "eu tento escalar o muro do pátio"
) -> dict[str, object]:
    return {
        "tentativa": tentativa,
        "veredito": {"tipo": "teste", "pericia": pericia, "dificuldade": dificuldade},
    }


# ---------------------------------------------------------------- aceite


def test_veredito_divergente_sem_motivo_e_recusado_e_pergunta_nao_rola(mesa: protocolo.Contexto) -> None:
    ex = protocolo.Executor(mesa, TODOS)
    r1 = ex.executar(chamada("dar_veredito", pedido_teste("Atletismo", 15)))
    assert r1.ok and r1.saida is not None and r1.saida["rolagem"]["contador"] == 1

    mesa.sessao_id, mesa.turno_atual = "s2", "t-2"
    r2 = ex.executar(
        chamada("dar_veredito", pedido_teste("Atletismo", 25, "tento escalar o muro do pátio"), "t-2")
    )
    assert r2.erro is not None and r2.erro.codigo == "veredito_divergente"
    assert "dificuldade 15" in r2.erro.mensagem
    assert r2.erro.alternativa is not None and r2.erro.alternativa["manter"]["dificuldade"] == 15

    antes = (
        len(vereditos.listar(mesa.con, "cp1")),
        len(mesa.con.execute("select * from rolagem").fetchall()),
        len(mesa.con.execute("select * from fato").fetchall()),
    )
    r3 = ex.executar(
        chamada(
            "responder_pergunta",
            {
                "pergunta": "e se eu escalar o muro?",
                "resposta": "Pediria Atletismo contra 15.",
                "veredito_provavel": {"tipo": "teste", "pericia": "Atletismo", "dificuldade": 15},
            },
            "t-2",
        )
    )
    assert r3.ok and r3.saida is not None and r3.saida["rolou"] is False and r3.saida["gravou_fato"] is False
    depois = (
        len(vereditos.listar(mesa.con, "cp1")),
        len(mesa.con.execute("select * from rolagem").fetchall()),
        len(mesa.con.execute("select * from fato").fetchall()),
    )
    assert depois == (antes[0] + 1, antes[1], antes[2])
    assert vereditos.listar(mesa.con, "cp1")[-1].pergunta


# ---------------------------------------------------------------- veredito


def test_teste_rola_com_os_modificadores_da_ficha(mesa: protocolo.Contexto) -> None:
    r = protocolo.Executor(mesa, TODOS).executar(chamada("dar_veredito", pedido_teste("Atletismo", 15)))
    assert r.ok and r.saida is not None
    rol = r.saida["rolagem"]
    assert rol["modificadores"] == {"Força": 3, "proficiência": 2}  # Brenna é proficiente em Atletismo
    assert rol["total"] == rol["dados"][0] + 5
    assert r.saida["resultado"]["sucesso"] == (rol["total"] >= 15)
    assert r.saida["mostrar_ao_jogador"].startswith("Atletismo: d20 (")
    assert vereditos.listar(mesa.con, "cp1")[0].rolagem_seq == rol["registro"]


def test_divergencia_com_motivo_e_aceita_e_registrada(mesa: protocolo.Contexto) -> None:
    ex = protocolo.Executor(mesa, TODOS)
    ex.executar(chamada("dar_veredito", pedido_teste("Atletismo", 15)))
    r = ex.executar(
        chamada(
            "dar_veredito",
            {**pedido_teste("Atletismo", 25), "motivo_divergencia": "o muro agora está molhado e sem apoio"},
        )
    )
    assert r.ok and r.saida is not None and r.saida["consistencia"]["justificada"]
    ultimo = vereditos.listar(mesa.con, "cp1")[-1]
    assert ultimo.divergiu_de == vereditos.listar(mesa.con, "cp1")[0].seq


def test_situacao_diferente_nao_e_divergencia(mesa: protocolo.Contexto) -> None:
    ex = protocolo.Executor(mesa, TODOS)
    ex.executar(chamada("dar_veredito", pedido_teste("Atletismo", 15)))
    r = ex.executar(
        chamada("dar_veredito", pedido_teste("Furtividade", 20, "eu tento passar sem ser visto pelo guarda"))
    )
    assert r.ok and r.saida is not None and r.saida["consistencia"]["anterior"] is None


def test_dificuldade_fora_da_escala(mesa: protocolo.Contexto) -> None:
    r = protocolo.Executor(mesa, TODOS).executar(chamada("dar_veredito", pedido_teste("Atletismo", 45)))
    assert r.erro is not None and r.erro.codigo == "dificuldade_fora_da_escala"
    assert r.erro.alternativa is not None and r.erro.alternativa["escala"]["30"] == "quase impossível"


def test_pericia_inexistente(mesa: protocolo.Contexto) -> None:
    r = protocolo.Executor(mesa, TODOS).executar(chamada("dar_veredito", pedido_teste("Escalada", 15)))
    assert r.erro is not None and r.erro.codigo == "pericia_inexistente"


def test_de_cara_e_impossivel_nao_rolam(mesa: protocolo.Contexto) -> None:
    ex = protocolo.Executor(mesa, TODOS)
    r = ex.executar(
        chamada("dar_veredito", {"tentativa": "eu abro a porta destrancada", "veredito": {"tipo": "de_cara"}})
    )
    assert (
        r.ok
        and r.saida is not None
        and "rolagem" not in r.saida
        and r.saida["mostrar_ao_jogador"] == "Consegue, sem teste."
    )
    r2 = ex.executar(
        chamada(
            "dar_veredito",
            {
                "tentativa": "eu voo até o telhado",
                "veredito": {"tipo": "impossivel", "motivo": "você não tem como voar"},
            },
        )
    )
    assert r2.ok and r2.saida is not None and "não tem como voar" in r2.saida["mostrar_ao_jogador"]
    r3 = ex.executar(
        chamada("dar_veredito", {"tentativa": "x", "veredito": {"tipo": "de_cara", "dificuldade": 10}})
    )
    assert r3.erro is not None and r3.erro.codigo == "entrada_invalida"


def test_teste_de_atributo_puro(mesa: protocolo.Contexto) -> None:
    r = protocolo.Executor(mesa, TODOS).executar(
        chamada("dar_veredito", pedido_teste("Força", 12, "eu tento arrombar a porta"))
    )
    assert r.ok and r.saida is not None and r.saida["rolagem"]["modificadores"] == {"Força": 3}


def test_vantagem_no_teste(mesa: protocolo.Contexto) -> None:
    r = protocolo.Executor(mesa, TODOS).executar(
        chamada(
            "dar_veredito",
            {
                "tentativa": "eu tento convencer o guarda",
                "veredito": {"tipo": "teste", "pericia": "Persuasão", "dificuldade": 15, "modo": "vantagem"},
            },
        )
    )
    assert r.ok and r.saida is not None and len(r.saida["rolagem"]["descartados"]) == 1


def test_perguntar_ao_jogador_com_e_sem_jogador(mesa: protocolo.Contexto) -> None:
    ex = protocolo.Executor(mesa, TODOS)
    r = ex.executar(
        chamada(
            "perguntar_ao_jogador", {"pergunta": "Você pergunta ou já faz?", "opcoes": ["pergunto", "faço"]}
        )
    )
    assert r.ok and r.saida is not None and r.saida["pendente"]
    mesa.extras["responder_ao_mestre"] = lambda pergunta, opcoes: opcoes[1]
    r2 = ex.executar(
        chamada(
            "perguntar_ao_jogador", {"pergunta": "Você pergunta ou já faz?", "opcoes": ["pergunto", "faço"]}
        )
    )
    assert r2.ok and r2.saida is not None and r2.saida["resposta"] == "faço"


# ---------------------------------------------------------------- motor puro


@pytest.mark.parametrize(
    ("texto", "classe"),
    [
        ("e se eu escalar o muro?", "pergunta"),
        ("Posso tentar abrir a fechadura?", "pergunta"),
        ("dá pra pular o fosso?", "pergunta"),
        ("eu tento escalar o muro", "acao"),
        ("Ataco o rato com a espada", "acao"),
        ("vou até o balcão e falo com o taverneiro", "acao"),
        ("o muro", "ambigua"),
        ("", "ambigua"),
        ("eu pulo?", "ambigua"),
    ],
)
def test_classificacao_da_entrada(texto: str, classe: str) -> None:
    assert entrada.classificar(texto) == classe


def test_situacao_comparavel_ignora_palavras_vazias() -> None:
    assert veredito.situacao_comparavel("Eu tento escalar o muro do pátio") == veredito.situacao_comparavel(
        "tento escalar o muro do patio"
    )


def test_comparar_tolera_faixa_de_dois_pontos() -> None:
    v = veredito.validar("teste", "eu tento escalar o muro", "Atletismo", 17)
    anterior = veredito.VereditoAnterior(
        1, veredito.situacao_comparavel("tento escalar o muro"), "teste", "srd:pericia:athletics", 15
    )
    assert veredito.comparar(v, [anterior]).coerente
    v2 = veredito.validar("teste", "eu tento escalar o muro", "Atletismo", 18)
    assert not veredito.comparar(v2, [anterior]).coerente
