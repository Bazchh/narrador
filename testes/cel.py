import os
RAIZ=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(RAIZ,'shots'),exist_ok=True)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    pg=b.new_context(viewport={'width':390,'height':760}, device_scale_factor=2).new_page()
    pg.goto(('file://'+RAIZ+'/dist/index.html#jogar')); pg.wait_for_timeout(300)
    pg.click('button:has-text("Usar heróis prontos")'); pg.wait_for_timeout(100)
    i=pg.evaluate("JSON.parse(localStorage.getItem('cronica2.herois'))[0].id"); pg.check('#mh-'+i, force=True)
    pg.click('summary'); pg.fill('#mesa-semente','d3'); pg.click('#btn-abrir-mesa'); pg.wait_for_timeout(300)
    for t in ['Falar com Dona Marga','Puxar conversa com Bento','Pagar uma bebida']:
        pg.click('button.ficha-acao:has-text("%s")'%t); pg.wait_for_timeout(150)
    pg.click('button.ficha-acao:has-text("Subir a trilha")'); pg.wait_for_timeout(3600)
    pg.screenshot(path=RAIZ+'/shots/cel-limpo.png')
    bts=[x.inner_text() for x in pg.query_selector_all('#opcoes button')]
    alvo=[x for x in bts if 'Atacar' in x]
    if alvo: pg.click('button.ficha-acao:has-text("Atacar os goblins")'); pg.wait_for_timeout(5500); pg.screenshot(path=RAIZ+'/shots/cel-combate.png')
    b.close()
