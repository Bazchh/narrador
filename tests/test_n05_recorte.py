"""Card N-05: módulo canônico, consulta e recorte da cena.

Critério de aceite: dada a semente publicada, quando o motor pede o recorte da cena do
porão, então recebe descrição, encontro com dois ratos, a ligação para o túnel, e o
segredo do anel vem separado e marcado.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from narrador.modulo import banco as modulo_banco
from narrador.modulo import canonico


@pytest.fixture
def av() -> Iterator[sqlite3.Connection]:
    con = modulo_banco.criar()
    modulo_banco.aplicar_semente(con)
    yield con
    con.close()


@pytest.fixture
def modulo(av: sqlite3.Connection) -> canonico.ModuloCanonico:
    return canonico.carregar(av, "av-porao", 1)


def test_recorte_do_porao(modulo: canonico.ModuloCanonico) -> None:
    r = canonico.recortar(modulo, "cena-porao")
    assert "barris roídos" in r.cena.dados["descricao"]
    assert [p.item.nome for p in r.presentes] == ["Rato gigante", "Rato gigante"]
    assert all(p.mapeamento and p.mapeamento.srd_id == "srd:creature:giant-rat" for p in r.presentes)
    assert [li.para for li in r.ligacoes_saida if li.tipo == "leva_a"] == ["cena-tunel"]
    assert r.no_caminho_critico
    assert [s.item.id for s in r.segredos] == ["seg-anel"]
    assert r.segredos[0].marca == canonico.NAO_NARRAR
    assert "marcas de ferramenta" in r.segredos[0].condicao_descoberta


def test_segredo_nunca_entra_no_narravel(modulo: canonico.ModuloCanonico) -> None:
    r = canonico.recortar(modulo, "cena-porao")
    texto = str(r.narravel())
    assert "seg-anel" not in texto and "contrabandista" not in texto


def test_segredo_descoberto_sai_da_lista(modulo: canonico.ModuloCanonico) -> None:
    r = canonico.recortar(modulo, "cena-tunel", segredos_descobertos={"seg-anel"})
    assert r.segredos == []


def test_segredo_ligado_a_cena_e_marcado_como_tal(modulo: canonico.ModuloCanonico) -> None:
    taverna = canonico.recortar(modulo, "cena-taverna")
    assert [p.item.id for p in taverna.presentes] == ["np-taverneiro"]
    assert taverna.segredos[0].ligado_a_cena  # o taverneiro sabe do anel
    porao = canonico.recortar(modulo, "cena-porao")
    assert not porao.segredos[0].ligado_a_cena


def test_fatos_da_campanha_viva_entram_por_cima_do_canonico(modulo: canonico.ModuloCanonico) -> None:
    r = canonico.recortar(
        modulo,
        "cena-porao",
        fatos_por_item={
            "cena-porao": ["a porta do alçapão está aberta"],
            "cri-rato-1": ["morto na sessão 1"],
        },
    )
    assert r.fatos_da_cena == ["a porta do alçapão está aberta"]
    assert r.presentes[0].fatos == ["morto na sessão 1"]
    assert r.narravel()["presentes"][0]["fatos"] == ["morto na sessão 1"]


def test_itens_e_ganchos(modulo: canonico.ModuloCanonico) -> None:
    tunel = canonico.recortar(modulo, "cena-tunel")
    assert [i.item.id for i in tunel.itens] == ["it-anel"]
    taverna = canonico.recortar(modulo, "cena-taverna")
    assert [g.id for g in taverna.ganchos] == ["gancho-barulho"]


def test_cena_inexistente_devolve_vizinhas(modulo: canonico.ModuloCanonico) -> None:
    with pytest.raises(canonico.CenaInexistenteError) as ex:
        canonico.recortar(modulo, "cena-sotao", cena_atual="cena-porao")
    assert {v.id for v in ex.value.vizinhas} == {"cena-tunel", "cena-taverna"}
    with pytest.raises(canonico.CenaInexistenteError) as ex2:
        canonico.recortar(modulo, "cena-sotao")
    assert {v.id for v in ex2.value.vizinhas} == {"cena-taverna", "cena-porao", "cena-tunel"}


def test_caminho_critico(modulo: canonico.ModuloCanonico) -> None:
    assert modulo.caminho_critico("cena-taverna") == ["cena-taverna", "cena-porao", "cena-tunel"]


def test_rascunho_nao_e_carregavel(av: sqlite3.Connection) -> None:
    av.execute(
        "insert into modulo_versao (aventura_id, versao, origem, impressao_texto) values ('av-porao', 2, 'importado', 'x')"
    )
    with pytest.raises(canonico.ModuloNaoPublicadoError):
        canonico.carregar(av, "av-porao", 2)
    with pytest.raises(canonico.ModuloNaoPublicadoError):
        canonico.carregar(av, "av-porao", 9)


def test_modulo_carregado_e_imutavel(modulo: canonico.ModuloCanonico) -> None:
    with pytest.raises(Exception, match="frozen"):
        modulo.versao = 2  # type: ignore[misc]
