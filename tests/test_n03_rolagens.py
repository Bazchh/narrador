"""Card N-03: diário e gerador de rolagens.

Critério de aceite: dada uma campanha com semente e cem rolagens gravadas, quando a
reprodução roda, então cem rolagens refeitas são iguais às gravadas, e uma rolagem com
contador repetido é recusada pelo banco.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from collections.abc import Iterator

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from narrador.campanha import banco as campanha
from narrador.campanha import rolagens
from narrador.motor import dados as motor

FACES = st.sampled_from(motor.FACES_PERMITIDAS)
QUANTIDADE = st.integers(min_value=1, max_value=motor.QUANTIDADE_MAXIMA)
SEMENTE = st.text(min_size=1, max_size=40)
CONTADOR = st.integers(min_value=1, max_value=10**9)


# ---------------------------------------------------------------- motor: propriedades


@given(SEMENTE, CONTADOR, QUANTIDADE, FACES, st.integers(min_value=-20, max_value=20))
def test_cada_dado_fica_na_faixa_e_o_total_fecha(semente: str, contador: int, n: int, m: int, k: int) -> None:
    exp = motor.Expressao(n, m, k)
    r = motor.rolar(semente, contador, exp)
    assert len(r.dados) == n
    assert all(1 <= d <= m for d in r.dados)
    assert r.total == sum(r.dados) + k


@given(SEMENTE, CONTADOR, QUANTIDADE, FACES)
def test_mesma_semente_e_contador_dao_sempre_o_mesmo_resultado(
    semente: str, contador: int, n: int, m: int
) -> None:
    exp = motor.Expressao(n, m)
    assert motor.rolar(semente, contador, exp) == motor.rolar(semente, contador, exp)


@given(SEMENTE, CONTADOR)
def test_vantagem_fica_com_o_maior_e_desvantagem_com_o_menor(semente: str, contador: int) -> None:
    v = motor.rolar(semente, contador, "1d20", "vantagem")
    d = motor.rolar(semente, contador, "1d20", "desvantagem")
    assert len(v.dados) == len(v.descartados) == 1
    assert v.dados[0] >= v.descartados[0]
    assert d.dados[0] <= d.descartados[0]
    assert {v.dados[0], v.descartados[0]} == {d.dados[0], d.descartados[0]}


@settings(max_examples=20)
@given(FACES)
def test_todas_as_faces_aparecem(m: int) -> None:
    contagem = Counter(
        motor.rolar("distribuicao", c, motor.Expressao(1, m)).dados[0] for c in range(1, 60 * m + 1)
    )
    assert sorted(contagem) == list(range(1, m + 1))


@pytest.mark.parametrize("texto", ["1d20+3", "d20", "2d6", "1d8-1", "4D6", " 1d100 + 10 "])
def test_expressoes_validas(texto: str) -> None:
    motor.Expressao.analisar(texto)


@pytest.mark.parametrize("texto", ["", "d7", "0d6", "101d6", "1d20+", "abacaxi", "1d20+1+1"])
def test_expressoes_invalidas(texto: str) -> None:
    with pytest.raises(motor.ExpressaoInvalidaError):
        motor.Expressao.analisar(texto)


def test_vantagem_so_vale_para_um_d20() -> None:
    with pytest.raises(motor.ModoInvalidoError):
        motor.rolar("s", 1, "2d6", "vantagem")


def test_composicao_mostra_cada_parte() -> None:
    r = motor.rolar("s", 7, "1d20+3", modificadores={"proficiência": 2})
    texto = r.composicao()
    assert texto.startswith(f"d20 ({r.dados[0]})")
    assert "+ 3" in texto and "+ 2 proficiência" in texto and texto.endswith(f"= {r.total}")


# ---------------------------------------------------------------- diário


@pytest.fixture
def cv() -> Iterator[sqlite3.Connection]:
    con = campanha.criar()
    con.execute(
        "insert into campanha (id, nome, aventura_id, modulo_versao, semente, classificacao)"
        " values ('cp1','Teste','av-porao',1,'semente-abc','adulto')"
    )
    con.execute("insert into sessao (id, campanha_id, numero) values ('s1','cp1',1)")
    yield con
    con.close()


def test_cem_rolagens_gravadas_sao_reproduzidas_iguais(cv: sqlite3.Connection) -> None:
    for i in range(100):
        rolagens.rolar(cv, "cp1", "s1", "E01", "1d20+3", f"teste {i}", modificadores={"forca": 3})
    comparacoes = rolagens.reproduzir(cv, "cp1")
    assert len(comparacoes) == 100
    assert all(c.igual for c in comparacoes)
    assert [c.contador for c in comparacoes] == list(range(1, 101))


def test_contador_repetido_e_recusado_pelo_banco(cv: sqlite3.Connection) -> None:
    r = rolagens.rolar(cv, "cp1", "s1", "E01", "1d20", "primeira")
    cv.execute(
        "insert into diario (campanha_id, sessao_id, tipo, origem, dados) values ('cp1','s1','rolagem','E01','{}')"
    )
    seq = cv.execute("select max(seq) from diario").fetchone()[0]
    with pytest.raises(sqlite3.IntegrityError, match=r"rolagem.contador"):
        cv.execute(
            "insert into rolagem (seq, campanha_id, contador, expressao, modo, dados, modificadores, total, motivo)"
            " values (?, 'cp1', ?, '1d20', 'normal', '{}', '{}', 1, 'repetida')",
            (seq, r.contador),
        )


def test_rolagem_e_registro_do_diario_entram_juntos(cv: sqlite3.Connection) -> None:
    r = rolagens.rolar(cv, "cp1", "s1", "C05", "2d6+1", "dano da espada")
    (tipo, origem) = cv.execute("select tipo, origem from diario where seq = ?", (r.seq,)).fetchone()
    assert (tipo, origem) == ("rolagem", "C05")
    assert r.total == sum(r.dados) + 1


def test_rolagem_informada_nao_tem_contador_e_nao_entra_na_reproducao(cv: sqlite3.Connection) -> None:
    rolagens.rolar(cv, "cp1", "s1", "E01", "1d20", "do motor")
    inf = rolagens.informar(cv, "cp1", "s1", "E01", "1d20+2", (17,), "dado físico")
    assert inf.informada and inf.contador is None and inf.total == 19
    assert len(rolagens.reproduzir(cv, "cp1")) == 1
    assert inf.composicao.startswith("informada: 17")


def test_rolagem_informada_fora_da_faixa_e_recusada(cv: sqlite3.Connection) -> None:
    with pytest.raises(motor.ExpressaoInvalidaError):
        rolagens.informar(cv, "cp1", "s1", "E01", "1d20", (21,), "impossível")


def test_registro_adulterado_aparece_como_divergencia(cv: sqlite3.Connection) -> None:
    for i in range(5):
        rolagens.rolar(cv, "cp1", "s1", "E01", "1d20", f"teste {i}")
    # O diário não aceita alteração; a única forma de adulterar é trocar a semente da campanha.
    cv.execute("update campanha set semente = 'outra' where id = 'cp1'")
    comparacoes = rolagens.reproduzir(cv, "cp1")
    assert any(not c.igual for c in comparacoes)


def test_reproducao_por_intervalo(cv: sqlite3.Connection) -> None:
    for i in range(10):
        rolagens.rolar(cv, "cp1", "s1", "E01", "1d6", f"teste {i}")
    assert [c.contador for c in rolagens.reproduzir(cv, "cp1", de=4, ate=6)] == [4, 5, 6]


def test_campanha_inexistente(cv: sqlite3.Connection) -> None:
    with pytest.raises(rolagens.CampanhaInexistenteError):
        rolagens.rolar(cv, "nao-existe", None, "E01", "1d20", "x")
