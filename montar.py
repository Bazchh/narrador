# Junta o motor e a tela em um arquivo só: dist/index.html (jogo) e dist/teste.html (versão de teste).
import os, sys
d = os.path.dirname(os.path.abspath(__file__))
def r(*p): return open(os.path.join(d, *p), encoding='utf-8').read()
partes = ['10-base.js', '20-combate.js', '30-sino.js', '35-treino.js', '37-kit.js', '40-mesa.js']
motor = "(function (root) {\n  'use strict';\n" + "\n".join(r('motor', p) for p in partes) + "\n})(typeof globalThis !== 'undefined' ? globalThis : this);\n"
os.makedirs(os.path.join(d, 'dist'), exist_ok=True)
open(os.path.join(d, 'dist', 'motor.js'), 'w', encoding='utf-8').write(motor)
print('motor', len(motor))
if os.path.exists(os.path.join(d, 'tela', 'shell.html')):
    h = r('tela', 'shell.html')
    for k, c in (('/*CSS*/', r('tela', 'style.css')), ('/*ENGINE*/', motor), ('/*UI*/', "(function () {\n  'use strict';\n" + "\n".join(r('tela', 'ui', f) for f in sorted(os.listdir(os.path.join(d, 'tela', 'ui')))) + "\n})();\n")):
        assert h.count(k) == 1, k
        assert '</script' not in c and '</style' not in c, k
        h = h.replace(k, c)
    open(os.path.join(d, 'dist', 'index.html'), 'w', encoding='utf-8').write(h)
    print('site', len(h))
    t = h.replace('var MODO_TESTE = false;', 'var MODO_TESTE = true;')
    assert t != h
    open(os.path.join(d, 'dist', 'teste.html'), 'w', encoding='utf-8').write(t)
    print('teste', len(t))
