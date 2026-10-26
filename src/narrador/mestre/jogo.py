"""O jogo: a lógica da sessão jogável, sem interface (card N-12; casos B03, C02, C04 a C09, D02).

O terminal só mostra o que este módulo devolve e manda de volta o que o jogador escreveu.
Aqui vive o que é da plataforma: comandos, deslocamento pelo grafo do módulo (C07), a
declaração do jogador em combate (D02), os turnos das criaturas pelo mestre (D03), as
mensagens de recusa em linguagem de jogador e a linha de custo e tempo ao encerrar.
"""

from __future__ import annotations

import re
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from narrador.campanha import personagens, sessoes
from narrador.mestre import servico
from narrador.mestre.mesa import Mesa
from narrador.mestre.protocolo import CodigoErro, Erro, Resultado
from narrador.modulo import canonico
from narrador.motor import combate as motor_combate
from narrador.motor import ficha as motor_ficha
from narrador.motor.combate import Declaracao, EstadoCombate
from narrador.srd.catalogo import normalizar

TipoMensagem = Literal["sistema", "narracao", "mestre", "rolagem", "combate", "recusa", "pergunta", "eco"]

ENTRADA_ABERTURA = "(abertura da sessão)"
ENTRADA_CONTINUAR = "(continuar)"
ENTRADA_FIM_DO_COMBATE = "(fim do combate)"
PREFIXO_TURNO_CRIATURA = "(turno de "
PREFIXO_CHEGADA = "(chegada: "
MINUTOS_POR_DESLOCAMENTO = 5
LIMITE_TURNOS_DE_CRIATURA = 40  # trava contra laço: nenhuma rodada real passa disso

AJUDA = (
    "Escreva o que o personagem faz ou pergunta. Comandos: /ficha (a ficha e de onde vem cada número), "
    "/cena (a descrição do módulo e as saídas), /ir <lugar> (deslocar-se), /continuar (o mestre segue sem você agir), "
    "/ajuda, /sair (encerra a sessão). "
    "Em combate: ataco <alvo>, me aproximo de <alvo>, me afasto, esquivo, desengajo, corro, fujo, passo."
)

RECUSAS: dict[CodigoErro, str] = {
    "entrada_invalida": "O mestre pediu algo malformado ao motor e teve de refazer.",
    "identificador_inexistente": "O mestre citou algo que não existe no módulo e teve de refazer.",
    "pericia_inexistente": "O mestre pediu uma perícia que não existe nas regras e teve de refazer.",
    "dificuldade_fora_da_escala": "O mestre propôs uma dificuldade fora da escala e teve de refazer.",
    "acao_nao_permitida": "As regras não permitem isso agora.",
    "fora_do_srd": "Isso não está nas regras disponíveis nesta mesa.",
    "segredo_bloqueado": "O mestre quase revelou algo que a história ainda não entregou; refez a narração.",
    "contradiz_fato": "O mestre contradisse algo já estabelecido; refez a narração.",
    "reverte_conquista": "O mestre tentou desfazer algo que você já conquistou; o motor não deixou.",
    "veredito_divergente": "O mestre mudou um veredito anterior sem motivo; o motor manteve o anterior.",
    "turno_encerrado": "Uma resposta atrasada do mestre foi descartada.",
    "sem_autorizacao_envio": "Este trecho não pode ser enviado ao serviço sem a sua autorização.",
    "pedido_ambiguo": "O mestre não entendeu o pedido.",
}

FALHAS: dict[servico.TipoFalha, str] = {
    "indisponivel": "o mestre não respondeu",
    "formato": "o mestre respondeu fora do formato",
    "recusa": "o mestre recusou o pedido",
    "limite_de_saida": "a resposta do mestre ficou longa demais",
    "turno_tardio": "a resposta do mestre chegou tarde demais",
}


@dataclass(frozen=True)
class Mensagem:
    tipo: TipoMensagem
    texto: str


@dataclass(frozen=True)
class LinhaDeCombate:
    id: str
    nome: str
    lado: str
    pv: int
    pv_max: int
    zona: str
    condicoes: tuple[str, ...]
    atual: bool
    fora: bool


@dataclass(frozen=True)
class Painel:
    """O que a barra de status e o painel de combate mostram."""

    nome: str
    classe: str
    nivel: int
    pv: int
    pv_max: int
    ca: int
    cena: str
    sessao: int
    relogio_minutos: int
    estado: str
    rodada: int | None
    combatentes: tuple[LinhaDeCombate, ...]
    economia: tuple[str, ...]

    @property
    def em_combate(self) -> bool:
        return self.rodada is not None


# ---------------------------------------------------------------- interpretação da entrada


_MOVIMENTO = re.compile(
    r"\b(vou|vamos|ir|sigo|seguir|entro|entrar|desco|descer|subo|subir|atravesso|atravessar|caminho|ando|"
    r"rastejo|passo (pelo|pela|para|por)|me enfio|avanco (pelo|pela|para|por)|volto|voltar)\b"
)
_PALAVRAS_VAZIAS = {
    "o",
    "a",
    "os",
    "as",
    "de",
    "do",
    "da",
    "dos",
    "das",
    "ao",
    "atras",
    "para",
    "um",
    "uma",
    "e",
}

_DECLARACOES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"^(ataco|atacar|ataque|golpeio|golpear|acerto|bato|corto|espeto|invisto|arremesso)\b"),
        "atacar",
    ),
    (re.compile(r"^(me aproximo|aproximo|avanco|chego perto|vou ate|corro ate|parto para)\b"), "aproximar"),
    (re.compile(r"^(me afasto|afasto|recuo|me distancio)\b"), "afastar"),
    (re.compile(r"^(esquivo|esquiva|me defendo|defendo|me protejo)\b"), "esquivar"),
    (re.compile(r"^(desengajo|desengajar|me desengajo)\b"), "desengajar"),
    (re.compile(r"^(corro|disparo|corrida)\b"), "correr"),
    (re.compile(r"^(fujo|fugir|foge|escapo|me mando)\b"), "fugir"),
    (re.compile(r"^(passo|encerro|termino|fim do turno|nada|espero|aguardo)\b"), "encerrar"),
)


def _palavras(nome: str) -> set[str]:
    return {p for p in normalizar(nome).split() if len(p) >= 4 and p not in _PALAVRAS_VAZIAS}


def _escolher_alvo(texto_norm: str, combate: EstadoCombate) -> motor_combate.Combatente | None:
    vivos = [h for h in combate.hostis() if not h.fora]
    if not vivos:
        return None
    numeros = re.search(r"\b(\d+)\b", texto_norm)
    ordinais = {"primeiro": 1, "primeira": 1, "segundo": 2, "segunda": 2, "terceiro": 3, "terceira": 3}
    indice = (
        int(numeros.group(1)) if numeros else next((v for k, v in ordinais.items() if k in texto_norm), None)
    )
    if indice is not None:
        por_sufixo = [h for h in vivos if h.id.endswith(f"-{indice}")]
        if por_sufixo:
            return por_sufixo[0]
        if 1 <= indice <= len(vivos):
            return vivos[indice - 1]
    nomeados = [h for h in vivos if _palavras(h.nome) & set(texto_norm.split())]
    candidatos = nomeados or vivos
    perto = [h for h in candidatos if h.zona == "perto"]
    return (perto or candidatos)[0]


def interpretar_declaracao(texto: str, combate: EstadoCombate) -> Declaracao | None:
    """A fala do jogador no turno dele vira uma declaração do motor; None quando não dá para entender."""
    t = normalizar(texto)
    for padrao, acao in _DECLARACOES:
        if not padrao.search(t):
            continue
        if acao == "atacar":
            alvo = _escolher_alvo(t, combate)
            if alvo is None:
                return None
            arma = next((a.nome for a in combate.jogador.ataques if _palavras(a.nome) & set(t.split())), None)
            return Declaracao("atacar", alvo=alvo.id, ataque=arma)
        if acao in ("aproximar", "afastar"):
            alvo = _escolher_alvo(t, combate)
            return Declaracao("mover", alvo=alvo.id if alvo else None, direcao=acao)  # type: ignore[arg-type]
        return Declaracao(acao)  # type: ignore[arg-type]
    return None


# ---------------------------------------------------------------- o jogo


@dataclass
class Jogo:
    caminho_campanha: Path
    caminho_aventura: Path
    mestre: servico.ServicoDeLinguagem
    mesa: Mesa = field(init=False)
    encerrado: bool = False
    turnos_do_mestre: int = 0
    uso: servico.Uso = field(default_factory=servico.Uso)
    inicio: float = field(default_factory=time.monotonic)
    ultima_pergunta: str | None = None

    # ---------------------------------------------------------------- abrir e encerrar

    def abrir(self) -> list[Mensagem]:
        """C02: abre (ou retoma) e deixa o mestre abrir a cena. Erros de abertura sobem para quem chamou."""
        self.mesa = Mesa(self.caminho_campanha, self.caminho_aventura)
        sessao = self.mesa.abrir()
        msgs: list[Mensagem] = []
        if sessao.retomada_de:
            msgs.append(
                Mensagem(
                    "sistema", f"Sessão {sessao.numero} retomada: a anterior foi interrompida sem encerrar."
                )
            )
        else:
            msgs.append(Mensagem("sistema", f"Sessão {sessao.numero} aberta."))
        combate = self.mesa.combate_atual()
        if sessao.em_combate and combate is not None:
            msgs.append(Mensagem("combate", f"Você estava em combate: rodada {combate.rodada}."))
            msgs.extend(self._linhas_de_combate(combate.eventos[-3:]))
        msgs.extend(self._turno(ENTRADA_CONTINUAR if sessao.narracao_pendente else ENTRADA_ABERTURA))
        msgs.extend(self._turnos_das_criaturas())
        return msgs

    def encerrar(self) -> list[Mensagem]:
        """C09: tudo já está salvo; marca o fim e mostra a linha de custo e tempo."""
        if self.encerrado:
            return []
        pendencias = []
        if self.mesa.estado == "em_combate":
            pendencias.append("combate em andamento")
        if self.mesa.estado == "pausada":
            self.mesa.retomar_servico()
        self.mesa.encerrar(pendencias or None)
        self.encerrado = True
        minutos = int((time.monotonic() - self.inicio) // 60)
        provedor = getattr(self.mestre, "nome", type(self.mestre).__name__)
        custo = (
            "sem custo"
            if self.uso.custo_estimado == 0 and self.uso.tokens_entrada == 0
            else f"{self.uso.tokens_entrada + self.uso.tokens_saida} tokens, custo estimado {self.uso.custo_estimado:.4f}"
        )
        return [
            Mensagem(
                "sistema",
                f"Sessão encerrada. {self.turnos_do_mestre} turnos do mestre em {minutos} min; {custo} ({provedor}).",
            )
        ]

    # ---------------------------------------------------------------- a entrada do jogador

    def entrada(self, texto: str) -> list[Mensagem]:
        """Uma linha do jogador vira as mensagens que a tela mostra."""
        texto = texto.strip()
        if self.encerrado or not texto:
            return []
        if texto.startswith("/"):
            return self._comando(texto)
        msgs: list[Mensagem] = []
        if self.mesa.estado == "pausada":
            self.mesa.retomar_servico()
            msgs.append(Mensagem("sistema", "Tentando o mestre de novo."))
        if self.mesa.estado not in ("em_cena", "em_combate"):
            return [*msgs, Mensagem("sistema", f"A mesa está '{self.mesa.estado}'; não dá para jogar agora.")]
        if self._caida():
            return [
                *msgs,
                Mensagem(
                    "recusa",
                    "Você está a 0 pontos de vida e não pode agir. Descansar e curar vêm num card futuro; "
                    "por ora, /sair encerra a sessão.",
                ),
            ]
        combate = self.mesa.combate_atual()
        if self.mesa.estado == "em_combate" and combate is not None and combate.estado == "turno_pj":
            return [*msgs, *self._declaracao(texto, combate)]
        if self.mesa.estado == "em_combate":
            return [*msgs, *self._turnos_das_criaturas()]
        destino = self.destino(texto)
        if destino is not None:
            msgs.extend(self._deslocar(destino, texto))
        else:
            msgs.extend(self._turno(texto))
        msgs.extend(self._turnos_das_criaturas())
        return msgs

    def _deslocar(self, destino: canonico.ItemCanonico, texto: str) -> list[Mensagem]:
        """C07: a plataforma muda a cena e o relógio; o mestre narra a chegada (C03)."""
        self.mesa.ir_para(destino.id, MINUTOS_POR_DESLOCAMENTO)
        return [
            Mensagem("sistema", f"Você segue para: {destino.nome}."),
            *self._turno(f"{PREFIXO_CHEGADA}{destino.nome}) {texto}"),
        ]

    def destino(self, texto: str) -> canonico.ItemCanonico | None:
        """C07: a fala do jogador contra as saídas da cena atual no grafo do módulo."""
        t = normalizar(texto)
        if not _MOVIMENTO.search(t):
            return None
        palavras = set(t.split())
        for vizinha in self._vizinhas():
            if _palavras(vizinha.nome) & palavras or vizinha.id in t:
                return vizinha
        return None

    def _vizinhas(self) -> list[canonico.ItemCanonico]:
        assert self.mesa.sessao is not None
        atual = self.mesa.sessao.instantaneo.cena_atual
        if not atual:
            return []
        modulo = self.mesa.modulo
        return [
            modulo.itens[li.para]
            for li in modulo.saidas(atual)
            if li.tipo == "leva_a" and modulo.itens[li.para].tipo == "cena"
        ]

    # ---------------------------------------------------------------- comandos

    def _comando(self, texto: str) -> list[Mensagem]:
        nome, _, resto = texto[1:].partition(" ")
        nome = normalizar(nome)
        if nome in ("sair", "encerrar", "fim"):
            return self.encerrar()
        if nome == "ajuda":
            return [Mensagem("sistema", AJUDA)]
        if nome == "continuar":
            if self.mesa.estado == "em_combate":
                return [Mensagem("recusa", "Em combate é a sua vez: declare o que faz, ou passo.")]
            return [*self._turno(ENTRADA_CONTINUAR), *self._turnos_das_criaturas()]
        if nome == "ficha":
            return [Mensagem("sistema", self.texto_da_ficha())]
        if nome == "cena":
            return [Mensagem("sistema", self.texto_da_cena())]
        if nome == "ir":
            if self.mesa.estado == "em_combate":
                return [Mensagem("recusa", "Em combate não dá para sair andando: lute, desengaje ou fuja.")]
            destino = self.destino(f"vou {resto}") if resto.strip() else None
            if destino is None:
                saidas = ", ".join(v.nome for v in self._vizinhas()) or "nenhuma"
                return [Mensagem("recusa", f"Não achei esse lugar a partir daqui. Saídas: {saidas}.")]
            msgs = self._deslocar(destino, f"vou para {destino.nome}")
            msgs.extend(self._turnos_das_criaturas())
            return msgs
        return [Mensagem("recusa", f"Comando desconhecido: /{nome}. {AJUDA}")]

    def texto_da_ficha(self) -> str:
        """B03: a ficha com o estado da campanha viva e a origem de cada derivado; não gasta turno."""
        assert self.mesa.sessao is not None
        inst = self.mesa.sessao.instantaneo
        if not inst.personagem_id:
            return "A campanha não tem personagem vinculado."
        gravada, d = personagens.consultar(self.mesa.con, self.mesa.campanha_id, inst.personagem_id)
        f = gravada.ficha
        pv = inst.pontos_de_vida if inst.pontos_de_vida is not None else d.pontos_de_vida_maximos.total
        linhas = [
            f"{f.nome}, {d.especie.nome_pt} {d.classe.nome_pt} nível {f.nivel}",
            f"Pontos de vida: {pv} de {d.pontos_de_vida_maximos.total}",
            f"Classe de armadura: {d.classe_armadura.explicar()}",
            f"Iniciativa: {d.iniciativa.explicar()}",
            f"Percepção passiva: {d.percepcao_passiva.explicar()}",
            "Ataques: "
            + "; ".join(
                f"{a.arma.nome_pt} {a.bonus_ataque.total:+d} ({a.dano_dados}{a.bonus_dano.total:+d} {a.dano_tipo})"
                for a in d.ataques
            ),
            "Perícias com proficiência: "
            + ", ".join(
                d.pericias[p].explicar() + f" ({p.rsplit(':', 1)[1]})" for p in f.pericias_proficientes
            ),
        ]
        combate = self.mesa.combate_atual()
        if combate is not None and combate.estado != "encerrado":
            eco = combate.economia
            resta = [
                n
                for n, ok in (("ação", eco.acao), ("movimento", eco.movimento), ("reação", eco.reacao))
                if ok
            ]
            linhas.append(f"Neste turno ainda resta: {', '.join(resta) or 'nada'}.")
        return "\n".join(linhas)

    def texto_da_cena(self) -> str:
        assert self.mesa.sessao is not None
        atual = self.mesa.sessao.instantaneo.cena_atual
        nome = self.mesa.modulo.itens[atual].nome if atual and atual in self.mesa.modulo.itens else "?"
        saidas = ", ".join(v.nome for v in self._vizinhas()) or "nenhuma registrada"
        return f"{nome}. {self.mesa.texto_literal()} Saídas: {saidas}."

    # ---------------------------------------------------------------- turnos

    def _turno(self, texto: str) -> list[Mensagem]:
        turno = self.mesa.rodar_turno(texto, self.mestre)
        self._contabilizar(turno)
        msgs = self._mensagens_das_chamadas(turno.chamadas)
        if turno.falha is not None:
            motivo = FALHAS.get(turno.falha.tipo, turno.falha.tipo)
            if self.mesa.estado == "pausada":
                msgs.append(
                    Mensagem(
                        "sistema",
                        f"Mesa pausada: {motivo} duas vezes. Enquanto isso, o módulo diz: {self.mesa.texto_literal()} "
                        "Escreva de novo para tentar outra vez, ou /sair.",
                    )
                )
            else:
                msgs.append(Mensagem("sistema", f"Falha: {motivo} ({turno.falha.detalhe}). Tente de novo."))
            return msgs
        if turno.narracao is not None:
            msgs.append(Mensagem("narracao", turno.narracao.texto))
        return msgs

    def _turnos_das_criaturas(self) -> list[Mensagem]:
        """D03: cada turno de criatura é um turno do mestre; se o mestre falha, a ficha age (E1)."""
        msgs: list[Mensagem] = []
        for _ in range(LIMITE_TURNOS_DE_CRIATURA):
            combate = self.mesa.combate_atual()
            if self.mesa.estado != "em_combate" or combate is None or combate.estado != "turno_cri":
                break
            atual = combate.atual
            assert atual is not None
            marca = (combate.rodada, combate.indice)
            turno = self.mesa.rodar_turno(f"{PREFIXO_TURNO_CRIATURA}{atual.id})", self.mestre)
            self._contabilizar(turno)
            msgs.extend(self._mensagens_das_chamadas(turno.chamadas))
            if turno.narracao is not None:
                msgs.append(Mensagem("narracao", turno.narracao.texto))
            depois = self.mesa.combate_atual()
            if self._pausada():
                msgs.append(
                    Mensagem("sistema", "Mesa pausada no turno das criaturas; escreva para tentar de novo.")
                )
                break
            if (
                depois is not None
                and depois.estado == "turno_cri"
                and (depois.rodada, depois.indice) == marca
            ):
                estado = self.mesa.agir_padrao_da_criatura(atual.id)
                msgs.append(Mensagem("sistema", f"O mestre não agiu por {atual.nome}; a ficha agiu por ela."))
                msgs.extend(self._linhas_de_combate(estado.eventos[len(combate.eventos) :]))
        if self.mesa.estado == "em_cena":
            combate = self.mesa.combate_atual()
            if combate is not None and combate.estado == "encerrado" and not self._fim_narrado(combate):
                msgs.extend(self._turno(ENTRADA_FIM_DO_COMBATE))
        return msgs

    def _caida(self) -> bool:
        assert self.mesa.sessao is not None
        pv = self.mesa.sessao.instantaneo.pontos_de_vida
        return pv is not None and pv <= 0 and self.mesa.estado == "em_cena"

    def _pausada(self) -> bool:
        # Em função própria: o verificador de tipos não enxerga que rodar_turno muda o estado da mesa.
        return self.mesa.estado == "pausada"

    def _fim_narrado(self, combate: EstadoCombate) -> bool:
        return any(e.tipo == "recompensa" for e in combate.eventos)

    def _declaracao(self, texto: str, combate: EstadoCombate) -> list[Mensagem]:
        decl = interpretar_declaracao(texto, combate)
        if decl is None:
            return [
                Mensagem(
                    "recusa",
                    "Em combate, diga o que faz: ataco <alvo>, me aproximo de <alvo>, me afasto, esquivo, "
                    "desengajo, corro, fujo ou passo.",
                )
            ]
        antes = len(combate.eventos)
        try:
            estado = self.mesa.agir_pelo_jogador(decl)
        except motor_combate.AcaoNaoPermitidaError as ex:
            return [Mensagem("recusa", _recusa_do_motor(ex))]
        msgs = self._linhas_de_combate(estado.eventos[antes:])
        if estado.estado == "turno_pj" and estado.atual is not None and estado.atual.lado == "jogador":
            return [*msgs, Mensagem("mestre", "Ainda é o seu turno.")]
        msgs.extend(self._turno(texto))
        msgs.extend(self._turnos_das_criaturas())
        return msgs

    # ---------------------------------------------------------------- mensagens

    def _contabilizar(self, turno: servico.Turno) -> None:
        self.turnos_do_mestre += 1
        u = turno.uso
        self.uso = servico.Uso(
            self.uso.tokens_entrada + u.tokens_entrada,
            self.uso.tokens_saida + u.tokens_saida,
            self.uso.tokens_cache + u.tokens_cache,
            self.uso.latencia_ms + u.latencia_ms,
            self.uso.custo_estimado + u.custo_estimado,
        )

    def _mensagens_das_chamadas(self, chamadas: Iterable[Resultado]) -> list[Mensagem]:
        msgs: list[Mensagem] = []
        for r in chamadas:
            if r.erro is not None:
                msgs.append(Mensagem("recusa", _recusa(r.erro)))
                continue
            saida = r.saida or {}
            if r.ferramenta == "dar_veredito":
                msgs.append(Mensagem("rolagem", str(saida.get("mostrar_ao_jogador", ""))))
            elif r.ferramenta == "responder_pergunta":
                msgs.append(Mensagem("mestre", str(saida.get("resposta", ""))))
            elif r.ferramenta == "iniciar_combate":
                nomes = [c["nome"] for c in saida.get("combatentes", ())]
                msgs.append(Mensagem("combate", f"Combate! Participantes: {', '.join(nomes)}."))
                msgs.extend(self._linhas_de_combate(saida.get("eventos", ())))
            elif r.ferramenta == "agir_como_criatura":
                msgs.extend(self._linhas_de_combate(saida.get("eventos", ())))
            elif r.ferramenta == "declarar_fim_do_combate":
                rec = saida.get("recompensa", {})
                msgs.append(
                    Mensagem(
                        "combate",
                        f"Fim do combate: {rec.get('pontos_de_experiencia', 0)} pontos de experiência.",
                    )
                )
            elif r.ferramenta == "perguntar_ao_jogador" and saida.get("pendente"):
                opcoes = saida.get("opcoes") or []
                texto = str(saida.get("pergunta", ""))
                if opcoes:
                    texto += " Opções: " + "; ".join(opcoes) + "."
                self.ultima_pergunta = texto
                msgs.append(Mensagem("pergunta", texto))
        return msgs

    def _linhas_de_combate(self, eventos: Iterable[Any]) -> list[Mensagem]:
        linhas = []
        nome_pj = self.painel().nome
        for e in eventos:
            tipo = e["tipo"] if isinstance(e, dict) else e.tipo
            texto = e["texto"] if isinstance(e, dict) else e.texto
            if tipo in ("situacao", "intencao", "padrao"):
                continue
            if tipo == "turno":
                if f"turno de {nome_pj} " not in texto:
                    continue
                texto = "Seu turno" + texto[texto.index(" (") :]
            linhas.append(Mensagem("combate", texto))
        return linhas

    # ---------------------------------------------------------------- painel

    def painel(self) -> Painel:
        assert self.mesa.sessao is not None
        inst = self.mesa.sessao.instantaneo
        nome, classe, nivel, pv_max, ca = "?", "?", 0, 0, 0
        if inst.personagem_id:
            gravada, d = personagens.consultar(self.mesa.con, self.mesa.campanha_id, inst.personagem_id)
            nome, classe, nivel = gravada.ficha.nome, d.classe.nome_pt, gravada.ficha.nivel
            pv_max, ca = d.pontos_de_vida_maximos.total, d.classe_armadura.total
        pv = inst.pontos_de_vida if inst.pontos_de_vida is not None else pv_max
        cena = (
            self.mesa.modulo.itens[inst.cena_atual].nome if inst.cena_atual in self.mesa.modulo.itens else "?"
        )
        combate = self.mesa.combate_atual()
        rodada = None
        linhas: tuple[LinhaDeCombate, ...] = ()
        economia: tuple[str, ...] = ()
        if combate is not None and combate.estado != "encerrado":
            rodada = combate.rodada
            atual = combate.atual
            linhas = tuple(
                LinhaDeCombate(
                    c.id,
                    c.nome,
                    c.lado,
                    c.pontos_de_vida,
                    c.pontos_de_vida_maximos,
                    c.zona,
                    tuple(sorted(c.condicoes)),
                    atual is not None and atual.id == c.id,
                    c.fora,
                )
                for cid in combate.ordem
                for c in (combate.combatentes[cid],)
            )
            eco = combate.economia
            economia = tuple(
                n
                for n, ok in (("ação", eco.acao), ("movimento", eco.movimento), ("reação", eco.reacao))
                if ok
            )
        return Painel(
            nome,
            classe,
            nivel,
            pv,
            pv_max,
            ca,
            cena,
            self.mesa.sessao.numero,
            inst.relogio_minutos,
            self.mesa.estado,
            rodada,
            linhas,
            economia,
        )


# ---------------------------------------------------------------- recusas em linguagem de jogador


def _recusa(erro: Erro) -> str:
    base = RECUSAS.get(erro.codigo, "O motor recusou o pedido.")
    if erro.codigo in ("acao_nao_permitida", "fora_do_srd", "pedido_ambiguo"):
        return f"{base} {_humanizar(erro.mensagem)}"
    return base


def _recusa_do_motor(ex: motor_combate.AcaoNaoPermitidaError) -> str:
    texto = f"As regras não permitem isso agora: {_humanizar(ex.mensagem)}."
    alt = ex.alternativa or {}
    if "alvos" in alt:
        texto += f" Alvos possíveis: {', '.join(alt['alvos'])}."  # type: ignore[arg-type]
    if "mover" in alt:
        texto += f" {alt['mover']}."
    if "ataques" in alt:
        texto += f" Ataques possíveis: {', '.join(alt['ataques'])}."  # type: ignore[arg-type]
    return texto


def _humanizar(mensagem: str) -> str:
    return mensagem.replace("_", " ").rstrip(".")


def criar_campanha_da_semente(pasta: Path, nome: str, semente: str | None = None) -> sessoes.CampanhaCriada:
    """C01 pela plataforma: a campanha da aventura semente, com a ficha pré-gerada, na cena inicial."""
    return sessoes.criar_campanha(
        pasta, nome, "av-porao", 1, motor_ficha.pre_gerados()[0], "cena-taverna", semente=semente
    )
