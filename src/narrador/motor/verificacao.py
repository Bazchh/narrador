"""Verificação de consistência e vazamento de segredo (caso de uso G03; regras RN-01 e RN-05).

Regra pura: recebe o texto que o mestre quer entregar, os fatos novos que ele declara, os
segredos ainda não descobertos e os fatos ativos da campanha, e devolve a lista de
violações. Nada do mestre chega à tela sem passar por aqui.

A verificação é mecânica: palavras-chave do segredo no texto, e ações atribuídas a quem
a campanha viva já deu como morto. É o nível que roda sem serviço de linguagem; o nível
semântico é refinamento posterior, com a mesma saída.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

from narrador.srd.catalogo import normalizar

Codigo = Literal["segredo_bloqueado", "contradiz_fato"]
PALAVRA_MINIMA = 7
VERBOS_DE_VIVO = (
    "fala",
    "diz",
    "responde",
    "sorri",
    "levanta",
    "caminha",
    "ataca",
    "grita",
    "olha",
    "entra",
    "chega",
    "pergunta",
    "oferece",
)
MARCAS_DE_MORTE = re.compile(r"\b(mort[oa]s?|morreu|morreram|cad[aá]ver)\b")


@dataclass(frozen=True)
class Segredo:
    id: str
    nome: str
    texto: str
    palavras_chave: tuple[str, ...] = ()
    condicao_descoberta: str = ""

    def termos(self, excluir: Iterable[str] = ()) -> list[str]:
        """Palavras que só fazem sentido sabendo o segredo: as declaradas ou as longas e raras."""
        if self.palavras_chave:
            return [normalizar(p) for p in self.palavras_chave]
        comuns = set(excluir)
        candidatos = {
            p
            for p in re.findall(r"[a-zà-ú]+", normalizar(f"{self.nome} {self.texto}"))
            if len(p) >= PALAVRA_MINIMA
        }
        return sorted(p for p in candidatos if p not in comuns)


@dataclass(frozen=True)
class FatoAtivo:
    seq: int
    tipo: str
    referencia: str | None
    resumo: str
    nome_referencia: str | None = None


@dataclass(frozen=True)
class FatoDeclarado:
    tipo: str
    referencia: str | None
    resumo: str


@dataclass(frozen=True)
class Violacao:
    codigo: Codigo
    detalhe: str
    referencia: str | None = None


@dataclass(frozen=True)
class Verificacao:
    violacoes: tuple[Violacao, ...] = ()
    conferido: dict[str, int] = field(default_factory=dict)

    @property
    def aprovado(self) -> bool:
        return not self.violacoes


def _mencoes(texto_norm: str, termos: Iterable[str]) -> list[str]:
    return [t for t in termos if t and re.search(rf"\b{re.escape(t)}\w*", texto_norm)]


def verificar(
    texto: str,
    fatos_novos: Iterable[FatoDeclarado],
    segredos: Iterable[Segredo],
    fatos_ativos: Iterable[FatoAtivo],
    vocabulario_da_cena: Iterable[str] = (),
) -> Verificacao:
    """Confere o texto e os fatos novos contra segredos não descobertos e fatos ativos."""
    fatos_novos, segredos, fatos_ativos = list(fatos_novos), list(segredos), list(fatos_ativos)
    corpo = " ".join([texto, *(f.resumo for f in fatos_novos)])
    corpo_norm = normalizar(corpo)
    comuns = {p for p in re.findall(r"[a-zà-ú]+", normalizar(" ".join(vocabulario_da_cena)))}
    violacoes: list[Violacao] = []

    for s in segredos:
        achados = _mencoes(corpo_norm, s.termos(comuns))
        if achados:
            violacoes.append(
                Violacao(
                    "segredo_bloqueado",
                    f"o texto menciona {', '.join(achados)}; o personagem ainda não descobriu: {s.nome}",
                    s.id,
                )
            )

    mortos = [
        f
        for f in fatos_ativos
        if f.tipo in ("estado_personagem", "evento")
        and MARCAS_DE_MORTE.search(normalizar(f.resumo))
        and f.referencia
    ]
    for f in mortos:
        nome = normalizar(f.nome_referencia or "")
        if not nome:
            continue
        if re.search(rf"\b{re.escape(nome)}\b[^.!?]*\b({'|'.join(VERBOS_DE_VIVO)})\b", corpo_norm):
            violacoes.append(
                Violacao(
                    "contradiz_fato",
                    f"{f.nome_referencia} age no texto, mas a campanha viva registra: {f.resumo} (registro {f.seq})",
                    f.referencia,
                )
            )
        for novo in fatos_novos:
            if (
                novo.referencia == f.referencia
                and not MARCAS_DE_MORTE.search(normalizar(novo.resumo))
                and novo.tipo == "estado_personagem"
            ):
                violacoes.append(
                    Violacao(
                        "contradiz_fato",
                        f"fato novo sobre {f.nome_referencia} ignora: {f.resumo} (registro {f.seq})",
                        f.referencia,
                    )
                )

    return Verificacao(
        tuple(violacoes),
        {"segredos": len(segredos), "fatos_ativos": len(fatos_ativos), "fatos_novos": len(fatos_novos)},
    )
