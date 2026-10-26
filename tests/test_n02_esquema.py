"""Card N-02: esquema, migrações e as quinze provas do capítulo 3 do Blueprint.

Critério de aceite: dado um banco vazio, quando a migração roda, então as dezessete
tabelas existem, as quinze provas respondem como no capítulo 3 e a semente está
publicada como versão 1.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from importlib import resources
from pathlib import Path

import pytest

from narrador import banco
from narrador.campanha import banco as campanha
from narrador.modulo import banco as modulo

RAIZ = Path(__file__).resolve().parents[1]


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


@pytest.fixture
def av() -> Iterator[sqlite3.Connection]:
    con = modulo.criar()
    modulo.aplicar_semente(con)
    yield con
    con.close()


def registro(con: sqlite3.Connection, tipo: str, origem: str) -> int:
    con.execute(
        "insert into diario (campanha_id, sessao_id, tipo, origem, dados) values ('cp1','s1',?,?,'{}')",
        (tipo, origem),
    )
    seq = con.execute("select max(seq) from diario").fetchone()[0]
    assert isinstance(seq, int)
    return seq


def recusa(con: sqlite3.Connection, sql: str, params: tuple[object, ...] = ()) -> str:
    with pytest.raises(sqlite3.IntegrityError) as ex:
        con.execute(sql, params)
    return str(ex.value)


# ---------------------------------------------------------------- estrutura


def test_campanha_viva_tem_dez_tabelas_e_dez_gatilhos(cv: sqlite3.Connection) -> None:
    assert len(banco.tabelas(cv)) == 10
    assert len(banco.gatilhos(cv)) == 10


def test_pasta_de_aventuras_tem_sete_tabelas_e_cinco_gatilhos(av: sqlite3.Connection) -> None:
    assert len(banco.tabelas(av)) == 7
    assert len(banco.gatilhos(av)) == 5


def test_migracao_roda_uma_vez_e_e_idempotente() -> None:
    con = campanha.criar()
    assert banco.migrar(con, banco.migracoes_do_pacote("narrador.campanha")) == []
    assert [v for (v,) in con.execute("select versao from migracao")] == [1]
    con.close()


def test_sql_do_pacote_e_o_mesmo_do_documento() -> None:
    pares = [
        ("narrador.campanha", "migracoes/0001_campanha_viva.sql", "campanha.sql"),
        ("narrador.modulo", "migracoes/0001_pasta_de_aventuras.sql", "aventura.sql"),
        ("narrador.modulo", "semente/porao_da_taverna.sql", "semente.sql"),
    ]
    for pacote, no_pacote, no_documento in pares:
        a = (resources.files(pacote) / no_pacote).read_text(encoding="utf-8")
        b = (RAIZ / "docs" / "fonte" / "esquema" / no_documento).read_text(encoding="utf-8")
        assert a == b, f"{no_pacote} divergiu do documento ({no_documento})"


# ---------------------------------------------------------------- provas da campanha viva


def test_prova_01_diario_nao_aceita_alteracao(cv: sqlite3.Connection) -> None:
    seq = registro(cv, "rolagem", "E01")
    assert "diario_somente_insercao" in recusa(
        cv, "update diario set dados = '{\"x\":1}' where seq = ?", (seq,)
    )


def test_prova_02_diario_nao_aceita_exclusao(cv: sqlite3.Connection) -> None:
    seq = registro(cv, "rolagem", "E01")
    assert "diario_somente_insercao" in recusa(cv, "delete from diario where seq = ?", (seq,))


def test_prova_03_contador_de_rolagem_e_unico_na_campanha(cv: sqlite3.Connection) -> None:
    s1, s2 = registro(cv, "rolagem", "E01"), registro(cv, "rolagem", "E01")
    cv.execute(
        "insert into rolagem (seq, campanha_id, contador, expressao, modo, dados, modificadores, total, motivo)"
        " values (?, 'cp1', 1, '1d20+3', 'normal', '[14]', '{\"destreza\":3}', 17, 'teste de Atletismo')",
        (s1,),
    )
    erro = recusa(
        cv,
        "insert into rolagem (seq, campanha_id, contador, expressao, modo, dados, modificadores, total, motivo)"
        " values (?, 'cp1', 1, '1d20', 'normal', '[9]', '{}', 9, 'repetida')",
        (s2,),
    )
    assert "rolagem.contador" in erro


def test_prova_04_rolagem_informada_em_dado_fisico_nao_tem_contador(cv: sqlite3.Connection) -> None:
    seq = registro(cv, "rolagem", "E01")
    cv.execute(
        "insert into rolagem (seq, campanha_id, contador, expressao, modo, dados, modificadores, total, motivo, informada)"
        " values (?, 'cp1', null, '1d20', 'normal', '[9]', '{}', 9, 'dado físico', 1)",
        (seq,),
    )
    assert cv.execute("select informada from rolagem where seq = ?", (seq,)).fetchone() == (1,)


def _desvio(cv: sqlite3.Connection) -> int:
    seq = registro(cv, "desvio", "F02")
    cv.execute(
        "insert into desvio (seq, campanha_id, o_que_mudou, motivo, regra)"
        " values (?, 'cp1', 'taverneiro foge', 'reação do jogador', 'RN-02')",
        (seq,),
    )
    return seq


def test_prova_05_desvio_aceita_a_marca_de_revisao(cv: sqlite3.Connection) -> None:
    seq = _desvio(cv)
    cv.execute("update desvio set revisado = 1 where seq = ?", (seq,))
    assert cv.execute("select revisado from desvio where seq = ?", (seq,)).fetchone() == (1,)


def test_prova_06_desvio_nao_aceita_reescrever_o_motivo(cv: sqlite3.Connection) -> None:
    seq = _desvio(cv)
    assert "desvio_so_marca_de_revisao" in recusa(
        cv, "update desvio set motivo = 'outro' where seq = ?", (seq,)
    )


def test_prova_07_campanha_exige_semente_de_rolagens(cv: sqlite3.Connection) -> None:
    erro = recusa(
        cv,
        "insert into campanha (id, nome, aventura_id, modulo_versao, semente, classificacao)"
        " values ('cp2','x','av',1,null,'livre')",
    )
    assert "campanha.semente" in erro


def test_prova_08_dificuldade_fora_da_escala_do_srd_e_recusada(cv: sqlite3.Connection) -> None:
    seq = registro(cv, "veredito", "C05")
    erro = recusa(
        cv,
        "insert into veredito (seq, campanha_id, situacao, tipo, pericia, dificuldade)"
        " values (?, 'cp1', 'escalar o muro', 'teste', 'Atletismo', 45)",
        (seq,),
    )
    assert "dificuldade" in erro


# ---------------------------------------------------------------- provas da pasta de aventuras


def test_prova_09_semente_publicada_como_versao_1(av: sqlite3.Connection) -> None:
    itens = av.execute(
        "select count(*) from item_canonico where aventura_id='av-porao' and versao=1"
    ).fetchone()
    ligacoes = av.execute("select count(*) from ligacao where aventura_id='av-porao' and versao=1").fetchone()
    publicada = av.execute(
        "select publicada_em from modulo_versao where aventura_id='av-porao' and versao=1"
    ).fetchone()
    assert itens == (10,) and ligacoes == (5,)
    assert publicada is not None and publicada[0] is not None


def test_prova_10_versao_publicada_nao_aceita_alteracao(av: sqlite3.Connection) -> None:
    assert "versao_publicada_imutavel" in recusa(
        av, "update item_canonico set nome = 'x' where id = 'cena-porao' and versao = 1"
    )


def test_prova_11_versao_publicada_nao_aceita_cena_nova(av: sqlite3.Connection) -> None:
    erro = recusa(
        av,
        "insert into item_canonico (id, aventura_id, versao, tipo, nome, dados)"
        " values ('cena-nova','av-porao',1,'cena','Nova','{}')",
    )
    assert "versao_publicada_imutavel" in erro


def test_prova_12_segredo_exige_condicao_de_descoberta(av: sqlite3.Connection) -> None:
    av.execute(
        "insert into modulo_versao (aventura_id, versao, origem, impressao_texto) values ('av-porao', 2, 'importado', 'sha256:v2')"
    )
    erro = recusa(
        av,
        "insert into item_canonico (id, aventura_id, versao, tipo, nome, dados, segredo)"
        " values ('seg-x','av-porao',2,'segredo','Sem condição','{}',1)",
    )
    assert "condicao_descoberta" in erro


def test_prova_13_rascunho_aceita_cena_nova(av: sqlite3.Connection) -> None:
    av.execute(
        "insert into modulo_versao (aventura_id, versao, origem, impressao_texto) values ('av-porao', 2, 'importado', 'sha256:v2')"
    )
    av.execute(
        "insert into item_canonico (id, aventura_id, versao, tipo, nome, dados) values ('cena-nova','av-porao',2,'cena','Nova','{}')"
    )
    assert av.execute("select count(*) from item_canonico where versao = 2").fetchone() == (1,)


def test_prova_14_mapeamento_sem_srd_sem_ficha_e_sem_pendente_e_recusado(av: sqlite3.Connection) -> None:
    av.execute(
        "insert into modulo_versao (aventura_id, versao, origem, impressao_texto) values ('av-porao', 2, 'importado', 'sha256:v2')"
    )
    av.execute(
        "insert into item_canonico (id, aventura_id, versao, tipo, nome, dados) values ('cri-x','av-porao',2,'criatura','X','{}')"
    )
    erro = recusa(
        av,
        "insert into mapeamento_srd (aventura_id, versao, item_id, srd_versao) values ('av-porao', 2, 'cri-x', '5.2.1')",
    )
    assert "pendente" in erro


def test_prova_15_caminho_critico_da_semente(av: sqlite3.Connection) -> None:
    caminho = av.execute(
        """
        with recursive passo(item, n) as (
          select 'cena-taverna', 0
          union all
          select l.para_item, n + 1 from ligacao l join passo p on l.de_item = p.item
          where l.aventura_id = 'av-porao' and l.versao = 1 and l.caminho_critico = 1 and n < 20)
        select group_concat(item, ' -> ') from passo
        """
    ).fetchone()
    assert caminho == ("cena-taverna -> cena-porao -> cena-tunel",)


# ---------------------------------------------------------------- arquivo em disco


def test_arquivo_em_disco_sobrevive_a_reabertura(tmp_path: Path) -> None:
    caminho = tmp_path / "porao.sqlite"
    con = modulo.criar(caminho)
    modulo.aplicar_semente(con)
    con.close()
    con2 = modulo.criar(caminho)  # reabrir não reaplica a migração nem perde a semente
    assert con2.execute("select count(*) from item_canonico").fetchone() == (10,)
    assert [v for (v,) in con2.execute("select versao from migracao")] == [1]
    con2.close()
