"""O protocolo entre o mestre e o motor (Blueprint, capítulo 5; card N-07).

O mestre não tem acesso ao banco, à ficha nem ao dado: tem ferramentas. Cada ferramenta
tem entrada de forma fixa (campo desconhecido é recusado antes de qualquer regra rodar),
é executada pelo motor, registrada no diário com o turno, e devolve ou uma saída ou um
envelope de erro com código estável. Erro volta como resultado marcado, nunca como
exceção que derruba o turno.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

CodigoErro = Literal[
    "entrada_invalida",
    "identificador_inexistente",
    "pericia_inexistente",
    "dificuldade_fora_da_escala",
    "acao_nao_permitida",
    "fora_do_srd",
    "segredo_bloqueado",
    "contradiz_fato",
    "reverte_conquista",
    "veredito_divergente",
    "turno_encerrado",
    "sem_autorizacao_envio",
    "pedido_ambiguo",
]
CODIGOS_DE_ERRO: tuple[CodigoErro, ...] = (
    "entrada_invalida",
    "identificador_inexistente",
    "pericia_inexistente",
    "dificuldade_fora_da_escala",
    "acao_nao_permitida",
    "fora_do_srd",
    "segredo_bloqueado",
    "contradiz_fato",
    "reverte_conquista",
    "veredito_divergente",
    "turno_encerrado",
    "sem_autorizacao_envio",
    "pedido_ambiguo",
)


class Estrita(BaseModel):
    """Toda entrada de ferramenta: campo desconhecido é recusado, obrigatório ausente é recusado."""

    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------- as quinze entradas


class ConsultarCena(Estrita):
    cena_id: str | None = Field(default=None, description="identificador da cena; vazio = cena atual")


class ConsultarPersonagemMestre(Estrita):
    personagem_id: str


class ConsultarFicha(Estrita):
    secao: Literal["tudo", "vida", "ataques", "pericias", "salvaguardas", "inventario", "combate"] = "tudo"


class OQueOPersonagemSabe(Estrita):
    assunto: str


class ConsultarSrd(Estrita):
    tipo: Literal["criatura", "arma", "armadura", "pericia", "condicao", "especie", "classe"]
    nome: str


class VereditoProposto(Estrita):
    tipo: Literal["de_cara", "impossivel", "teste"]
    pericia: str | None = None
    dificuldade: int | None = None
    modo: Literal["normal", "vantagem", "desvantagem"] = "normal"
    motivo: str | None = None
    sucesso: str | None = None
    falha: str | None = None


class DarVeredito(Estrita):
    tentativa: str
    veredito: VereditoProposto
    motivo_divergencia: str | None = Field(
        default=None, description="o que mudou na cena, se o veredito diverge de um anterior"
    )


class ResponderPergunta(Estrita):
    pergunta: str
    resposta: str
    veredito_provavel: VereditoProposto


class FatoNovo(Estrita):
    tipo: Literal["estado_local", "estado_personagem", "posse", "relacao", "conhecimento", "evento"]
    referencia: str | None = None
    conhecimento: Literal["conhecido", "oculto", "acredita"] = "conhecido"
    resumo: str


class RegistrarFato(Estrita):
    fato: FatoNovo


class RegistrarDesvio(Estrita):
    item_canonico: str | None = None
    o_que_mudou: str
    motivo: str | None = None
    regra: str | None = None


class ProporCaminho(Estrita):
    objetivo: str
    proposta: str
    liga_a: str


class Participante(Estrita):
    id: str
    zona: Literal["perto", "medio", "longe"] = "medio"
    percebeu: bool = True


class IniciarCombate(Estrita):
    participantes: list[Participante]
    situacao: str


class AgirComoCriatura(Estrita):
    criatura_id: str
    intencao: str
    alvo_id: str | None = None
    acao: str | None = None


class DeclararFimDoCombate(Estrita):
    motivo: Literal["rendicao", "fuga", "preso", "outro"]
    descricao: str


class PerguntarAoJogador(Estrita):
    pergunta: str
    opcoes: list[str] = Field(default_factory=list)


class Narrar(Estrita):
    texto: str
    fatos: list[FatoNovo] = Field(default_factory=list)
    desvios: list[RegistrarDesvio] = Field(default_factory=list)


@dataclass(frozen=True)
class Ferramenta:
    nome: str
    descricao: str
    entrada: type[Estrita]
    casos: tuple[str, ...]

    def esquema(self) -> dict[str, Any]:
        """O esquema JSON estrito que vai ao serviço de linguagem."""
        esquema = self.entrada.model_json_schema()
        esquema["additionalProperties"] = False
        return esquema


FERRAMENTAS: dict[str, Ferramenta] = {
    f.nome: f
    for f in (
        Ferramenta(
            "consultar_cena",
            "Recorte da cena atual ou de outra por identificador, com segredos separados e marcados.",
            ConsultarCena,
            ("A05", "C03", "C07"),
        ),
        Ferramenta(
            "consultar_personagem_mestre",
            "Ficha de um personagem do mestre no módulo, estado na campanha viva e o que já disse.",
            ConsultarPersonagemMestre,
            ("C06",),
        ),
        Ferramenta(
            "consultar_ficha",
            "Ficha do personagem do jogador com o estado atual e a composição dos derivados.",
            ConsultarFicha,
            ("B03", "D02"),
        ),
        Ferramenta(
            "o_que_o_personagem_sabe",
            "Fatos conhecidos, acreditados e, para o mestre, os ocultos marcados, sobre um assunto.",
            OQueOPersonagemSabe,
            ("F04", "C02", "C04"),
        ),
        Ferramenta(
            "consultar_srd",
            "Regra, magia, criatura, item ou condição por nome ou identificador, com atribuição.",
            ConsultarSrd,
            ("E03", "B03"),
        ),
        Ferramenta(
            "dar_veredito",
            "Decide uma tentativa: de cara, impossível ou teste com perícia e dificuldade; o motor valida e rola.",
            DarVeredito,
            ("C05", "E02", "E04", "G04"),
        ),
        Ferramenta(
            "responder_pergunta",
            "Registra a resposta a um 'e se eu fizer?' sem rolar nem gravar fato.",
            ResponderPergunta,
            ("C04",),
        ),
        Ferramenta(
            "registrar_fato",
            "Afirmação concreta sobre o mundo, conferida contra os fatos ativos.",
            RegistrarFato,
            ("F01", "G03"),
        ),
        Ferramenta(
            "registrar_desvio",
            "Diferença em relação ao canônico, com motivo e regra invocada.",
            RegistrarDesvio,
            ("F02",),
        ),
        Ferramenta(
            "propor_caminho",
            "Caminho alternativo quando o crítico fechou; validado contra fatos, conquistas e segredos.",
            ProporCaminho,
            ("F03",),
        ),
        Ferramenta(
            "iniciar_combate",
            "Participantes, zonas e quem percebeu quem; o motor monta, resolve surpresa e rola iniciativa.",
            IniciarCombate,
            ("D01",),
        ),
        Ferramenta(
            "agir_como_criatura",
            "Intenção da criatura no turno dela; o motor confere e resolve.",
            AgirComoCriatura,
            ("D03", "D04", "D05"),
        ),
        Ferramenta(
            "declarar_fim_do_combate",
            "Fim por rendição aceita, fuga ou combate preso, com desvio quando couber.",
            DeclararFimDoCombate,
            ("D08",),
        ),
        Ferramenta(
            "perguntar_ao_jogador",
            "Esclarecimento quando a entrada é ambígua.",
            PerguntarAoJogador,
            ("C04", "D02", "E04"),
        ),
        Ferramenta(
            "narrar",
            "Saída final do turno: o texto para o jogador mais os fatos novos; passa pela verificação antes da tela.",
            Narrar,
            ("C03", "C06", "G03"),
        ),
    )
}


# ---------------------------------------------------------------- chamada, resultado, erro


class Erro(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    codigo: CodigoErro
    mensagem: str
    alternativa: dict[str, Any] | None = None
    registro: int | None = None


class ErroDeFerramentaError(Exception):
    """Lançado por um executor para virar envelope de erro, nunca para derrubar o turno."""

    def __init__(self, codigo: CodigoErro, mensagem: str, alternativa: dict[str, Any] | None = None):
        self.codigo, self.mensagem, self.alternativa = codigo, mensagem, alternativa
        super().__init__(f"{codigo}: {mensagem}")


@dataclass(frozen=True)
class Chamada:
    id: str
    ferramenta: str
    entrada: dict[str, Any]
    turno: str


@dataclass(frozen=True)
class Resultado:
    chamada_id: str
    ferramenta: str
    saida: dict[str, Any] | None
    erro: Erro | None
    registro: int | None

    @property
    def ok(self) -> bool:
        return self.erro is None


Tratador = Callable[[Estrita, "Contexto"], dict[str, Any]]


@dataclass
class Contexto:
    """O que o executor sabe da mesa ao executar uma chamada."""

    con: sqlite3.Connection
    campanha_id: str
    sessao_id: str | None
    turno_atual: str | None
    extras: dict[str, Any] = field(default_factory=dict)


class Executor:
    """Valida, executa, registra. Só expõe as ferramentas que têm tratador."""

    def __init__(self, contexto: Contexto, tratadores: dict[str, Tratador]):
        desconhecidas = set(tratadores) - set(FERRAMENTAS)
        if desconhecidas:
            raise KeyError(f"tratador para ferramenta inexistente: {sorted(desconhecidas)}")
        self.contexto = contexto
        self.tratadores = tratadores

    def disponiveis(self) -> list[Ferramenta]:
        return [FERRAMENTAS[n] for n in FERRAMENTAS if n in self.tratadores]

    def executar(self, chamada: Chamada) -> Resultado:
        saida: dict[str, Any] | None = None
        erro: Erro | None = None
        try:
            if chamada.turno != self.contexto.turno_atual:
                raise ErroDeFerramentaError(
                    "turno_encerrado",
                    f"turno {chamada.turno} já encerrado; atual é {self.contexto.turno_atual}",
                )
            ferramenta = FERRAMENTAS.get(chamada.ferramenta)
            if ferramenta is None or chamada.ferramenta not in self.tratadores:
                raise ErroDeFerramentaError(
                    "entrada_invalida",
                    f"ferramenta desconhecida: {chamada.ferramenta}",
                    {"disponiveis": [f.nome for f in self.disponiveis()]},
                )
            try:
                entrada = ferramenta.entrada.model_validate(chamada.entrada)
            except ValidationError as ex:
                raise ErroDeFerramentaError(
                    "entrada_invalida", _resumo_validacao(ex), {"esquema": ferramenta.esquema()}
                ) from ex
            saida = self.tratadores[chamada.ferramenta](entrada, self.contexto)
        except ErroDeFerramentaError as ex:
            erro = Erro(codigo=ex.codigo, mensagem=ex.mensagem, alternativa=ex.alternativa)
        registro = self._registrar(chamada, saida, erro)
        if erro is not None:
            erro = erro.model_copy(update={"registro": registro})
        return Resultado(chamada.id, chamada.ferramenta, saida, erro, registro)

    def _registrar(self, chamada: Chamada, saida: dict[str, Any] | None, erro: Erro | None) -> int:
        dados = {
            "ferramenta": chamada.ferramenta,
            "turno": chamada.turno,
            "entrada": chamada.entrada,
            "saida_resumida": _resumir(saida) if saida is not None else None,
            "erro": erro.model_dump(exclude_none=True) if erro else None,
        }
        cur = self.contexto.con.execute(
            "insert into diario (campanha_id, sessao_id, tipo, origem, dados) values (?, ?, 'consulta', ?, ?)",
            (
                self.contexto.campanha_id,
                self.contexto.sessao_id,
                chamada.ferramenta,
                json.dumps(dados, ensure_ascii=False, default=str),
            ),
        )
        assert cur.lastrowid is not None
        return int(cur.lastrowid)


def _resumo_validacao(ex: ValidationError) -> str:
    partes = []
    for e in ex.errors():
        campo = ".".join(str(x) for x in e["loc"]) or "(raiz)"
        partes.append(f"{campo}: {e['msg']}")
    return "; ".join(partes)


def _resumir(saida: dict[str, Any], limite: int = 400) -> str:
    texto = json.dumps(saida, ensure_ascii=False, default=str)
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"
