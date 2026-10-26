"""Card N-07: protocolo de ferramentas e provedor falso.

Critério de aceite: dado o provedor falso com um roteiro de duas chamadas, quando o turno
roda, então as duas chamadas são executadas na ordem, registradas no diário com o turno,
e a terceira, de turno encerrado, é recusada e registrada.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator

import pytest

from narrador.campanha import banco as campanha_banco
from narrador.campanha import personagens
from narrador.mestre import protocolo, servico, tratadores
from narrador.modulo import banco as modulo_banco
from narrador.modulo import canonico
from narrador.motor import ficha as motor_ficha


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
    modulo = canonico.carregar(av, "av-porao", 1)
    pj = personagens.gravar(cv, "cp1", motor_ficha.pre_gerados()[0])
    yield protocolo.Contexto(
        con=cv,
        campanha_id="cp1",
        sessao_id="s1",
        turno_atual="t-1",
        extras={"modulo": modulo, "cena_atual": "cena-porao", "personagem_id": pj.personagem_id},
    )
    cv.close()
    av.close()


def contexto_do_turno(turno: str) -> servico.ContextoDoTurno:
    return servico.ContextoDoTurno(
        turno=turno, sistema="", mesa="", campanha="", cena={}, personagem={}, entrada="olho em volta"
    )


def consultas(con: sqlite3.Connection) -> list[dict[str, object]]:
    return [
        json.loads(d) for (d,) in con.execute("select dados from diario where tipo = 'consulta' order by seq")
    ]


# ---------------------------------------------------------------- aceite


def test_duas_chamadas_na_ordem_e_a_terceira_de_turno_encerrado_recusada(mesa: protocolo.Contexto) -> None:
    executor = protocolo.Executor(mesa, tratadores.TRATADORES)
    roteiro = [
        [
            servico.Passo("consultar_cena", {}),
            servico.Passo("narrar", {"texto": "Dois pares de olhos vermelhos brilham entre os barris."}),
            servico.Passo("consultar_ficha", {"secao": "vida"}, turno="t-0"),  # turno já encerrado
        ]
    ]
    falso = servico.ServicoFalso(roteiro)
    turno = falso.rodar_turno(contexto_do_turno("t-1"), executor.disponiveis(), executor.executar)

    assert [r.ferramenta for r in turno.chamadas] == ["consultar_cena", "narrar", "consultar_ficha"]
    assert turno.chamadas[0].ok and turno.chamadas[1].ok
    assert turno.chamadas[2].erro is not None and turno.chamadas[2].erro.codigo == "turno_encerrado"
    assert turno.narracao is not None and "olhos vermelhos" in turno.narracao.texto
    assert turno.falha is None

    registros = consultas(mesa.con)
    assert [r["ferramenta"] for r in registros] == ["consultar_cena", "narrar", "consultar_ficha"]
    assert [r["turno"] for r in registros] == ["t-1", "t-1", "t-0"]
    assert registros[2]["erro"]["codigo"] == "turno_encerrado"  # type: ignore[index]
    assert turno.chamadas[2].erro.registro == turno.chamadas[2].registro


# ---------------------------------------------------------------- contrato


def test_as_quinze_ferramentas_existem_com_esquema_estrito() -> None:
    assert len(protocolo.FERRAMENTAS) == 15
    for f in protocolo.FERRAMENTAS.values():
        esquema = f.esquema()
        assert esquema["additionalProperties"] is False, f.nome
        assert f.casos, f.nome


def test_os_treze_codigos_de_erro() -> None:
    assert len(protocolo.CODIGOS_DE_ERRO) == 13


def test_campo_desconhecido_e_recusado_antes_de_executar(mesa: protocolo.Contexto) -> None:
    executor = protocolo.Executor(mesa, tratadores.TRATADORES)
    r = executor.executar(
        protocolo.Chamada("c1", "consultar_cena", {"cena_id": "cena-porao", "spoiler": True}, "t-1")
    )
    assert r.erro is not None and r.erro.codigo == "entrada_invalida" and "spoiler" in r.erro.mensagem
    assert r.erro.alternativa is not None and "esquema" in r.erro.alternativa
    assert r.registro is not None


def test_erro_do_tratador_volta_como_resultado_marcado(mesa: protocolo.Contexto) -> None:
    executor = protocolo.Executor(mesa, tratadores.TRATADORES)
    r = executor.executar(
        protocolo.Chamada("c1", "consultar_srd", {"tipo": "criatura", "nome": "Beholder"}, "t-1")
    )
    assert r.erro is not None and r.erro.codigo == "fora_do_srd"
    r2 = executor.executar(protocolo.Chamada("c2", "consultar_cena", {"cena_id": "cena-sotao"}, "t-1"))
    assert r2.erro is not None and r2.erro.codigo == "identificador_inexistente"
    assert r2.erro.alternativa is not None and {v["id"] for v in r2.erro.alternativa["vizinhas"]} == {
        "cena-tunel",
        "cena-taverna",
    }


def test_ferramenta_sem_tratador_nao_e_exposta_nem_executada(mesa: protocolo.Contexto) -> None:
    executor = protocolo.Executor(mesa, tratadores.TRATADORES)
    assert "dar_veredito" not in {f.nome for f in executor.disponiveis()}
    r = executor.executar(
        protocolo.Chamada("c1", "dar_veredito", {"tentativa": "x", "veredito": {"tipo": "de_cara"}}, "t-1")
    )
    assert r.erro is not None and r.erro.codigo == "entrada_invalida"


def test_tratador_para_ferramenta_inexistente_e_erro_de_programacao(mesa: protocolo.Contexto) -> None:
    with pytest.raises(KeyError):
        protocolo.Executor(mesa, {"abrir_portal": tratadores.narrar})


def test_recorte_chega_ao_mestre_com_segredo_separado(mesa: protocolo.Contexto) -> None:
    executor = protocolo.Executor(mesa, tratadores.TRATADORES)
    r = executor.executar(protocolo.Chamada("c1", "consultar_cena", {}, "t-1"))
    assert r.ok and r.saida is not None
    assert r.saida["cena"]["id"] == "cena-porao" and len(r.saida["presentes"]) == 2
    assert r.saida["nao_narrar"][0]["id"] == "seg-anel"
    assert "contrabandista" not in json.dumps(r.saida["cena"]) + json.dumps(r.saida["presentes"])


def test_ficha_chega_ao_mestre_com_composicao(mesa: protocolo.Contexto) -> None:
    executor = protocolo.Executor(mesa, tratadores.TRATADORES)
    r = executor.executar(protocolo.Chamada("c1", "consultar_ficha", {"secao": "combate"}, "t-1"))
    assert r.ok and r.saida is not None
    assert r.saida["classe_armadura"] == {"total": 18, "composicao": {"Cota de malha": 16, "escudo": 2}}


def test_turno_sem_narrar_e_falha_de_formato(mesa: protocolo.Contexto) -> None:
    executor = protocolo.Executor(mesa, tratadores.TRATADORES)
    falso = servico.ServicoFalso([[servico.Passo("consultar_cena", {})]])
    turno = falso.rodar_turno(contexto_do_turno("t-1"), executor.disponiveis(), executor.executar)
    assert turno.narracao is None and turno.falha is not None and turno.falha.tipo == "formato"


def test_falha_simulada_e_classificada(mesa: protocolo.Contexto) -> None:
    executor = protocolo.Executor(mesa, tratadores.TRATADORES)
    falso = servico.ServicoFalso([[servico.Passo(falha=servico.Falha("indisponivel", "tempo esgotado"))]])
    turno = falso.rodar_turno(contexto_do_turno("t-1"), executor.disponiveis(), executor.executar)
    assert turno.falha == servico.Falha("indisponivel", "tempo esgotado") and turno.chamadas == ()
