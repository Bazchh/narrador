#!/bin/sh
# Monta o jogo e roda todos os testes. Sai com erro se algum falhar.
set -e
cd "$(dirname "$0")"
python3 montar.py
echo "== motor: partidas automáticas =="; FUZZ=${FUZZ:-30} BOT=${BOT:-30} node testes/t2.js | tail -1
echo "== motor: luta contra moradores e modos =="; node testes/t3.js | tail -1
echo "== motor: campanha como kit =="; node testes/t4.js | tail -2
if python3 -c "import playwright" 2>/dev/null; then
  for t in nav2 nav3 nav4 nav5 nav6; do echo "== navegador: $t =="; python3 testes/$t.py | tail -1; done
else
  echo "Playwright não instalado: testes de navegador pulados."
fi
