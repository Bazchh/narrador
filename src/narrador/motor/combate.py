"""Combate por zonas (casos de uso D01 a D04, D07, D08; decisão DC-13; Blueprint, capítulo 4).

Regras puras: o estado do combate é um valor; cada ação devolve um estado novo e os
eventos que produziu. Todo dado vem de um `Rolador` injetado (o diário da campanha), para
que o motor continue sem banco, sem rede e sem relógio. A máquina de estados segue a
tabela do capítulo 4: par fora da tabela é `TransicaoInvalidaError`, e nada muda.

Zonas são relativas ao personagem do jogador: perto (corpo a corpo), médio (até 30 pés)
e longe (além). Mover muda a zona de uma criatura em um passo.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from typing import Literal

Zona = Literal["perto", "medio", "longe"]
ZONAS: tuple[Zona, ...] = ("perto", "medio", "longe")
Lado = Literal["jogador", "hostil", "aliado"]
EstadoMaquina = Literal["montando", "turno_pj", "turno_cri", "fim_rodada", "encerrado"]
Modo = Literal["normal", "vantagem", "desvantagem"]
ALCANCE_MEDIO_PES = 30
RODADAS_SEM_DANO_LIMITE = 3
PE_POR_ND = {"0": 10, "0.125": 25, "0.25": 50, "0.5": 100, "1": 200, "2": 450, "3": 700, "4": 1100, "5": 1800}


class TransicaoInvalidaError(Exception):
    """Par (estado, evento) fora da tabela do capítulo 4. Nada é gravado."""


class AcaoNaoPermitidaError(Exception):
    """A declaração viola economia de ação, alcance, condição ou ficha; nada é gasto."""

    def __init__(self, mensagem: str, alternativa: dict[str, object] | None = None):
        self.mensagem, self.alternativa = mensagem, alternativa
        super().__init__(mensagem)


@dataclass(frozen=True)
class Rolagem:
    dados: tuple[int, ...]
    total: int
    registro: int | None = None


Rolador = Callable[[str, Modo, str, dict[str, int]], Rolagem]
"""rolar(expressao, modo, motivo, modificadores) -> Rolagem; a implementação grava no diário."""


@dataclass(frozen=True)
class Ataque:
    nome: str
    bonus: int
    dano_dados: str
    bonus_dano: int
    dano_tipo: str
    alcance_pes: int = 5
    a_distancia: bool = False


@dataclass(frozen=True)
class Combatente:
    id: str
    nome: str
    lado: Lado
    classe_armadura: int
    pontos_de_vida_maximos: int
    pontos_de_vida: int
    bonus_iniciativa: int
    ataques: tuple[Ataque, ...]
    zona: Zona = "perto"
    pontos_de_vida_temporarios: int = 0
    resistencias: frozenset[str] = frozenset()
    vulnerabilidades: frozenset[str] = frozenset()
    imunidades: frozenset[str] = frozenset()
    condicoes: frozenset[str] = frozenset()
    surpreso: bool = False
    fugiu: bool = False
    nivel_de_desafio: str | None = None
    pontos_de_experiencia: int = 0

    @property
    def caido(self) -> bool:
        return self.pontos_de_vida <= 0

    @property
    def fora(self) -> bool:
        return self.caido or self.fugiu


@dataclass(frozen=True)
class Economia:
    acao: bool = True
    acao_bonus: bool = True
    movimento: bool = True
    reacao: bool = True


@dataclass(frozen=True)
class Evento:
    tipo: str
    texto: str
    dados: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class EstadoCombate:
    estado: EstadoMaquina
    combatentes: dict[str, Combatente]
    ordem: tuple[str, ...] = ()
    indice: int = 0
    rodada: int = 0
    economia: Economia = Economia()
    rodadas_sem_dano: int = 0
    houve_dano_na_rodada: bool = False
    aguardando_mestre: bool = False
    eventos: tuple[Evento, ...] = ()

    @property
    def atual(self) -> Combatente | None:
        if self.estado not in ("turno_pj", "turno_cri") or not self.ordem:
            return None
        return self.combatentes[self.ordem[self.indice]]

    @property
    def jogador(self) -> Combatente:
        return next(c for c in self.combatentes.values() if c.lado == "jogador")

    def hostis(self) -> list[Combatente]:
        return [c for c in self.combatentes.values() if c.lado == "hostil"]

    def com(self, **mudancas: object) -> EstadoCombate:
        return replace(self, **mudancas)  # type: ignore[arg-type]

    def anotar(self, tipo: str, texto: str, **dados: object) -> EstadoCombate:
        return self.com(eventos=(*self.eventos, Evento(tipo, texto, dict(dados))))

    def trocar(self, c: Combatente) -> EstadoCombate:
        return self.com(combatentes={**self.combatentes, c.id: c})


# ---------------------------------------------------------------- a tabela de transições

TRANSICOES: dict[tuple[EstadoMaquina, str], str] = {
    ("montando", "iniciativa_rolada"): "turno_*",
    ("montando", "criatura_pendente"): "bloqueado",
    ("turno_pj", "declaracao_valida"): "turno_pj",
    ("turno_pj", "declaracao_invalida"): "turno_pj",
    ("turno_pj", "turno_encerrado"): "proximo",
    ("turno_cri", "intencao_valida"): "turno_cri",
    ("turno_cri", "intencao_impossivel"): "turno_cri",
    ("turno_cri", "servico_falhou"): "turno_cri",
    ("turno_cri", "turno_encerrado"): "proximo",
    ("fim_rodada", "duracoes_aplicadas"): "turno_*",
    ("fim_rodada", "fim_detectado"): "encerrado",
    ("fim_rodada", "preso_no_limite"): "fim_rodada",
    ("turno_pj", "fim_declarado"): "encerrado",
    ("turno_cri", "fim_declarado"): "encerrado",
    ("fim_rodada", "fim_declarado"): "encerrado",
}


def conferir_transicao(estado: EstadoMaquina, evento: str) -> str:
    try:
        return TRANSICOES[(estado, evento)]
    except KeyError as ex:
        raise TransicaoInvalidaError(f"({estado}, {evento}) não está na tabela") from ex


# ---------------------------------------------------------------- montagem


def _turno_de(c: Combatente) -> EstadoMaquina:
    return "turno_pj" if c.lado == "jogador" else "turno_cri"


def montar(combatentes: Sequence[Combatente], rolar: Rolador) -> EstadoCombate:
    """Rola iniciativa para todos e abre o primeiro turno. Surpreso não age na rodada 1."""
    estado = EstadoCombate("montando", {c.id: c for c in combatentes})
    conferir_transicao("montando", "iniciativa_rolada")
    iniciativas: list[tuple[int, int, str]] = []
    for c in combatentes:
        r = rolar("1d20", "normal", f"iniciativa de {c.nome}", {"iniciativa": c.bonus_iniciativa})
        iniciativas.append((r.total, c.bonus_iniciativa, c.id))
        estado = estado.anotar(
            "iniciativa", f"{c.nome}: {r.total}", id=c.id, total=r.total, registro=r.registro
        )
    ordem = tuple(cid for _, _, cid in sorted(iniciativas, key=lambda t: (-t[0], -t[1], t[2])))
    estado = estado.com(ordem=ordem, rodada=1, indice=0)
    return _abrir_turno(estado, "combate iniciado")


def _abrir_turno(estado: EstadoCombate, motivo: str) -> EstadoCombate:
    c = estado.combatentes[estado.ordem[estado.indice]]
    estado = estado.com(estado=_turno_de(c), economia=Economia())
    if c.surpreso and estado.rodada == 1:
        estado = estado.anotar("surpreso", f"{c.nome} está surpreso e perde o turno", id=c.id)
        return encerrar_turno(estado)
    if c.fora:
        return encerrar_turno(estado)
    return estado.anotar(
        "turno", f"turno de {c.nome} (rodada {estado.rodada})", id=c.id, rodada=estado.rodada
    )


def encerrar_turno(estado: EstadoCombate) -> EstadoCombate:
    conferir_transicao(estado.estado, "turno_encerrado")
    proximo = estado.indice + 1
    if proximo >= len(estado.ordem):
        return _fim_da_rodada(estado.com(estado="fim_rodada", indice=0))
    return _abrir_turno(estado.com(indice=proximo), "próximo da ordem")


def _fim_detectado(estado: EstadoCombate) -> str | None:
    if all(h.fora for h in estado.hostis()):
        return "todos os hostis caídos ou fugidos"
    pj = estado.jogador
    if pj.fugiu:
        return "o personagem fugiu"
    if pj.caido:
        return "o personagem caiu"
    return None


def _fim_da_rodada(estado: EstadoCombate) -> EstadoCombate:
    conferir_transicao("fim_rodada", "duracoes_aplicadas")
    motivo = _fim_detectado(estado)
    if motivo:
        conferir_transicao("fim_rodada", "fim_detectado")
        return estado.com(estado="encerrado").anotar("fim", motivo)
    sem_dano = 0 if estado.houve_dano_na_rodada else estado.rodadas_sem_dano + 1
    estado = estado.com(rodadas_sem_dano=sem_dano, houve_dano_na_rodada=False)
    if sem_dano >= RODADAS_SEM_DANO_LIMITE:
        conferir_transicao("fim_rodada", "preso_no_limite")
        estado = estado.com(aguardando_mestre=True).anotar(
            "preso", f"{sem_dano} rodadas sem dano: o mestre decide"
        )
    return _abrir_turno(estado.com(rodada=estado.rodada + 1), "nova rodada")


# ---------------------------------------------------------------- ataque e dano


def _alcance_ok(estado: EstadoCombate, atacante: Combatente, alvo: Combatente, ataque: Ataque) -> Modo | None:
    """Devolve o modo do ataque (normal/desvantagem) ou None se fora de alcance."""
    zona = alvo.zona if atacante.lado == "jogador" else atacante.zona
    if not ataque.a_distancia:
        return "normal" if zona == "perto" else None
    if zona == "perto":
        return "desvantagem"  # arma à distância com inimigo adjacente
    if zona == "medio":
        return "normal"
    return "desvantagem" if ataque.alcance_pes > ALCANCE_MEDIO_PES else None


def _dobrar_dados(expressao: str) -> str:
    n, resto = expressao.lower().split("d", 1)
    return f"{int(n or 1) * 2}d{resto}"


def _aplicar_dano(alvo: Combatente, quantidade: int, tipo: str) -> tuple[Combatente, int, str | None]:
    ajuste = None
    if tipo in alvo.imunidades:
        quantidade, ajuste = 0, "imune"
    elif tipo in alvo.resistencias:
        quantidade, ajuste = quantidade // 2, "resistente"
    elif tipo in alvo.vulnerabilidades:
        quantidade, ajuste = quantidade * 2, "vulnerável"
    temporarios = alvo.pontos_de_vida_temporarios
    absorvido = min(temporarios, quantidade)
    restante = quantidade - absorvido
    novo = alvo.pontos_de_vida - restante
    morreu_direto = alvo.lado != "jogador" and novo <= 0
    novo = max(0, novo)
    condicoes = alvo.condicoes
    if novo == 0:
        condicoes = condicoes | ({"morto"} if morreu_direto else {"inconsciente"})
    return (
        replace(
            alvo, pontos_de_vida=novo, pontos_de_vida_temporarios=temporarios - absorvido, condicoes=condicoes
        ),
        quantidade,
        ajuste,
    )


def atacar(
    estado: EstadoCombate, atacante_id: str, alvo_id: str, nome_ataque: str | None, rolar: Rolador
) -> EstadoCombate:
    """Resolve um ataque: d20 (20 natural acerta e é crítico; 1 natural erra), dano, resistências, PV temporários."""
    atacante, alvo = estado.combatentes[atacante_id], estado.combatentes.get(alvo_id)
    if alvo is None or alvo.fora:
        raise AcaoNaoPermitidaError(
            f"alvo inválido: {alvo_id}",
            {"alvos": [c.id for c in estado.combatentes.values() if not c.fora and c.id != atacante_id]},
        )
    ataque = next(
        (a for a in atacante.ataques if nome_ataque is None or a.nome.lower() == nome_ataque.lower()), None
    )
    if ataque is None:
        raise AcaoNaoPermitidaError(
            f"{atacante.nome} não tem o ataque {nome_ataque!r}",
            {"ataques": [a.nome for a in atacante.ataques]},
        )
    modo = _alcance_ok(estado, atacante, alvo, ataque)
    if modo is None:
        raise AcaoNaoPermitidaError(
            f"{alvo.nome} está fora do alcance de {ataque.nome}", {"mover": "aproxime-se primeiro"}
        )
    r = rolar("1d20", modo, f"{atacante.nome} ataca {alvo.nome} com {ataque.nome}", {"ataque": ataque.bonus})
    natural = r.dados[0]
    critico, erro_automatico = natural == 20, natural == 1
    acertou = critico or (not erro_automatico and r.total >= alvo.classe_armadura)
    estado = estado.anotar(
        "ataque",
        f"{atacante.nome}: {ataque.nome} contra {alvo.nome}, {r.total} contra CA {alvo.classe_armadura}",
        acertou=acertou,
        critico=critico,
        registro=r.registro,
    )
    if not acertou:
        return estado
    dados = _dobrar_dados(ataque.dano_dados) if critico else ataque.dano_dados
    d = rolar(dados, "normal", f"dano de {ataque.nome}", {"dano": ataque.bonus_dano})
    novo_alvo, aplicado, ajuste = _aplicar_dano(alvo, max(0, d.total), ataque.dano_tipo)
    estado = estado.trocar(novo_alvo).com(houve_dano_na_rodada=estado.houve_dano_na_rodada or aplicado > 0)
    estado = estado.anotar(
        "dano",
        f"{alvo.nome} sofre {aplicado} de {ataque.dano_tipo}{' (' + ajuste + ')' if ajuste else ''}",
        registro=d.registro,
        pv=novo_alvo.pontos_de_vida,
    )
    if novo_alvo.caido:
        estado = estado.anotar(
            "zero",
            f"{alvo.nome} cai a 0 pontos de vida" + (" e morre" if "morto" in novo_alvo.condicoes else ""),
            id=alvo.id,
        )
    return estado


# ---------------------------------------------------------------- turnos


AcaoTipo = Literal["atacar", "mover", "esquivar", "desengajar", "correr", "fugir", "encerrar"]


@dataclass(frozen=True)
class Declaracao:
    acao: AcaoTipo
    alvo: str | None = None
    ataque: str | None = None
    direcao: Literal["aproximar", "afastar"] = "aproximar"


def _mover(estado: EstadoCombate, quem: Combatente, alvo_id: str | None, direcao: str) -> EstadoCombate:
    """Mover muda a zona de uma criatura (relativa ao jogador) em um passo."""
    if quem.lado == "jogador":
        if alvo_id is None:
            raise AcaoNaoPermitidaError("mover precisa de um alvo para se aproximar ou afastar")
        quem_muda = estado.combatentes[alvo_id]
    else:
        quem_muda = quem
    i = ZONAS.index(quem_muda.zona)
    nova = ZONAS[max(0, i - 1)] if direcao == "aproximar" else ZONAS[min(2, i + 1)]
    return estado.trocar(replace(quem_muda, zona=nova)).anotar(
        "movimento", f"{quem_muda.nome} agora está {nova}", id=quem_muda.id, zona=nova
    )


def agir(estado: EstadoCombate, quem_id: str, decl: Declaracao, rolar: Rolador) -> EstadoCombate:
    """Executa uma declaração no turno de `quem_id`, conferindo economia de ação e condições."""
    atual = estado.atual
    if atual is None or atual.id != quem_id:
        raise AcaoNaoPermitidaError(f"não é o turno de {quem_id}", {"turno_de": atual.id if atual else None})
    evento = "declaracao_valida" if atual.lado == "jogador" else "intencao_valida"
    conferir_transicao(estado.estado, evento)
    if "inconsciente" in atual.condicoes or "morto" in atual.condicoes:
        raise AcaoNaoPermitidaError(f"{atual.nome} não pode agir: {', '.join(sorted(atual.condicoes))}")
    eco = estado.economia
    if decl.acao == "encerrar":
        return encerrar_turno(estado)
    if decl.acao == "mover":
        if not eco.movimento:
            raise AcaoNaoPermitidaError("movimento já usado neste turno")
        return _mover(estado, atual, decl.alvo, decl.direcao).com(economia=replace(eco, movimento=False))
    if not eco.acao:
        raise AcaoNaoPermitidaError(
            "ação já usada neste turno", {"resta": {"movimento": eco.movimento, "acao_bonus": eco.acao_bonus}}
        )
    if decl.acao == "atacar":
        if decl.alvo is None:
            raise AcaoNaoPermitidaError("atacar precisa de alvo")
        return atacar(estado, atual.id, decl.alvo, decl.ataque, rolar).com(economia=replace(eco, acao=False))
    if decl.acao in ("esquivar", "desengajar"):
        c = replace(atual, condicoes=atual.condicoes | {decl.acao})
        return (
            estado.trocar(c)
            .com(economia=replace(eco, acao=False))
            .anotar(decl.acao, f"{atual.nome} usa a ação {decl.acao}")
        )
    if decl.acao == "correr":
        return estado.com(economia=replace(eco, acao=False, movimento=True)).anotar(
            "correr", f"{atual.nome} corre: movimento dobrado"
        )
    if decl.acao == "fugir":
        c = replace(atual, fugiu=True)
        return (
            estado.trocar(c)
            .com(economia=replace(eco, acao=False))
            .anotar("fuga", f"{atual.nome} foge do combate", id=atual.id)
        )
    raise AcaoNaoPermitidaError(f"ação desconhecida: {decl.acao}")


def acao_padrao(estado: EstadoCombate, criatura_id: str, rolar: Rolador) -> EstadoCombate:
    """A ação padrão da ficha quando o mestre falha ou insiste em algo impossível (D03 E1, E2):
    aproxima-se se preciso e ataca o jogador com o primeiro ataque."""
    c = estado.combatentes[criatura_id]
    pj = estado.jogador
    if c.zona != "perto" and not any(a.a_distancia for a in c.ataques):
        estado = agir(estado, criatura_id, Declaracao("mover", direcao="aproximar"), rolar)
        c = estado.combatentes[criatura_id]
    if c.zona == "perto" or any(a.a_distancia for a in c.ataques):
        estado = agir(estado, criatura_id, Declaracao("atacar", alvo=pj.id), rolar)
    return estado.anotar("padrao", f"{c.nome} agiu pela ação padrão da ficha", id=c.id)


# ---------------------------------------------------------------- fim e recompensa


@dataclass(frozen=True)
class Recompensa:
    pontos_de_experiencia: int
    derrotados: tuple[str, ...]
    fugidos: tuple[str, ...]


def encerrar(estado: EstadoCombate, motivo: str) -> tuple[EstadoCombate, Recompensa]:
    """Fim detectado ou declarado pelo mestre; a experiência vem da tabela do SRD por criatura derrotada."""
    if estado.estado != "encerrado":
        conferir_transicao(estado.estado, "fim_declarado")
        estado = estado.com(estado="encerrado").anotar("fim", motivo)
    derrotados = tuple(h.id for h in estado.hostis() if h.caido)
    fugidos = tuple(h.id for h in estado.hostis() if h.fugiu)
    xp = sum(estado.combatentes[i].pontos_de_experiencia for i in derrotados)
    return estado.anotar("recompensa", f"{xp} PE", pe=xp), Recompensa(xp, derrotados, fugidos)
