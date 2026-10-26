"""Card N-09: combate por zonas: iniciativa, turnos, ataque e fim.

Critério de aceite: dado o personagem e dois ratos gigantes no porão, quando o jogador
ataca e os ratos agem com o provedor falso, então o combate termina com os ratos a zero,
a experiência calculada, cada rolagem no diário e a máquina de estados sem transição
inválida.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from narrador.campanha import banco as campanha_banco
from narrador.campanha import combate as campanha_combate
from narrador.campanha import personagens, rolagens
from narrador.mestre import protocolo, servico, tratadores, tratadores_combate
from narrador.modulo import banco as modulo_banco
from narrador.modulo import canonico
from narrador.motor import combate as motor
from narrador.motor import ficha as motor_ficha

TODOS = {**tratadores.TRATADORES, **tratadores_combate.TRATADORES}
RATOS = [{"id": "cri-rato-1"}, {"id": "cri-rato-2"}]


@pytest.fixture
def mesa() -> Iterator[protocolo.Contexto]:
    cv = campanha_banco.criar()
    cv.execute(
        "insert into campanha (id, nome, aventura_id, modulo_versao, semente, classificacao)"
        " values ('cp1','Teste','av-porao',1,'semente-porao','adulto')"
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


def rolador_puro() -> motor.Rolador:
    """Rolador sem banco para os testes do motor: determinístico por semente."""
    from narrador.motor import dados

    contador = {"n": 0}

    def rolar(expressao: str, modo: motor.Modo, motivo: str, modificadores: dict[str, int]) -> motor.Rolagem:
        contador["n"] += 1
        r = dados.rolar("teste-motor", contador["n"], expressao, modo, modificadores)
        return motor.Rolagem(r.dados, r.total)

    return rolar


# ---------------------------------------------------------------- aceite


def test_combate_do_porao_de_ponta_a_ponta(mesa: protocolo.Contexto) -> None:
    ex = protocolo.Executor(mesa, TODOS)
    r = ex.executar(
        chamada("iniciar_combate", {"participantes": RATOS, "situacao": "dois ratos saltam dos barris"})
    )
    assert r.ok and r.saida is not None and len(r.saida["combatentes"]) == 3
    pj = mesa.extras["personagem_id"]
    rolar = campanha_combate.rolador(mesa.con, "cp1", "s1", "D02")
    mestre = servico.ServicoFalso([])  # os ratos agem por chamadas diretas ao tratador, como o mestre faria
    rodadas = 0
    while mesa.extras["combate"].estado != "encerrado" and rodadas < 30:
        estado: motor.EstadoCombate = mesa.extras["combate"]
        atual = estado.atual
        assert atual is not None
        if estado.estado == "turno_pj":
            alvo = next((h for h in estado.hostis() if not h.fora), None)
            assert alvo is not None
            estado = motor.agir(
                estado, pj, motor.Declaracao("atacar", alvo=alvo.id, ataque="Espada longa"), rolar
            )
            if estado.estado == "turno_pj":
                estado = motor.encerrar_turno(estado)
            mesa.extras["combate"] = estado
            campanha_combate.gravar(mesa.con, "cp1", "s1", estado, "D02")
        else:
            r = ex.executar(
                chamada(
                    "agir_como_criatura",
                    {"criatura_id": atual.id, "intencao": "morde o invasor", "acao": "atacar"},
                )
            )
            assert r.ok, r.erro
        rodadas += 1
    estado = mesa.extras["combate"]
    assert estado.estado == "encerrado"
    assert all(h.caido for h in estado.hostis())
    assert not estado.jogador.caido  # dois ratos contra CA 18 e 12 PV
    assert mestre.turnos_rodados == 0
    fim = ex.executar(
        chamada("declarar_fim_do_combate", {"motivo": "outro", "descricao": "os ratos foram mortos"})
    )
    assert fim.ok and fim.saida is not None and fim.saida["recompensa"]["pontos_de_experiencia"] == 50
    assert set(fim.saida["recompensa"]["derrotados"]) == {"cri-rato-1", "cri-rato-2"}
    registradas = rolagens.listar(mesa.con, "cp1")
    assert len(registradas) == sum(1 for e in estado.eventos if e.tipo in ("iniciativa", "ataque", "dano"))
    assert all(r.contador is not None for r in registradas)
    assert all(c.igual for c in rolagens.reproduzir(mesa.con, "cp1"))


# ---------------------------------------------------------------- máquina de estados


def test_tabela_de_transicoes_inteira() -> None:
    for (estado, evento), destino in motor.TRANSICOES.items():
        assert motor.conferir_transicao(estado, evento) == destino
    pares_invalidos = [
        ("montando", "turno_encerrado"),
        ("encerrado", "declaracao_valida"),
        ("turno_pj", "intencao_valida"),
        ("fim_rodada", "declaracao_valida"),
        ("turno_cri", "declaracao_valida"),
    ]
    for estado, evento in pares_invalidos:
        with pytest.raises(motor.TransicaoInvalidaError):
            motor.conferir_transicao(estado, evento)  # type: ignore[arg-type]


def _ratos_e_brenna() -> list[motor.Combatente]:
    from narrador.srd import catalogo

    rato = catalogo.criatura("Rato gigante")
    brenna = motor.Combatente(
        "pj", "Brenna", "jogador", 18, 12, 12, 1, (motor.Ataque("Espada longa", 5, "1d8", 3, "cortante"),)
    )
    return [
        brenna,
        campanha_combate.combatente_da_criatura("r1", rato),
        campanha_combate.combatente_da_criatura("r2", rato, zona="medio"),
    ]


def test_montagem_ordena_pela_iniciativa_e_surpreso_perde_o_turno() -> None:
    rolar = rolador_puro()
    combatentes = _ratos_e_brenna()
    combatentes[2] = motor.Combatente(**{**combatentes[2].__dict__, "surpreso": True})
    estado = motor.montar(combatentes, rolar)
    assert estado.rodada == 1 and len(estado.ordem) == 3 and estado.estado in ("turno_pj", "turno_cri")
    iniciativas = {e.dados["id"]: e.dados["total"] for e in estado.eventos if e.tipo == "iniciativa"}
    assert list(estado.ordem) == sorted(estado.ordem, key=lambda i: -int(iniciativas[i]))  # type: ignore[call-overload]
    assert any(e.tipo == "surpreso" for e in estado.eventos) or estado.ordem.index("r2") > estado.indice


def test_economia_de_acao_e_alcance() -> None:
    rolar = rolador_puro()
    estado = motor.montar(_ratos_e_brenna(), rolar)
    while estado.estado != "turno_pj":
        estado = motor.encerrar_turno(estado)
    with pytest.raises(motor.AcaoNaoPermitidaError, match="fora do alcance"):
        motor.agir(estado, "pj", motor.Declaracao("atacar", alvo="r2"), rolar)  # r2 está em zona média
    estado = motor.agir(estado, "pj", motor.Declaracao("mover", alvo="r2", direcao="aproximar"), rolar)
    assert estado.combatentes["r2"].zona == "perto" and not estado.economia.movimento
    estado = motor.agir(estado, "pj", motor.Declaracao("atacar", alvo="r2"), rolar)
    assert not estado.economia.acao
    with pytest.raises(motor.AcaoNaoPermitidaError, match="ação já usada"):
        motor.agir(estado, "pj", motor.Declaracao("atacar", alvo="r1"), rolar)
    with pytest.raises(motor.AcaoNaoPermitidaError, match="não é o turno"):
        motor.agir(estado, "r1", motor.Declaracao("atacar", alvo="pj"), rolar)


def test_critico_dobra_os_dados_e_um_natural_erra() -> None:
    chamadas: list[str] = []

    def rolar_fixo(valor_d20: int) -> motor.Rolador:
        def rolar(
            expressao: str, modo: motor.Modo, motivo: str, modificadores: dict[str, int]
        ) -> motor.Rolagem:
            chamadas.append(expressao)
            if expressao == "1d20":
                return motor.Rolagem((valor_d20,), valor_d20 + sum(modificadores.values()))
            n = int(expressao.split("d")[0])
            return motor.Rolagem(tuple([4] * n), 4 * n + sum(modificadores.values()))

        return rolar

    estado = motor.montar(_ratos_e_brenna(), rolar_fixo(10))
    estado = estado.com(estado="turno_pj", indice=estado.ordem.index("pj"), economia=motor.Economia())
    chamadas.clear()
    estado20 = motor.agir(estado, "pj", motor.Declaracao("atacar", alvo="r1"), rolar_fixo(20))
    assert chamadas == ["1d20", "2d8"]  # crítico: dados dobrados
    assert estado20.combatentes["r1"].caido and "morto" in estado20.combatentes["r1"].condicoes
    chamadas.clear()
    estado1 = motor.agir(estado, "pj", motor.Declaracao("atacar", alvo="r1"), rolar_fixo(1))
    assert chamadas == ["1d20"] and estado1.combatentes["r1"].pontos_de_vida == 7


def test_resistencia_vulnerabilidade_e_pv_temporarios() -> None:
    alvo = motor.Combatente(
        "x",
        "X",
        "hostil",
        10,
        20,
        20,
        0,
        (),
        resistencias=frozenset({"cortante"}),
        pontos_de_vida_temporarios=3,
    )
    novo, aplicado, ajuste = motor._aplicar_dano(alvo, 10, "cortante")
    assert (aplicado, ajuste, novo.pontos_de_vida_temporarios, novo.pontos_de_vida) == (
        5,
        "resistente",
        0,
        18,
    )
    vul = motor.Combatente("y", "Y", "hostil", 10, 20, 20, 0, (), vulnerabilidades=frozenset({"fogo"}))
    assert motor._aplicar_dano(vul, 6, "fogo")[1] == 12
    imune = motor.Combatente("z", "Z", "hostil", 10, 20, 20, 0, (), imunidades=frozenset({"veneno"}))
    assert motor._aplicar_dano(imune, 6, "veneno")[0].pontos_de_vida == 20


def test_jogador_a_zero_fica_inconsciente_e_o_combate_encerra() -> None:
    def rolar(expressao: str, modo: motor.Modo, motivo: str, modificadores: dict[str, int]) -> motor.Rolagem:
        if expressao == "1d20":
            return motor.Rolagem((19,), 19 + sum(modificadores.values()))
        return motor.Rolagem((4,), 4 + sum(modificadores.values()))

    brenna = motor.Combatente(
        "pj", "Brenna", "jogador", 10, 5, 5, 1, (motor.Ataque("Espada longa", 5, "1d8", 3, "cortante"),)
    )
    from narrador.srd import catalogo

    rato = campanha_combate.combatente_da_criatura("r1", catalogo.criatura("Rato gigante"))
    estado = motor.montar([brenna, rato], rolar)
    while estado.estado != "turno_cri":
        estado = motor.encerrar_turno(estado)
    estado = motor.agir(estado, "r1", motor.Declaracao("atacar", alvo="pj"), rolar)
    assert (
        estado.jogador.pontos_de_vida == 0
        and "inconsciente" in estado.jogador.condicoes
        and "morto" not in estado.jogador.condicoes
    )
    estado = motor.encerrar_turno(estado)
    assert estado.estado == "encerrado"


def test_combate_preso_pergunta_ao_mestre() -> None:
    rolar = rolador_puro()
    estado = motor.montar(_ratos_e_brenna(), rolar)
    for _ in range(3 * 3 + 1):
        if estado.estado in ("turno_pj", "turno_cri"):
            estado = motor.encerrar_turno(estado)
        if estado.aguardando_mestre:
            break
    assert estado.aguardando_mestre
    estado, recompensa = motor.encerrar(estado, "preso: os ratos fogem pelo túnel")
    assert estado.estado == "encerrado" and recompensa.pontos_de_experiencia == 0


def test_acao_padrao_da_criatura_aproxima_e_ataca() -> None:
    rolar = rolador_puro()
    estado = motor.montar(_ratos_e_brenna(), rolar)
    while not (estado.estado == "turno_cri" and estado.atual is not None and estado.atual.id == "r2"):
        estado = motor.encerrar_turno(estado)
    estado = motor.acao_padrao(estado, "r2", rolar)
    tipos = [e.tipo for e in estado.eventos[-4:]]
    assert "movimento" in tipos and "ataque" in tipos and tipos[-1] == "padrao"


# ---------------------------------------------------------------- tratadores e persistência


def test_criatura_pendente_bloqueia_o_combate(mesa: protocolo.Contexto) -> None:
    modulo: canonico.ModuloCanonico = mesa.extras["modulo"]
    sem_mapa = modulo.model_copy(update={"mapeamentos": {}})
    mesa.extras["modulo"] = sem_mapa
    r = protocolo.Executor(mesa, TODOS).executar(
        chamada("iniciar_combate", {"participantes": RATOS, "situacao": "x"})
    )
    assert r.erro is not None and r.erro.codigo == "acao_nao_permitida" and "bloqueado" in r.erro.mensagem


def test_intencao_impossivel_devolve_a_acao_padrao(mesa: protocolo.Contexto) -> None:
    ex = protocolo.Executor(mesa, TODOS)
    ex.executar(chamada("iniciar_combate", {"participantes": RATOS, "situacao": "x"}))
    estado: motor.EstadoCombate = mesa.extras["combate"]
    while estado.estado != "turno_cri":
        estado = motor.encerrar_turno(estado)
        mesa.extras["combate"] = estado
    atual = estado.atual
    assert atual is not None
    r = ex.executar(
        chamada(
            "agir_como_criatura", {"criatura_id": atual.id, "intencao": "cospe fogo", "acao": "cuspir_fogo"}
        )
    )
    assert (
        r.erro is not None
        and r.erro.codigo == "acao_nao_permitida"
        and r.erro.alternativa is not None
        and "padrao" in r.erro.alternativa
    )
    r2 = ex.executar(
        chamada(
            "agir_como_criatura",
            {
                "criatura_id": "cri-rato-2" if atual.id == "cri-rato-1" else "cri-rato-1",
                "intencao": "x",
                "acao": "atacar",
            },
        )
    )
    assert r2.erro is not None and "não é o turno" in r2.erro.mensagem


def test_estado_gravado_e_recarregado_igual(mesa: protocolo.Contexto) -> None:
    ex = protocolo.Executor(mesa, TODOS)
    ex.executar(chamada("iniciar_combate", {"participantes": RATOS, "situacao": "x"}))
    estado: motor.EstadoCombate = mesa.extras["combate"]
    recarregado = campanha_combate.carregar_ultimo(mesa.con, "cp1")
    assert recarregado == estado
    assert campanha_combate.carregar_ultimo(mesa.con, "cp-vazia") is None
