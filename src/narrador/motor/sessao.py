"""A máquina de estados da sessão (Blueprint, capítulo 4; casos C02, C09, F05, G05).

Função pura: estado atual mais evento devolve o novo estado. Par fora da tabela é
`TransicaoInvalidaError` e nada é gravado. Interrupção não é estado: é o arquivo ficar
em 'em cena' ou 'em combate' sem encerramento, e a abertura seguinte retomar de lá.
"""

from __future__ import annotations

from typing import Literal

EstadoSessao = Literal["fechada", "abrindo", "em_cena", "em_combate", "pausada", "encerrando", "so_leitura"]
ESTADOS: tuple[EstadoSessao, ...] = (
    "fechada",
    "abrindo",
    "em_cena",
    "em_combate",
    "pausada",
    "encerrando",
    "so_leitura",
)


class TransicaoInvalidaError(Exception):
    """Par (estado, evento) fora da tabela. Nada é gravado."""


TRANSICOES: dict[tuple[EstadoSessao, str], EstadoSessao] = {
    ("fechada", "abrir"): "abrindo",
    ("abrindo", "contexto_pronto"): "em_cena",
    ("abrindo", "contexto_pronto_em_combate"): "em_combate",
    ("abrindo", "inconsistencia"): "so_leitura",
    ("abrindo", "servico_indisponivel"): "fechada",
    ("em_cena", "combate_iniciado"): "em_combate",
    ("em_cena", "falha_servico"): "pausada",
    ("em_cena", "falha_disco"): "pausada",
    ("em_cena", "encerrar"): "encerrando",
    ("em_combate", "combate_encerrado"): "em_cena",
    ("em_combate", "falha_servico"): "pausada",
    ("em_combate", "falha_disco"): "pausada",
    ("em_combate", "encerrar"): "encerrando",
    ("pausada", "servico_voltou"): "em_cena",
    ("pausada", "servico_voltou_em_combate"): "em_combate",
    ("pausada", "encerrar"): "encerrando",
    ("encerrando", "resumo_gravado"): "fechada",
    ("so_leitura", "corrigida_pelo_dono"): "fechada",
}


def transicao(atual: EstadoSessao, evento: str) -> EstadoSessao:
    try:
        return TRANSICOES[(atual, evento)]
    except KeyError as ex:
        raise TransicaoInvalidaError(f"({atual}, {evento}) não está na tabela") from ex
