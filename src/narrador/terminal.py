"""A tela de jogo no terminal (card N-12): barra de status no topo, narração no centro,
painel de combate à direita só durante o combate, linha do mestre e entrada embaixo.

Tudo que é regra fica em `mestre.jogo`; aqui só se desenha e se encaminha o que foi digitado.
"""

from __future__ import annotations

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, RichLog, Static

from narrador.mestre.jogo import Jogo, Mensagem, Painel

ESTILOS: dict[str, str] = {
    "sistema": "italic dim",
    "narracao": "",
    "mestre": "bold",
    "rolagem": "cyan",
    "combate": "yellow",
    "recusa": "red",
    "pergunta": "bold magenta",
    "eco": "dim",
}

PROMPT_EM_CENA = "O que você faz? (/ajuda)"
PROMPT_EM_COMBATE = "Seu turno: ataco <alvo>, me aproximo, esquivo, fujo, passo"
PROMPT_PAUSADA = "Mesa pausada: escreva para tentar de novo, ou /sair"


class Terminal(App[None]):
    TITLE = "Narrador"
    CSS = """
    Screen { layout: vertical; }
    #status { height: 1; background: $primary; color: $text; padding: 0 1; }
    #corpo { height: 1fr; }
    #narracao { width: 1fr; padding: 0 1; }
    #combate { width: 36; border-left: solid $secondary; padding: 0 1; display: none; }
    #combate.visivel { display: block; }
    #mestre { height: 1; padding: 0 1; color: $text-muted; }
    #entrada { dock: bottom; }
    """

    def __init__(self, jogo: Jogo, iniciais: list[Mensagem]) -> None:
        super().__init__()
        self.jogo = jogo
        self.iniciais = iniciais

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(id="status")
            with Horizontal(id="corpo"):
                yield RichLog(id="narracao", wrap=True, markup=False)
                yield Static(id="combate")
            yield Static(id="mestre")
            yield Input(placeholder=PROMPT_EM_CENA, id="entrada")

    def on_mount(self) -> None:
        self.mostrar(self.iniciais)
        self.query_one("#entrada", Input).focus()

    def on_input_submitted(self, evento: Input.Submitted) -> None:
        texto = evento.value
        entrada = self.query_one("#entrada", Input)
        entrada.value = ""
        if not texto.strip():
            return
        self.mostrar([Mensagem("eco", f"> {texto}")])
        self.mostrar(self.jogo.entrada(texto))
        if self.jogo.encerrado:
            self.exit()

    # ---------------------------------------------------------------- desenho

    def mostrar(self, mensagens: list[Mensagem]) -> None:
        log = self.query_one("#narracao", RichLog)
        for m in mensagens:
            log.write(Text(m.texto, style=ESTILOS.get(m.tipo, "")))
            if m.tipo == "narracao":
                log.write(Text(""))
        self.atualizar(mensagens)

    def atualizar(self, mensagens: list[Mensagem]) -> None:
        if self.jogo.encerrado:
            return
        painel = self.jogo.painel()
        self.query_one("#status", Static).update(texto_da_barra(painel))
        combate = self.query_one("#combate", Static)
        combate.set_class(painel.em_combate, "visivel")
        combate.update(texto_do_painel_de_combate(painel) if painel.em_combate else "")
        linha = next((m.texto for m in reversed(mensagens) if m.tipo in ("pergunta", "mestre", "recusa")), "")
        if not linha:
            linha = "Seu turno." if painel.em_combate else ""
        self.query_one("#mestre", Static).update(linha)
        entrada = self.query_one("#entrada", Input)
        if painel.estado == "pausada":
            entrada.placeholder = PROMPT_PAUSADA
        elif painel.em_combate:
            entrada.placeholder = PROMPT_EM_COMBATE
        else:
            entrada.placeholder = PROMPT_EM_CENA


def texto_da_barra(p: Painel) -> str:
    relogio = f"{p.relogio_minutos // 60:02d}h{p.relogio_minutos % 60:02d}"
    partes = [
        f"{p.nome}, {p.classe} {p.nivel}",
        f"PV {p.pv}/{p.pv_max}",
        f"CA {p.ca}",
        f"{p.cena}",
        f"sessão {p.sessao}",
        relogio,
    ]
    if p.em_combate:
        partes.append(f"COMBATE rodada {p.rodada}")
    if p.estado == "pausada":
        partes.append("PAUSADA")
    return "  |  ".join(partes)


def texto_do_painel_de_combate(p: Painel) -> str:
    linhas = [f"Rodada {p.rodada}", ""]
    for c in p.combatentes:
        marca = ">" if c.atual else " "
        estado = "fora" if c.fora else f"{c.pv}/{c.pv_max} PV"
        extra = f" [{', '.join(c.condicoes)}]" if c.condicoes else ""
        lado = "" if c.lado == "jogador" else f" ({c.zona})"
        linhas.append(f"{marca} {c.nome}{lado}: {estado}{extra}")
    if p.economia:
        linhas += ["", "Neste turno resta: " + ", ".join(p.economia)]
    return "\n".join(linhas)
