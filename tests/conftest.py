"""Trava de rede: nenhum teste do Narrador chama a rede (Blueprint, capítulo 9).

Qualquer tentativa de abrir um socket durante os testes falha na hora com uma mensagem
clara. O provedor falso cobre tudo que precisaria de serviço de linguagem.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from typing import Any

import pytest


class RedeProibidaError(RuntimeError):
    """Um teste tentou abrir conexão de rede."""


def _socket_proibido(*_args: Any, **_kwargs: Any) -> None:
    raise RedeProibidaError("teste tentou abrir socket; use o provedor falso")


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(socket, "socket", _socket_proibido)
    monkeypatch.setattr(socket, "create_connection", _socket_proibido)
    yield
