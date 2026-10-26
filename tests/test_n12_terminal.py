"""Card N-12: o terminal: a primeira sessão jogável.

Critério de aceite: dada a semente e o provedor falso, quando o roteiro de aceite roda
no terminal, então a sessão vai da taverna ao túnel sem travar, com o anel recuperado,
e o diário mostra cada veredito e rolagem.

O roteiro cobre cena, pergunta, tentativa, combate, queda do programa e retomada. A
semente de dados é fixa para o roteiro ser o mesmo a cada execução.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from textual.widgets import Input, Static

from narrador.campanha import banco as campanha_banco
from narrador.campanha import fatos, rolagens, vereditos
from narrador.cli import principal
from narrador.mestre import jogo as jogo_mod
from narrador.mestre import servico
from narrador.mestre.jogo import Jogo, Mensagem, interpretar_declaracao
from narrador.mestre.protocolo import CODIGOS_DE_ERRO, Ferramenta
from narrador.mestre.roteiros import RoteiroDoPorao
from narrador.modulo import banco as modulo_banco
from narrador.motor import combate as motor_combate
from narrador.terminal import Terminal, texto_da_barra, texto_do_painel_de_combate

SEMENTE = "aceite-n12-2"  # com esta semente a guerreira toma dano, sobrevive e o combate dura seis rodadas


@pytest.fixture
def pastas(tmp_path: Path) -> tuple[Path, Path]:
    aventura = tmp_path / "aventuras" / "porao.sqlite"
    aventura.parent.mkdir()
    con = modulo_banco.criar(aventura)
    modulo_banco.aplicar_semente(con)
    con.close()
    criada = jogo_mod.criar_campanha_da_semente(tmp_path / "campanhas", "O Porão", SEMENTE)
    return criada.caminho, aventura


def abrir(
    pastas: tuple[Path, Path], mestre: servico.ServicoDeLinguagem | None = None
) -> tuple[Jogo, list[Mensagem]]:
    j = Jogo(*pastas, mestre or RoteiroDoPorao())
    return j, j.abrir()


def textos(msgs: Sequence[Mensagem], tipo: str | None = None) -> list[str]:
    return [m.texto for m in msgs if tipo is None or m.tipo == tipo]


def sem_codigo_cru(msgs: Sequence[Mensagem]) -> None:
    for m in msgs:
        for codigo in CODIGOS_DE_ERRO:
            assert codigo not in m.texto, f"código cru na tela: {codigo} em {m.texto!r}"


# ---------------------------------------------------------------- aceite


def test_roteiro_de_aceite_da_taverna_ao_tunel_com_queda_e_retomada(pastas: tuple[Path, Path]) -> None:
    jogo, abertura = abrir(pastas)
    tela: list[Mensagem] = list(abertura)
    assert textos(abertura, "sistema") == ["Sessão 1 aberta."]
    assert any("Taverna do Cavalo Manco" in t for t in textos(abertura, "narracao"))
    con = jogo.mesa.con
    cid = jogo.mesa.campanha_id

    # pergunta não é ação (RN-11): resposta sem dado e sem fato
    r = jogo.entrada("posso falar com o taverneiro?")
    tela += r
    assert textos(r, "mestre") and not rolagens.listar(con, cid)
    assert vereditos.listar(con, cid)[-1].pergunta is True
    assert not fatos.listar(con, cid)

    # conversa: fato de conhecimento gravado
    tela += jogo.entrada("falo com o taverneiro sobre o barulho")
    assert any(f.referencia == "np-taverneiro" and f.tipo == "conhecimento" for f in fatos.listar(con, cid))

    # tentativa: veredito de teste com rolagem no diário
    r = jogo.entrada("pressiono o taverneiro sobre o anel")
    tela += r
    assert any(t.startswith("Persuasão") for t in textos(r, "rolagem"))
    ultimo = vereditos.listar(con, cid)[-1]
    assert ultimo.tipo == "teste" and ultimo.rolagem_seq is not None

    # deslocamento pela plataforma (C07) e combate aberto pelo mestre (D01)
    r = jogo.entrada("desço ao porão")
    tela += r
    assert jogo.mesa.sessao is not None and jogo.mesa.sessao.instantaneo.cena_atual == "cena-porao"
    assert jogo.mesa.estado == "em_combate" and any("Combate!" in t for t in textos(r, "combate"))
    assert jogo.painel().em_combate and jogo.painel().rodada == 1

    # a declaração do jogador (D02) e os turnos das criaturas (D03)
    r = jogo.entrada("ataco o rato")
    tela += r
    assert any("Espada longa contra Rato gigante" in t for t in textos(r, "combate"))
    assert jogo.mesa.estado == "em_combate"
    sessao_1 = jogo.mesa.sessao.sessao_id
    rolagens_antes = [(x.contador, x.total) for x in rolagens.listar(con, cid)]

    # queda do programa no meio do combate: conexões somem sem encerrar, trava com pid morto
    jogo.mesa.con.close()
    jogo.mesa.con_aventura.close()
    jogo.mesa.trava.caminho.write_text(json.dumps({"pid": 999999}), encoding="utf-8")

    # retomada (C02, F05): mesma rodada, nada rolado de novo
    jogo2, retomada = abrir(pastas)
    tela += retomada
    assert retomada[0].texto.startswith("Sessão 2 retomada")
    assert jogo2.mesa.estado == "em_combate" and jogo2.mesa.sessao is not None
    assert jogo2.mesa.sessao.retomada_de == sessao_1
    con2, cid2 = jogo2.mesa.con, jogo2.mesa.campanha_id
    assert [(x.contador, x.total) for x in rolagens.listar(con2, cid2)] == rolagens_antes

    for _ in range(30):
        if jogo2.mesa.estado != "em_combate":
            break
        tela += jogo2.entrada("ataco o rato")
    assert jogo2.mesa.estado == "em_cena"
    assert any(t.startswith("Fim do combate: 50 pontos") for t in textos(tela, "combate"))
    inst = jogo2.mesa.sessao.instantaneo
    assert inst.pontos_de_vida is not None and 0 < inst.pontos_de_vida < 12  # tomou dano e sobreviveu
    assert not jogo2.painel().em_combate

    # exploração, túnel e o anel
    r = jogo2.entrada("examino os barris")
    tela += r
    assert any(t.startswith("Investigação") for t in textos(r, "rolagem"))
    tela += jogo2.entrada("sigo pelo túnel")
    assert jogo2.mesa.sessao.instantaneo.cena_atual == "cena-tunel"
    tela += jogo2.entrada("pego o anel")
    assert any(f.referencia == "it-anel" and f.tipo == "posse" for f in fatos.listar(con2, cid2))

    # encerramento com a linha de custo e tempo
    fim = jogo2.entrada("/sair")
    tela += fim
    assert jogo2.encerrado and fim[0].texto.startswith("Sessão encerrada.") and "sem custo" in fim[0].texto
    assert jogo2.entrada("ataco") == []

    # o diário mostra cada veredito e rolagem, e nenhuma rolagem se perdeu
    con3 = campanha_banco.criar(pastas[0])
    todos_vereditos = vereditos.listar(con3, cid2)
    assert len(todos_vereditos) == 4  # pergunta, persuasão, investigação, anel
    assert all(v.rolagem_seq is not None for v in todos_vereditos if v.tipo == "teste")
    assert len(rolagens.listar(con3, cid2)) == 24
    assert all(c.igual for c in rolagens.reproduzir(con3, cid2))
    assert con3.execute("select numero, motivo_fim from sessao order by numero").fetchall() == [
        (1, "interrompida"),
        (2, "encerrada"),
    ]
    con3.close()
    sem_codigo_cru(tela)


# ---------------------------------------------------------------- recusas, pausa, comandos


def test_recusas_em_linguagem_de_jogador(pastas: tuple[Path, Path]) -> None:
    jogo, _ = abrir(pastas)
    jogo.entrada("desço ao porão")
    assert jogo.mesa.estado == "em_combate"
    r = jogo.entrada("canto uma canção para os ratos")
    assert r[0].tipo == "recusa" and "ataco <alvo>" in r[0].texto
    r = jogo.entrada("/ir túnel")
    assert r[0].tipo == "recusa" and "Em combate" in r[0].texto
    assert jogo.entrada("me aproximo do rato")[-1].texto == "Ainda é o seu turno."
    r = jogo.entrada("me afasto do rato")
    assert r[0].tipo == "recusa" and r[0].texto.startswith(
        "As regras não permitem isso agora: movimento já usado"
    )
    sem_codigo_cru(r)
    jogo.encerrar()


class _MestreInstavel:
    """Cai N vezes e depois entrega ao roteiro."""

    nome = "instável"

    def __init__(self, falhas: int) -> None:
        self.falhas = falhas
        self.roteiro = RoteiroDoPorao()

    def rodar_turno(
        self, contexto: servico.ContextoDoTurno, ferramentas: Sequence[Ferramenta], executar: servico.Executar
    ) -> servico.Turno:
        if self.falhas > 0:
            self.falhas -= 1
            return servico.Turno(None, (), servico.Falha("indisponivel", "tempo esgotado"), servico.Uso())
        return self.roteiro.rodar_turno(contexto, ferramentas, executar)


def test_mesa_pausa_quando_o_mestre_cai_e_segue_quando_volta(pastas: tuple[Path, Path]) -> None:
    jogo, abertura = abrir(pastas, _MestreInstavel(2))
    assert any(t.startswith("Falha: o mestre não respondeu") for t in textos(abertura, "sistema"))
    assert jogo.mesa.estado == "em_cena"
    r = jogo.entrada("olho em volta")
    assert jogo.mesa.estado == "pausada" and jogo.painel().estado == "pausada"
    assert any("Mesa pausada" in t and "Mesas vazias" in t for t in textos(r, "sistema"))
    r = jogo.entrada("olho em volta")
    assert r[0].texto == "Tentando o mestre de novo." and textos(r, "narracao")
    assert jogo.mesa.estado == "em_cena"
    fim = jogo.encerrar()
    assert "(instável)" in fim[0].texto


def test_roteiro_entende_frases_livres_e_pergunta_quando_nao_entende(pastas: tuple[Path, Path]) -> None:
    jogo, _ = abrir(pastas)
    r = jogo.entrada("eu gostaria de falar com ele para me informar melhor sobre o que há no porão")
    assert any("três noites" in t for t in textos(r, "narracao"))
    r = jogo.entrada("canto uma cantiga de ninar")
    assert r[0].tipo == "pergunta" and "não entendeu" in r[0].texto and "desço ao porão" in r[0].texto
    r = jogo.entrada("/continuar")
    assert textos(r, "narracao")
    r = jogo.entrada("quero descer ao porão")
    assert jogo.mesa.estado == "em_combate" and r[0].texto == "Você segue para: O porão."
    assert jogo.entrada("/continuar")[0].tipo == "recusa"
    jogo.encerrar()


def test_ficha_e_cena_nao_gastam_turno(pastas: tuple[Path, Path]) -> None:
    jogo, _ = abrir(pastas)
    turnos = jogo.turnos_do_mestre
    ficha = jogo.entrada("/ficha")[0].texto
    assert "Brenna" in ficha and "Classe de armadura: 18 = " in ficha and "escudo" in ficha
    cena = jogo.entrada("/cena")[0].texto
    assert cena.startswith("A taverna ao anoitecer.") and "Saídas: O porão." in cena
    assert jogo.entrada("/ajuda")[0].texto.startswith("Escreva o que o personagem faz")
    assert jogo.entrada("/xyz")[0].tipo == "recusa"
    assert jogo.turnos_do_mestre == turnos
    jogo.encerrar()


def test_queda_a_zero_pontos_de_vida_bloqueia_as_acoes(tmp_path: Path, pastas: tuple[Path, Path]) -> None:
    # com esta semente os ratos derrubam a guerreira na terceira rodada
    criada = jogo_mod.criar_campanha_da_semente(tmp_path / "queda", "Queda", "aceite-n12-1")
    jogo, _ = abrir((criada.caminho, pastas[1]))
    tela = jogo.entrada("desço ao porão")
    for _ in range(30):
        if jogo.mesa.estado != "em_combate":
            break
        tela += jogo.entrada("ataco o rato")
    assert jogo.mesa.estado == "em_cena" and jogo.mesa.sessao is not None
    assert jogo.mesa.sessao.instantaneo.pontos_de_vida == 0 and jogo.painel().pv == 0
    assert any("Brenna cai a 0 pontos de vida" in t for t in textos(tela, "combate"))
    assert any("Tudo escurece" in t for t in textos(tela, "narracao"))
    r = jogo.entrada("sigo pelo túnel")
    assert r[0].tipo == "recusa" and "0 pontos de vida" in r[0].texto
    assert jogo.mesa.sessao.instantaneo.cena_atual == "cena-porao"
    assert jogo.entrada("/ficha")[0].texto.splitlines()[1] == "Pontos de vida: 0 de 12"
    sem_codigo_cru(tela)
    jogo.encerrar()


# ---------------------------------------------------------------- interpretação da declaração


def _combate() -> motor_combate.EstadoCombate:
    brenna = motor_combate.Combatente(
        "pj-1", "Brenna", "jogador", 18, 12, 12, 1,
        (motor_combate.Ataque("Espada longa", 5, "1d8", 3, "cortante"), motor_combate.Ataque("Azagaia", 5, "1d6", 3, "perfurante", 30, True)),
    )  # fmt: skip
    rato = motor_combate.Ataque("Bite", 5, "1d4", 3, "perfurante")
    r1 = motor_combate.Combatente("cri-rato-1", "Rato gigante", "hostil", 13, 7, 7, 2, (rato,), zona="medio")
    r2 = motor_combate.Combatente("cri-rato-2", "Rato gigante", "hostil", 13, 7, 7, 2, (rato,), zona="perto")
    return motor_combate.EstadoCombate(
        "turno_pj", {c.id: c for c in (brenna, r1, r2)}, ordem=("pj-1", "cri-rato-1", "cri-rato-2"), rodada=1
    )


def test_interpretar_declaracao_do_jogador() -> None:
    c = _combate()
    assert interpretar_declaracao("ataco o rato", c) == motor_combate.Declaracao("atacar", alvo="cri-rato-2")
    assert interpretar_declaracao("ataco o rato 1", c) == motor_combate.Declaracao(
        "atacar", alvo="cri-rato-1"
    )
    assert interpretar_declaracao("ataco o segundo rato", c) == motor_combate.Declaracao(
        "atacar", alvo="cri-rato-2"
    )
    assert interpretar_declaracao("arremesso a azagaia no rato 1", c) == motor_combate.Declaracao(
        "atacar", alvo="cri-rato-1", ataque="Azagaia"
    )
    assert interpretar_declaracao("me aproximo do rato 1", c) == motor_combate.Declaracao(
        "mover", alvo="cri-rato-1", direcao="aproximar"
    )
    assert interpretar_declaracao("me afasto", c) == motor_combate.Declaracao(
        "mover", alvo="cri-rato-2", direcao="afastar"
    )
    assert interpretar_declaracao("Esquivo!", c) == motor_combate.Declaracao("esquivar")
    assert interpretar_declaracao("fujo pela escada", c) == motor_combate.Declaracao("fugir")
    assert interpretar_declaracao("passo", c) == motor_combate.Declaracao("encerrar")
    assert interpretar_declaracao("canto uma canção", c) is None


# ---------------------------------------------------------------- comando único e tela


def test_demo_prepara_a_pasta_e_retoma_na_segunda_vez(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pasta = tmp_path / "demo"
    assert principal(["demo", str(pasta), "--so-preparar"]) == 0
    assert (pasta / "aventuras" / "porao-da-taverna.sqlite").exists()
    assert (pasta / "campanhas" / "o-porao-da-taverna.sqlite").exists()
    assert principal(["demo", str(pasta), "--so-preparar"]) == 0
    saida = capsys.readouterr().out
    assert "campanha criada" in saida and "campanha existente, retomando" in saida
    assert principal(["novo", str(pasta / "campanhas")]) == 1


def test_tela_abre_mostra_o_combate_e_encerra_pelo_comando(
    pastas: tuple[Path, Path], laco_asyncio: asyncio.AbstractEventLoop
) -> None:
    jogo, iniciais = abrir(pastas)
    app = Terminal(jogo, iniciais)

    async def roteiro() -> None:
        async with app.run_test(size=(110, 32)) as pilot:
            await pilot.pause()
            assert "Brenna, Guerreiro 1" in texto_da_barra(jogo.painel())
            assert not app.query_one("#combate", Static).has_class("visivel")
            entrada = app.query_one("#entrada", Input)
            entrada.value = "desço ao porão"
            await pilot.press("enter")
            await pilot.pause()
            assert jogo.mesa.estado == "em_combate"
            assert app.query_one("#combate", Static).has_class("visivel")
            assert "Rato gigante (perto)" in texto_do_painel_de_combate(jogo.painel())
            assert entrada.placeholder.startswith("Seu turno")
            entrada.value = "/sair"
            await pilot.press("enter")  # o jogo encerra e a tela fecha; esperar mais travaria

    laco_asyncio.run_until_complete(roteiro())
    assert jogo.encerrado and app.return_code == 0


def test_textos_da_barra_e_do_painel() -> None:
    p = jogo_mod.Painel(
        "Brenna", "Guerreiro", 1, 7, 12, 18, "O porão", 2, 65, "em_combate", 3,
        (jogo_mod.LinhaDeCombate("pj", "Brenna", "jogador", 7, 12, "perto", (), True, False),
         jogo_mod.LinhaDeCombate("r1", "Rato gigante", "hostil", 0, 7, "perto", ("morto",), False, True)),
        ("ação", "movimento"),
    )  # fmt: skip
    assert (
        texto_da_barra(p)
        == "Brenna, Guerreiro 1  |  PV 7/12  |  CA 18  |  O porão  |  sessão 2  |  01h05  |  COMBATE rodada 3"
    )
    painel = texto_do_painel_de_combate(p)
    assert "> Brenna: 7/12 PV" in painel and "  Rato gigante (perto): fora [morto]" in painel
    assert painel.endswith("Neste turno resta: ação, movimento")
