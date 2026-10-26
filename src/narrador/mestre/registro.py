"""Todos os tratadores disponíveis na mesa, juntos: é o que o executor da sessão recebe."""

from __future__ import annotations

from narrador.mestre import tratadores, tratadores_combate, tratadores_veredito
from narrador.mestre.protocolo import Tratador

TODOS: dict[str, Tratador] = {
    **tratadores.TRATADORES,
    **tratadores_veredito.TRATADORES,
    **tratadores_combate.TRATADORES,
}
