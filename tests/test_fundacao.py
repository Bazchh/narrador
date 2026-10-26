"""Card N-01: o chão pronto.

Critério de aceite: dado um clone limpo, quando o dev cria o ambiente e roda o comando
de teste, então lint, tipos e testes passam e o processo narrador responde com a versão.
"""

from __future__ import annotations

import importlib
import socket

import pytest

import narrador
from narrador.cli import principal
from tests.conftest import RedeProibidaError

PACOTES = ["motor", "srd", "modulo", "campanha", "mestre"]


def test_processo_responde_com_a_versao(capsys: pytest.CaptureFixture[str]) -> None:
    assert principal(["--versao"]) == 0
    assert capsys.readouterr().out.strip() == f"narrador {narrador.__version__}"


@pytest.mark.parametrize("nome", PACOTES)
def test_os_cinco_pacotes_existem(nome: str) -> None:
    pacote = importlib.import_module(f"narrador.{nome}")
    assert pacote.__doc__, f"o pacote {nome} precisa dizer para que serve"


def test_a_trava_de_rede_derruba_qualquer_socket() -> None:
    with pytest.raises(RedeProibidaError):
        socket.socket()
