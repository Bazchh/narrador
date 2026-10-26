"""Card N-06: personagem pré-gerado e valores derivados.

Critério de aceite: dado o pré-gerado com cota de malha e escudo, quando a ficha é
consultada, então a classe de armadura é 18 e a composição mostra 16 da armadura mais
2 do escudo.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from narrador.campanha import banco as campanha
from narrador.campanha import personagens
from narrador.motor import ficha as motor_ficha
from narrador.srd import catalogo


@pytest.fixture
def cv() -> Iterator[sqlite3.Connection]:
    con = campanha.criar()
    con.execute(
        "insert into campanha (id, nome, aventura_id, modulo_versao, semente, classificacao)"
        " values ('cp1','Teste','av-porao',1,'semente-abc','adulto')"
    )
    yield con
    con.close()


def test_pre_gerado_tem_ca_18_de_cota_e_escudo() -> None:
    brenna = motor_ficha.pre_gerados()[0]
    d = motor_ficha.calcular(brenna)
    assert d.classe_armadura.total == 18
    assert d.classe_armadura.partes == {"Cota de malha": 16, "escudo": 2}
    assert d.classe_armadura.explicar() == "18 = 16 (Cota de malha) + 2 (escudo)"


def test_derivados_batem_com_o_srd() -> None:
    brenna = motor_ficha.pre_gerados()[0]
    d = motor_ficha.calcular(brenna)
    assert d.modificadores == {"str": 3, "dex": 1, "con": 2, "int": 0, "wis": 1, "cha": -1}
    assert d.bonus_proficiencia == 2
    assert d.pontos_de_vida_maximos.total == 12  # d10 máximo + 2 de constituição
    assert d.iniciativa.total == 1
    assert d.salvaguardas["str"].partes == {"Força": 3, "proficiência": 2}
    assert d.salvaguardas["con"].total == 4 and d.salvaguardas["dex"].total == 1
    assert d.pericias["srd:pericia:athletics"].total == 5
    assert d.pericias["srd:pericia:stealth"].total == 1
    assert d.percepcao_passiva.total == 13
    assert d.velocidade_pes == 30


def test_ataques_derivados() -> None:
    d = motor_ficha.calcular(motor_ficha.pre_gerados()[0])
    espada, azagaia = d.ataques
    assert espada.arma.nome == "Longsword" and espada.bonus_ataque.total == 5 and espada.bonus_dano.total == 3
    assert espada.dano_dados == "1d8" and espada.dano_tipo == "cortante"
    assert azagaia.atributo == "str"  # arremesso usa Força


def test_armadura_media_limita_a_destreza() -> None:
    brenna = motor_ficha.pre_gerados()[0]
    agil = brenna.model_copy(
        update={
            "atributos": {**brenna.atributos, "dex": 18},
            "armadura_id": "srd:armadura:breastplate",
            "escudo": False,
        }
    )
    d = motor_ficha.calcular(agil)
    assert d.classe_armadura.partes == {"Peitoral": 14, "Destreza": 2}


def test_sem_armadura_e_dez_mais_destreza() -> None:
    brenna = motor_ficha.pre_gerados()[0]
    d = motor_ficha.calcular(brenna.model_copy(update={"armadura_id": None, "escudo": False}))
    assert d.classe_armadura.partes == {"base": 10, "Destreza": 1}


def test_ficha_invalida_e_recusada() -> None:
    brenna = motor_ficha.pre_gerados()[0]
    with pytest.raises(catalogo.ForaDoSrdError):
        motor_ficha.validar(brenna.model_copy(update={"armadura_id": "srd:armadura:mithral"}))
    with pytest.raises(motor_ficha.FichaInvalidaError):
        motor_ficha.validar(brenna.model_copy(update={"pontos_de_vida_maximos": 40}))
    with pytest.raises(motor_ficha.FichaInvalidaError):
        motor_ficha.validar(
            brenna.model_copy(
                update={"pericias_proficientes": ["srd:pericia:athletics", "srd:pericia:athletics"]}
            )
        )
    with pytest.raises(motor_ficha.FichaInvalidaError):
        motor_ficha.validar(brenna.model_copy(update={"armadura_id": "srd:armadura:shield"}))


def test_ficha_gravada_e_versionada(cv: sqlite3.Connection) -> None:
    brenna = motor_ficha.pre_gerados()[0]
    g1 = personagens.gravar(cv, "cp1", brenna)
    g2 = personagens.gravar(
        cv, "cp1", brenna.model_copy(update={"nome": "Brenna, a Manca"}), personagem_id=g1.personagem_id
    )
    assert (g1.versao, g2.versao) == (1, 2)
    assert personagens.versoes(cv, "cp1", g1.personagem_id) == [1, 2]
    assert personagens.carregar(cv, "cp1", g1.personagem_id, versao=1).ficha.nome == "Brenna"
    gravada, derivados = personagens.consultar(cv, "cp1", g1.personagem_id)
    assert gravada.versao == 2 and gravada.ficha.nome == "Brenna, a Manca"
    assert derivados.classe_armadura.total == 18


def test_personagem_inexistente(cv: sqlite3.Connection) -> None:
    with pytest.raises(personagens.PersonagemInexistenteError):
        personagens.consultar(cv, "cp1", "pj-nao-existe")


def test_pre_gerado_so_usa_conteudo_do_srd() -> None:
    for f in motor_ficha.pre_gerados():
        assert f.origem == "pre_gerado"
        motor_ficha.validar(f)  # tudo que a ficha cita existe no SRD carregado
