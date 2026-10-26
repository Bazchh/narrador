"""O mestre roteirizado da aventura semente (card N-12).

Um provedor sem rede e sem custo que joga "O Porão da Taverna" pelas mesmas ferramentas
que um serviço real usaria. Não é indexado por turno: olha a situação (cena, combate,
classe da entrada) e decide, por isso serve ao `narrador demo` com qualquer semente de
dados e ao roteiro de aceite. Quando o provedor real fizer diferente, este é o gabarito.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from narrador.mestre.protocolo import Chamada, Ferramenta, Resultado
from narrador.mestre.servico import ContextoDoTurno, Executar, Falha, Narracao, Turno, Uso
from narrador.srd.catalogo import normalizar

TEXTO_NEUTRO = "O mestre hesita, respira e descreve só o que está diante de você."


@dataclass
class _Turno:
    """Executa chamadas em sequência e fecha o turno pela mesma regra do provedor falso."""

    contexto: ContextoDoTurno
    disponiveis: set[str]
    executar: Executar
    resultados: list[Resultado] = field(default_factory=list)
    narracao: Narracao | None = None

    def chamar(self, ferramenta: str, entrada: dict[str, Any]) -> Resultado:
        if ferramenta not in self.disponiveis:
            raise LookupError(ferramenta)
        chamada = Chamada(
            id=f"{self.contexto.turno}-c{len(self.resultados) + 1}",
            ferramenta=ferramenta,
            entrada=entrada,
            turno=self.contexto.turno,
        )
        r = self.executar(chamada)
        self.resultados.append(r)
        return r

    def narrar(
        self, texto: str, fatos: Sequence[dict[str, Any]] = (), desvios: Sequence[dict[str, Any]] = ()
    ) -> None:
        r = self.chamar("narrar", {"texto": texto, "fatos": list(fatos), "desvios": list(desvios)})
        if not r.ok:
            # G03: a verificação devolveu o texto; a segunda tentativa vai sem os fatos e com texto neutro.
            r = self.chamar("narrar", {"texto": TEXTO_NEUTRO})
        if r.ok and r.saida is not None:
            self.narracao = Narracao(
                str(r.saida.get("texto", "")),
                tuple(r.saida.get("fatos", ())),
                tuple(r.saida.get("desvios", ())),
            )

    def concluir(self) -> Turno:
        if self.narracao is None and not any(
            r.erro and r.erro.codigo == "turno_encerrado" for r in self.resultados
        ):
            return Turno(None, tuple(self.resultados), Falha("formato", "o turno terminou sem narrar"), Uso())
        return Turno(self.narracao, tuple(self.resultados), None, Uso())


def _fato(tipo: str, referencia: str | None, resumo: str, conhecimento: str = "conhecido") -> dict[str, Any]:
    return {"tipo": tipo, "referencia": referencia, "resumo": resumo, "conhecimento": conhecimento}


def _sucesso(r: Resultado) -> bool:
    return r.ok and bool((r.saida or {}).get("resultado", {}).get("sucesso"))


def _tipos(r: Resultado) -> list[str]:
    return [str(e.get("tipo")) for e in (r.saida or {}).get("eventos", ())]


_ATAQUE = re.compile(
    r"^(ataco|atacar|ataque|golpeio|acerto|bato|corto|espeto|arremesso|esquivo|desengajo|fujo|corro|passo)\b"
)


class RoteiroDoPorao:
    """Serviço de linguagem roteirizado para a semente. Sem rede, sem custo, sem segredo vazado."""

    nome = "roteiro embutido da semente, sem custo"

    def rodar_turno(
        self, contexto: ContextoDoTurno, ferramentas: Sequence[Ferramenta], executar: Executar
    ) -> Turno:
        t = _Turno(contexto, {f.nome for f in ferramentas}, executar)
        classe, _, texto = contexto.entrada.partition("] ")
        classe = classe.lstrip("[")
        self._agir(t, classe, texto.strip(), normalizar(texto))
        return t.concluir()

    # ---------------------------------------------------------------- decisão por situação

    def _agir(self, t: _Turno, classe: str, texto: str, tn: str) -> None:
        ctx = t.contexto
        cena_id = str(ctx.cena.get("cena", {}).get("id", ""))
        combate = ctx.personagem.get("combate")
        pv = int(ctx.personagem.get("pv", 1))

        if texto.startswith("(turno de "):
            self._turno_da_criatura(t, texto[len("(turno de ") : -1], pv)
            return
        if texto == "(fim do combate)":
            self._fim_do_combate(t, pv)
            return
        if pv <= 0:
            t.narrar(
                "Você está caída no escuro, sem forças. A aventura termina aqui; use /sair para encerrar."
            )
            return
        if combate is not None:
            self._durante_o_combate(t, tn)
            return
        chegada = texto.startswith("(chegada:")
        abertura = texto in ("(abertura da sessão)", "(continuar)")
        if cena_id == "cena-taverna":
            self._taverna(t, classe, texto, tn, abertura)
        elif cena_id == "cena-porao":
            self._porao(t, classe, texto, tn, abertura or chegada)
        elif cena_id == "cena-tunel":
            self._tunel(t, classe, texto, tn, abertura or chegada)
        else:
            t.narrar(TEXTO_NEUTRO)

    # ---------------------------------------------------------------- a taverna

    def _taverna(self, t: _Turno, classe: str, texto: str, tn: str, abertura: bool) -> None:
        if abertura:
            t.narrar(
                "A Taverna do Cavalo Manco está vazia ao anoitecer. O taverneiro enxuga o mesmo caneco há "
                "minutos, de olho no alçapão trancado atrás do balcão. Ele oferece uma noite grátis a quem "
                "olhar o porão. Você pode falar com ele, examinar o alçapão ou descer ao porão."
            )
            return
        if classe == "pergunta":
            r = t.chamar(
                "responder_pergunta",
                {
                    "pergunta": texto,
                    "resposta": "Pode. O taverneiro está atrás do balcão e responde a quem perguntar; "
                    "o alçapão ele destranca para quem aceitar olhar o porão.",
                    "veredito_provavel": {"tipo": "de_cara"},
                },
            )
            t.narrar(
                "O taverneiro continua enxugando o caneco, esperando você decidir." if r.ok else TEXTO_NEUTRO
            )
            return
        if re.search(r"\b(pression|persuad|convenc|intimid|ameac|encar|insist|exij|forc|cobr)", tn):
            pericia = "Intimidação" if re.search(r"\b(intimid|ameac|encar|exij|forc)", tn) else "Persuasão"
            r = t.chamar(
                "dar_veredito",
                {"tentativa": texto, "veredito": {"tipo": "teste", "pericia": pericia, "dificuldade": 12}},
            )
            if _sucesso(r):
                t.narrar(
                    "O taverneiro cede. Baixa a voz: perdeu o anel numa aposta com um contrabandista, o mesmo "
                    "que cavou o túnel que sai do porão. Ele quer o anel de volta antes que a esposa note.",
                    [
                        _fato(
                            "conhecimento",
                            "seg-anel",
                            "o taverneiro perdeu o anel apostando com o contrabandista",
                        )
                    ],
                )
            else:
                t.narrar("O taverneiro se fecha: 'É só barulho de rato. Vai olhar ou não vai?'")
            return
        if re.search(r"\b(fal|convers|pergunt|dig|cumpriment|taverneiro|ele|inform|explic|sab|quest)", tn):
            t.narrar(
                "O taverneiro fala baixo: o barulho começou há três noites, sempre depois que a casa fecha. "
                "Ele não desce lá de jeito nenhum. A chave do alçapão está no bolso dele, pronta para quem for.",
                [_fato("conhecimento", "np-taverneiro", "o barulho no porão começou há três noites")],
            )
            return
        if re.search(r"\b(examin|olh|procur|investig|observ|vasculh|inspecion|verific)", tn):
            r = t.chamar(
                "dar_veredito",
                {
                    "tentativa": texto,
                    "veredito": {"tipo": "teste", "pericia": "Percepção", "dificuldade": 10},
                },
            )
            if _sucesso(r):
                t.narrar(
                    "Arranhões frescos na madeira do alçapão, de dentro para fora. E um cheiro de esgoto que "
                    "não combina com uma taverna.",
                    [
                        _fato(
                            "estado_local",
                            "cena-taverna",
                            "o alçapão tem arranhões frescos, de dentro para fora",
                        )
                    ],
                )
            else:
                t.narrar("Pouca luz, muita poeira: nada além de um alçapão trancado.")
            return
        if re.search(r"\b(abr|destranc|arromb|alcapao|chave)", tn):
            t.chamar("dar_veredito", {"tentativa": texto, "veredito": {"tipo": "de_cara"}})
            t.narrar(
                "O taverneiro destranca o alçapão e recua. Uma escada estreita desce para o escuro. "
                "Para descer, diga: desço ao porão."
            )
            return
        self._nao_entendi(
            t, ["falo com o taverneiro", "pressiono o taverneiro", "examino o alçapão", "desço ao porão"]
        )

    # ---------------------------------------------------------------- o porão

    def _porao(self, t: _Turno, classe: str, texto: str, tn: str, chegada: bool) -> None:
        fatos_da_cena = [str(f) for f in t.contexto.cena.get("fatos", ())]
        ratos_derrotados = any("derrotados" in f for f in fatos_da_cena)
        if chegada and not ratos_derrotados and "iniciar_combate" in t.disponiveis:
            r = t.chamar(
                "iniciar_combate",
                {
                    "participantes": [
                        {"id": "cri-rato-1", "zona": "perto"},
                        {"id": "cri-rato-2", "zona": "perto"},
                    ],
                    "situacao": "dois ratos gigantes saltam dos barris ao ver a luz",
                },
            )
            if r.ok:
                t.narrar(
                    "Escuro, úmido, barris roídos. Dois pares de olhos vermelhos, e os donos deles saltam "
                    "dos barris: ratos do tamanho de cães. Combate!"
                )
            else:
                t.narrar("Escuro, úmido, barris roídos. Algo se mexe entre eles.")
            return
        if chegada:
            t.narrar(
                "O porão está quieto. Os ratos jazem entre os barris roídos; atrás deles, uma brecha na parede."
            )
            return
        if classe == "pergunta":
            r = t.chamar(
                "responder_pergunta",
                {
                    "pergunta": texto,
                    "resposta": "Dá para examinar os barris sem risco agora; o que houver atrás deles aparece.",
                    "veredito_provavel": {"tipo": "teste", "pericia": "Investigação", "dificuldade": 10},
                },
            )
            t.narrar("O porão espera, escuro e quieto." if r.ok else TEXTO_NEUTRO)
            return
        if _ATAQUE.search(tn):
            t.narrar("O golpe acerta em cheio e o último rato cai, imóvel. O porão fica em silêncio.")
            return
        if re.search(r"\b(examin|olh|procur|investig|vasculh|barris|empurr|afast|revir|mex)", tn):
            r = t.chamar(
                "dar_veredito",
                {
                    "tentativa": texto,
                    "veredito": {"tipo": "teste", "pericia": "Investigação", "dificuldade": 10},
                },
            )
            if _sucesso(r):
                t.narrar(
                    "Atrás dos barris, a parede foi aberta: um túnel recém-cavado, baixo, com cheiro de esgoto. "
                    "Para entrar, diga: sigo pelo túnel.",
                    [_fato("estado_local", "cena-porao", "há um túnel recém-cavado atrás dos barris")],
                )
            else:
                t.narrar(
                    "Barris, umidade e marcas de dentes. Se há algo mais, está bem escondido. Pode tentar de novo."
                )
            return
        self._nao_entendi(t, ["examino os barris", "sigo pelo túnel"])

    # ---------------------------------------------------------------- o túnel

    def _tunel(self, t: _Turno, classe: str, texto: str, tn: str, chegada: bool) -> None:
        fatos_do_anel = [str(f) for p in t.contexto.cena.get("itens", ()) for f in p.get("fatos", ())]
        anel_recuperado = any("recuper" in f for f in fatos_do_anel)
        if chegada:
            t.narrar(
                "Um túnel recém-cavado, estreito, desce em direção ao esgoto. No chão de terra, algo brilha: "
                "um anel de prata."
                + (" Você já o tem no bolso." if anel_recuperado else " Para pegá-lo, diga: pego o anel.")
            )
            return
        if classe == "pergunta":
            r = t.chamar(
                "responder_pergunta",
                {
                    "pergunta": texto,
                    "resposta": "Pegar o anel não exige teste. Examinar as marcas na parede exige Investigação.",
                    "veredito_provavel": {"tipo": "de_cara"},
                },
            )
            t.narrar("O anel continua brilhando no chão de terra." if r.ok else TEXTO_NEUTRO)
            return
        if re.search(r"\b(peg|apanh|recolh|guard|pass)", tn) and "anel" in tn:
            if anel_recuperado:
                t.chamar("dar_veredito", {"tentativa": texto, "veredito": {"tipo": "de_cara"}})
                t.narrar("O anel já está com você.")
                return
            t.chamar("dar_veredito", {"tentativa": texto, "veredito": {"tipo": "de_cara"}})
            t.narrar(
                "Você pega o anel de prata e limpa a terra dele: tem as iniciais do taverneiro por dentro. "
                "O túnel segue para o esgoto; a história do porão termina aqui. Use /sair para encerrar.",
                [_fato("posse", "it-anel", "Brenna recuperou o anel de prata do taverneiro")],
            )
            return
        if re.search(r"\b(examin|olh|investig|marca|parede|ferramenta|observ)", tn):
            r = t.chamar(
                "dar_veredito",
                {
                    "tentativa": texto,
                    "veredito": {"tipo": "teste", "pericia": "Investigação", "dificuldade": 12},
                },
            )
            if _sucesso(r):
                t.narrar(
                    "As marcas de ferramenta vêm de fora para dentro: alguém cavou o túnel a partir do esgoto. "
                    "Um contrabandista, pelo cheiro de tabaco barato, e o anel caiu dele aqui depois da aposta.",
                    [
                        _fato(
                            "conhecimento",
                            "seg-anel",
                            "o túnel foi cavado pelo contrabandista que ganhou o anel na aposta",
                        )
                    ],
                )
            else:
                t.narrar("Terra revirada e marcas que você não sabe ler. Pode tentar de novo com mais luz.")
            return
        self._nao_entendi(t, ["pego o anel", "examino as marcas na parede"])

    def _nao_entendi(self, t: _Turno, opcoes: list[str]) -> None:
        """O roteiro desta fase entende pouco; em vez de fingir, pergunta ao jogador (C04)."""
        t.chamar(
            "perguntar_ao_jogador",
            {
                "pergunta": "O mestre roteirizado desta fase não entendeu. Tente, por exemplo:",
                "opcoes": opcoes,
            },
        )
        t.narrar("O mestre espera você dizer de outro jeito.")

    # ---------------------------------------------------------------- combate

    def _durante_o_combate(self, t: _Turno, tn: str) -> None:
        if re.search(r"\b(fujo|escapo)", tn):
            t.narrar("Você sobe a escada de costas, com os ratos guinchando atrás.")
        elif re.search(r"\b(esquivo|defendo|protejo)", tn):
            t.narrar("Você ergue o escudo e espera o bote.")
        elif re.search(r"\b(aproximo|avanco|afasto|recuo)", tn):
            t.narrar("Você se move entre os barris, sem perder os ratos de vista.")
        else:
            t.narrar("A espada longa corta o ar do porão; os ratos guincham e recuam um passo.")

    def _turno_da_criatura(self, t: _Turno, criatura_id: str, pv: int) -> None:
        r = t.chamar(
            "agir_como_criatura",
            {"criatura_id": criatura_id, "intencao": "morde o tornozelo mais próximo", "acao": "atacar"},
        )
        tipos = _tipos(r)
        if not r.ok:
            t.narrar("O rato hesita, farejando o ar.")
        elif "zero" in tipos:
            t.narrar("Os dentes encontram a junta da armadura. Tudo escurece.")
        elif "dano" in tipos:
            t.narrar("O rato salta e crava os dentes onde a malha não cobre.")
        else:
            t.narrar("O rato salta; os dentes raspam o escudo e ele cai de lado, guinchando.")

    def _fim_do_combate(self, t: _Turno, pv: int) -> None:
        r = t.chamar(
            "declarar_fim_do_combate",
            {"motivo": "outro", "descricao": "os ratos caíram" if pv > 0 else "a guerreira caiu"},
        )
        pe = (r.saida or {}).get("recompensa", {}).get("pontos_de_experiencia", 0)
        if pv <= 0:
            t.narrar("Você cai entre os barris. O porão fica em silêncio.")
            return
        t.narrar(
            f"Os dois ratos jazem entre os barris. Você respira fundo ({pe} pontos de experiência). "
            "Atrás dos barris roídos, a parede parece diferente: vale examinar os barris.",
            [_fato("evento", "cena-porao", "os ratos gigantes do porão foram derrotados")],
        )
