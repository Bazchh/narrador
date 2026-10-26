"""Trava de rede: nenhum teste do Narrador chama a rede (Blueprint, capítulo 9).

Qualquer tentativa de abrir um socket durante os testes falha na hora com uma mensagem
clara. O provedor falso cobre tudo que precisaria de serviço de linguagem.
"""

from __future__ import annotations

import asyncio
import socket
from collections.abc import Iterator
from typing import Any

import pytest


@pytest.fixture(scope="session")
def laco_asyncio() -> Iterator[asyncio.AbstractEventLoop]:
    """O laço de eventos nasce antes da trava: no Windows ele abre um par de sockets locais
    para acordar a si mesmo, e isso não é rede. Testes do terminal (Textual) rodam nele."""
    laco = asyncio.new_event_loop()
    yield laco
    laco.close()


class RedeProibidaError(RuntimeError):
    """Um teste tentou abrir conexão de rede."""


def _proibido(*_args: Any, **_kwargs: Any) -> None:
    raise RedeProibidaError("teste tentou conectar pela rede; use o provedor falso")


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # A classe socket fica no lugar (o laço de eventos do Windows faz isinstance nela);
    # o que se proíbe é conectar, resolver nome e mandar datagrama, inclusive para localhost.
    monkeypatch.setattr(socket.socket, "connect", _proibido)
    monkeypatch.setattr(socket.socket, "connect_ex", _proibido)
    monkeypatch.setattr(socket.socket, "sendto", _proibido)
    monkeypatch.setattr(socket, "create_connection", _proibido)
    monkeypatch.setattr(socket, "getaddrinfo", _proibido)
    yield
