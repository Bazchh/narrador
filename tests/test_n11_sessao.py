"""Card N-11: sessão: abrir, encerrar, retomar.

Critério de aceite: dada uma sessão em combate com um ataque resolvido e narração pendente,
quando o processo é morto e a campanha reaberta, então a sessão retoma em combate na mesma
rodada, a narração pendente é gerada e o diário não tem rolagem repetida.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from narrador.campanha import banco as campanha_banco
from narrador.campanha import combate as campanha_combate
from narrador.campanha import rolagens, sessoes
from narrador.mestre import mesa as mesa_mod
from narrador.mestre import servico
from narrador.modulo import banco as modulo_banco
from narrador.motor import combate as motor_combate
from narrador.motor import ficha as motor_ficha
from narrador.motor import sessao as motor_sessao


@pytest.fixture
def pastas(tmp_path: Path) -> tuple[Path, Path]:
    aventura = tmp_path / "aventuras" / "porao.sqlite"
    aventura.parent.mkdir()
    con = modulo_banco.criar(aventura)
    modulo_banco.aplicar_semente(con)
    con.close()
    criada = sessoes.criar_campanha(
        tmp_path / "campanhas", "O Porão", "av-porao", 1, motor_ficha.pre_gerados()[0], "cena-porao"
    )
    return criada.caminho, aventura


def abrir(pastas: tuple[Path, Path]) -> mesa_mod.Mesa:
    m = mesa_mod.Mesa(*pastas)
    m.abrir()
    return m


def narrar(texto: str) -> list[servico.Passo]:
    return [servico.Passo("narrar", {"texto": texto})]


# ---------------------------------------------------------------- aceite


def test_retomada_no_meio_do_combate_sem_rolagem_repetida(pastas: tuple[Path, Path]) -> None:
    m = abrir(pastas)
    assert m.estado == "em_cena" and m.sessao is not None and m.sessao.numero == 1
    # o mestre inicia o combate e narra
    turno = m.rodar_turno(
        "entro no porão",
        servico.ServicoFalso(
            [
                [
                    servico.Passo(
                        "iniciar_combate",
                        {
                            "participantes": [
                                {"id": "cri-rato-1", "zona": "perto"},
                                {"id": "cri-rato-2", "zona": "perto"},
                            ],
                            "situacao": "ratos!",
                        },
                    ),
                    *narrar("Dois ratos saltam dos barris."),
                ]
            ]
        ),
    )
    assert turno.falha is None and m.estado == "em_combate"
    combate = m.combate_atual()
    assert combate is not None
    # o jogador resolve um ataque pela plataforma; a narração fica pendente
    while combate.estado != "turno_pj":
        combate = motor_combate.encerrar_turno(combate)
    rolar = campanha_combate.rolador(m.con, m.campanha_id, m.sessao.sessao_id, "D02")
    alvo = next(h for h in combate.hostis() if not h.fora)
    combate = motor_combate.agir(
        combate,
        m.sessao.instantaneo.personagem_id or "",
        motor_combate.Declaracao("atacar", alvo=alvo.id),
        rolar,
    )
    campanha_combate.gravar(m.con, m.campanha_id, m.sessao.sessao_id, combate, "D02")
    rodada = combate.rodada
    rolagens_antes = [(r.contador, r.total) for r in rolagens.listar(m.con, m.campanha_id)]
    # o processo morre: conexões somem sem encerrar a sessão, e a trava fica com um pid morto
    m.con.close()
    m.con_aventura.close()
    m.trava.caminho.write_text(json.dumps({"pid": 999999}), encoding="utf-8")

    m2 = abrir(pastas)
    assert m2.sessao is not None and m2.sessao.retomada_de is not None and m2.sessao.numero == 2
    assert m2.estado == "em_combate" and m2.sessao.em_combate and m2.sessao.narracao_pendente
    retomado = m2.combate_atual()
    assert retomado is not None and retomado.rodada == rodada and retomado == combate
    turno2 = m2.rodar_turno(
        "continuar", servico.ServicoFalso([narrar("Sua espada atravessa o rato; o outro recua guinchando.")])
    )
    assert turno2.narracao is not None and turno2.falha is None
    depois = [(r.contador, r.total) for r in rolagens.listar(m2.con, m2.campanha_id)]
    assert depois == rolagens_antes  # nada foi rolado de novo
    assert all(c.igual for c in rolagens.reproduzir(m2.con, m2.campanha_id))
    sessoes_registradas = m2.con.execute("select numero, motivo_fim from sessao order by numero").fetchall()
    assert sessoes_registradas == [(1, "interrompida"), (2, None)]
    m2.encerrar()
    assert m2.estado == "fechada"


# ---------------------------------------------------------------- máquina de estados


def test_tabela_de_transicoes_da_sessao_inteira() -> None:
    for (estado, evento), destino in motor_sessao.TRANSICOES.items():
        assert motor_sessao.transicao(estado, evento) == destino
    for estado in motor_sessao.ESTADOS:
        eventos_validos = {ev for (e, ev) in motor_sessao.TRANSICOES if e == estado}
        for evento in {ev for (_, ev) in motor_sessao.TRANSICOES} - eventos_validos:
            with pytest.raises(motor_sessao.TransicaoInvalidaError):
                motor_sessao.transicao(estado, evento)


def test_nao_da_para_jogar_fora_de_cena_ou_combate(pastas: tuple[Path, Path]) -> None:
    m = mesa_mod.Mesa(*pastas)
    with pytest.raises(motor_sessao.TransicaoInvalidaError):
        m.rodar_turno("olá", servico.ServicoFalso([]))


# ---------------------------------------------------------------- campanha, trava, instantâneo


def test_criar_campanha_gera_semente_e_primeiro_registro(pastas: tuple[Path, Path]) -> None:
    caminho, _ = pastas
    con = campanha_banco.criar(caminho)
    (semente, classificacao) = con.execute("select semente, classificacao from campanha").fetchone()
    assert len(semente) == 32 and classificacao == "adulto"
    eventos = [
        json.loads(d)["evento"]
        for (d,) in con.execute("select dados from diario where tipo = 'sessao' order by seq")
    ]
    assert eventos == ["campanha criada"]
    inst = sessoes.ultimo_instantaneo(con, sessoes.campanha_unica(con))
    assert inst is not None and inst.cena_atual == "cena-porao" and inst.sessao_numero == 0
    con.close()
    with pytest.raises(FileExistsError):
        sessoes.criar_campanha(
            caminho.parent, "O Porão", "av-porao", 1, motor_ficha.pre_gerados()[0], "cena-porao"
        )


def test_segunda_abertura_da_mesma_campanha_e_recusada(pastas: tuple[Path, Path]) -> None:
    m = abrir(pastas)
    trava = sessoes.Trava(pastas[0])
    assert json.loads(trava.caminho.read_text(encoding="utf-8"))["pid"] == os.getpid()
    # outro processo vivo segurando a trava: simulado com o nosso próprio pid gravado por "outro"
    with pytest.raises(sessoes.CampanhaTravadaError):
        _simular_outro_processo(trava)
    m.encerrar()
    assert not trava.caminho.exists()


def _simular_outro_processo(trava: sessoes.Trava) -> None:
    original = sessoes._processo_vivo
    sessoes._processo_vivo = lambda pid: True  # type: ignore[assignment]
    try:
        trava.caminho.write_text(json.dumps({"pid": 123456}), encoding="utf-8")
        trava.adquirir()
    finally:
        sessoes._processo_vivo = original  # type: ignore[assignment]


def test_abrir_e_encerrar_registram_e_ir_para_muda_a_cena(pastas: tuple[Path, Path]) -> None:
    m = abrir(pastas)
    m.ir_para("cena-tunel", minutos=10)
    assert (
        m.sessao is not None
        and m.sessao.instantaneo.cena_atual == "cena-tunel"
        and m.sessao.instantaneo.relogio_minutos == 10
    )
    m.encerrar(pendencias=["subida de nível"])
    con = campanha_banco.criar(pastas[0])
    eventos = [
        json.loads(d) for (d,) in con.execute("select dados from diario where tipo = 'sessao' order by seq")
    ]
    assert [e["evento"] for e in eventos] == [
        "campanha criada",
        "sessão aberta",
        "cena atual",
        "sessão encerrada",
    ]
    assert eventos[-1]["pendencias"] == ["subida de nível", "resumo da sessão"]
    assert con.execute("select motivo_fim from sessao").fetchone() == ("encerrada",)
    con.close()


def test_instantaneo_inconsistente_abre_em_so_leitura(pastas: tuple[Path, Path]) -> None:
    con = campanha_banco.criar(pastas[0])
    cid = sessoes.campanha_unica(con)
    sessoes.gravar_instantaneo(con, cid, sessoes.Instantaneo(9999, "cena-porao", 0, None, 0))
    con.close()
    m = mesa_mod.Mesa(*pastas)
    with pytest.raises(sessoes.CampanhaInconsistenteError):
        m.abrir()
    assert m.estado == "so_leitura"
    assert not sessoes.Trava(pastas[0]).caminho.exists()


def test_falha_do_servico_pausa_a_mesa_e_o_servico_volta(pastas: tuple[Path, Path]) -> None:
    m = abrir(pastas)
    fora = servico.ServicoFalso([[servico.Passo(falha=servico.Falha("indisponivel", "tempo esgotado"))]] * 2)
    assert m.rodar_turno("olho em volta", fora).falha is not None
    assert m.estado == "em_cena"
    assert m.rodar_turno("olho em volta", fora).falha is not None
    assert m.estado == "pausada"
    assert m.texto_literal().startswith("Escuro, úmido")
    m.retomar_servico()
    assert m.estado == "em_cena"
    ok = m.rodar_turno("olho em volta", servico.ServicoFalso([narrar("Barris, umidade e olhos vermelhos.")]))
    assert ok.narracao is not None
    m.encerrar()
