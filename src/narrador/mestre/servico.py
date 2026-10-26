"""O adaptador do serviço de linguagem (Blueprint, capítulo 6; card N-07).

A interface é a única parte do código que sabe falar com um serviço. Aqui vive a
interface e o provedor falso, roteirizado por turno: dado um contexto, devolve as
chamadas e a narração que o roteiro manda, sem rede e sem custo. Os provedores reais
entram no card N-13, pela bancada.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from narrador.mestre.protocolo import Chamada, Ferramenta, Resultado

TipoFalha = Literal["indisponivel", "formato", "recusa", "limite_de_saida", "turno_tardio"]


@dataclass(frozen=True)
class ContextoDoTurno:
    """Os seis blocos do capítulo 6, já montados pela plataforma."""

    turno: str
    sistema: str
    mesa: str
    campanha: str
    cena: dict[str, Any]
    personagem: dict[str, Any]
    entrada: str


@dataclass(frozen=True)
class Falha:
    tipo: TipoFalha
    detalhe: str


@dataclass(frozen=True)
class Uso:
    tokens_entrada: int = 0
    tokens_saida: int = 0
    tokens_cache: int = 0
    latencia_ms: int = 0
    custo_estimado: float = 0.0


@dataclass(frozen=True)
class Narracao:
    texto: str
    fatos: tuple[dict[str, Any], ...] = ()
    desvios: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class Turno:
    narracao: Narracao | None
    chamadas: tuple[Resultado, ...]
    falha: Falha | None
    uso: Uso


Executar = Callable[[Chamada], Resultado]


class ServicoDeLinguagem(Protocol):
    def rodar_turno(
        self, contexto: ContextoDoTurno, ferramentas: Sequence[Ferramenta], executar: Executar
    ) -> Turno:
        """Entrega o contexto e as ferramentas ao serviço; executa cada chamada pelo motor e
        devolve os resultados; termina com a narração final ou com uma falha classificada."""
        ...


# ---------------------------------------------------------------- o provedor falso


@dataclass(frozen=True)
class Passo:
    """Um passo do roteiro: ou uma chamada de ferramenta, ou uma falha simulada."""

    ferramenta: str | None = None
    entrada: dict[str, Any] = field(default_factory=dict)
    turno: str | None = None  # para simular chamada de turno tardio
    falha: Falha | None = None


class ServicoFalso:
    """Roteirizado por turno. O roteiro de cada teste é a especificação do que o mestre
    deveria ter feito; quando o provedor real fizer diferente, o teste diz exatamente onde."""

    def __init__(self, roteiro: Sequence[Sequence[Passo]]):
        self.roteiro = [list(t) for t in roteiro]
        self.turnos_rodados = 0
        self.contextos: list[ContextoDoTurno] = []

    def rodar_turno(
        self, contexto: ContextoDoTurno, ferramentas: Sequence[Ferramenta], executar: Executar
    ) -> Turno:
        self.contextos.append(contexto)
        indice = self.turnos_rodados
        self.turnos_rodados += 1
        passos = self.roteiro[indice] if indice < len(self.roteiro) else []
        disponiveis = {f.nome for f in ferramentas}
        resultados: list[Resultado] = []
        narracao: Narracao | None = None
        for n, passo in enumerate(passos, 1):
            if passo.falha is not None:
                return Turno(narracao, tuple(resultados), passo.falha, Uso())
            assert passo.ferramenta is not None
            if passo.ferramenta not in disponiveis:
                return Turno(
                    narracao,
                    tuple(resultados),
                    Falha("formato", f"ferramenta fora da lista: {passo.ferramenta}"),
                    Uso(),
                )
            chamada = Chamada(
                id=f"{contexto.turno}-c{n}",
                ferramenta=passo.ferramenta,
                entrada=passo.entrada,
                turno=passo.turno or contexto.turno,
            )
            resultado = executar(chamada)
            resultados.append(resultado)
            if passo.ferramenta == "narrar" and resultado.ok and resultado.saida is not None:
                narracao = Narracao(
                    texto=str(resultado.saida.get("texto", "")),
                    fatos=tuple(resultado.saida.get("fatos", ())),
                    desvios=tuple(resultado.saida.get("desvios", ())),
                )
        if narracao is None and not any(r.erro and r.erro.codigo == "turno_encerrado" for r in resultados):
            return Turno(
                None, tuple(resultados), Falha("formato", "o turno terminou sem a ferramenta narrar"), Uso()
            )
        return Turno(narracao, tuple(resultados), None, Uso())
