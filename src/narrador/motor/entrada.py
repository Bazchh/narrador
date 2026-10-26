"""Classificação da entrada do jogador: pergunta, ação ou ambígua (casos de uso C04 e C05).

Pergunta não é ação (regra RN-11): "e se eu fizer?" recebe resposta sem dado e sem fato.
Em dúvida, a plataforma pergunta ao jogador, que é o lado seguro.
"""

from __future__ import annotations

import re
from typing import Literal

from narrador.srd.catalogo import normalizar

Classe = Literal["pergunta", "acao", "ambigua"]

_PERGUNTA = re.compile(
    r"^(e se|se eu|posso|poderia|consigo|da pra|da para|dava pra|o que acontece|o que aconteceria|"
    r"sera que|como faco|como faria|tem como|rola de|mestre,? (posso|e se|da pra|consigo))\b"
)
_ACAO = re.compile(
    r"^(eu |vou |tento |tentar |quero |pego |ataco |abro |fecho |subo |desco |escalo |corro |"
    r"falo |digo |pergunto |olho |examino |procuro |entro |saio |sigo |ando |uso |lanco |"
    r"empurro |puxo |me |nos )"
)


def classificar(texto: str) -> Classe:
    t = normalizar(texto)
    if not t:
        return "ambigua"
    if _PERGUNTA.search(t):
        return "pergunta"
    if t.endswith("?") or texto.strip().endswith("?"):
        return "pergunta" if not _ACAO.search(t) else "ambigua"
    if _ACAO.search(t):
        return "acao"
    return "ambigua"
