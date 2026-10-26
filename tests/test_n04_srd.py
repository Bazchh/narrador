"""Card N-04: SRD, carregador e as fichas do esqueleto.

Critério de aceite: dado o subconjunto carregado, quando o motor pede o rato gigante por
nome em português, então recebe a ficha com classe de armadura, pontos de vida, ataque e
a página do PDF, e a atribuição aparece na tela "sobre".
"""

from __future__ import annotations

import hashlib
import re
import warnings
from pathlib import Path

import pytest

from narrador.cli import principal
from narrador.srd import atribuicao, catalogo
from narrador.srd.modelo import VERSAO_SRD, Criatura

RAIZ = Path(__file__).resolve().parents[1]
PDF = RAIZ / "dados" / "srd" / "SRD_CC_v5.2.1.pdf"


def test_rato_gigante_por_nome_em_portugues() -> None:
    rato = catalogo.criatura("Rato gigante")
    assert rato.nome == "Giant Rat"
    assert rato.classe_armadura == 13 and rato.pontos_de_vida == 7 and rato.dados_de_vida == "2d6"
    assert rato.atributos == {"str": 7, "dex": 16, "con": 11, "int": 2, "wis": 10, "cha": 4}
    mordida = rato.ataques[0]
    assert (mordida.nome, mordida.bonus, mordida.dano_dados, mordida.dano_tipo) == (
        "Bite",
        5,
        "1d4+3",
        "perfurante",
    )
    assert rato.tracos[0].nome == "Pack Tactics"
    assert rato.pagina >= 1


def test_busca_sem_acento_e_em_ingles() -> None:
    assert catalogo.buscar("criatura", "rato GIGANTE").exato
    assert catalogo.buscar("criatura", "giant rat").exato
    assert catalogo.buscar("criatura", "srd:criatura:giant-rat").exato


def test_busca_aproximada_devolve_o_unico_candidato() -> None:
    r = catalogo.buscar("criatura", "rato gigant")
    assert not r.exato and r.registro.nome == "Giant Rat"


def test_fora_do_srd_nao_inventa() -> None:
    with pytest.raises(catalogo.ForaDoSrdError):
        catalogo.criatura("Beholder")
    with pytest.raises(catalogo.ForaDoSrdError):
        catalogo.arma("sabre de luz")


def test_fora_do_srd_lista_parecidos_quando_ambiguo() -> None:
    with pytest.raises(catalogo.ForaDoSrdError) as ex:
        catalogo.buscar("arma", "machado", limiar=0.5)
    assert len(ex.value.candidatos) >= 2


def test_subconjunto_do_esqueleto_esta_completo() -> None:
    srd = catalogo.carregar()
    assert (
        len(srd.armas) == 38
        and len(srd.armaduras) == 13
        and len(srd.pericias) == 18
        and len(srd.condicoes) == 15
    )
    assert [c.nome for c in srd.classes] == ["Fighter"] and [e.nome for e in srd.especies] == ["Human"]
    assert srd.versao == VERSAO_SRD


def test_todo_registro_aponta_para_uma_pagina_do_pdf() -> None:
    srd = catalogo.carregar()
    for r in catalogo.todos(srd):
        assert 1 <= r.pagina <= srd.paginas_pdf, r.id
        assert r.nome and r.nome_pt, r.id


def test_fichas_do_esqueleto() -> None:
    cota = catalogo.armadura("Cota de malha")
    assert (cota.classe_armadura_base, cota.soma_destreza, cota.categoria, cota.forca_minima) == (
        16,
        False,
        "pesada",
        13,
    )
    escudo = catalogo.armadura("Escudo")
    assert escudo.classe_armadura_base == 2 and escudo.categoria == "escudo"
    espada = catalogo.arma("Espada longa")
    assert (
        espada.dano_dados == "1d8"
        and espada.dano_tipo == "cortante"
        and not espada.simples
        and "Versatile" in espada.propriedades
    )
    assert catalogo.pericia("Atletismo").atributo == "str"
    assert catalogo.condicao("Caído").nome == "Prone"
    guerreiro = catalogo.classe("Guerreiro")
    assert guerreiro.dado_de_vida == "d10" and guerreiro.salvaguardas == ["con", "str"]
    assert {t.nome for t in guerreiro.tracos_nivel_1} == {"Fighting Style", "Second Wind", "Weapon Mastery"}
    humano = catalogo.especie("Humano")
    assert humano.velocidade_pes == 30 and any(t.nome == "Resourceful" for t in humano.tracos)


def test_criatura_e_imutavel() -> None:
    rato = catalogo.criatura("Rato gigante")
    assert isinstance(rato, Criatura)
    with pytest.raises(Exception, match="frozen"):
        rato.pontos_de_vida = 99  # type: ignore[misc]


def test_tela_sobre_mostra_a_atribuicao(capsys: pytest.CaptureFixture[str]) -> None:
    assert principal(["sobre"]) == 0
    saida = capsys.readouterr().out
    assert atribuicao.ATRIBUICAO in saida and VERSAO_SRD in saida


def test_atribuicao_e_a_do_pdf_oficial() -> None:
    pymupdf = pytest.importorskip("pymupdf")
    srd = catalogo.carregar()
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == srd.pdf_sha256
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        doc = pymupdf.open(str(PDF))
    assert doc.page_count == srd.paginas_pdf
    # O PDF quebra a linha no meio do endereço da licença; compara-se sem espaços.
    sem_espacos = re.compile(r"\s+")
    assert sem_espacos.sub("", atribuicao.ATRIBUICAO) in sem_espacos.sub("", doc[0].get_text())
