import os
RAIZ=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(RAIZ,'shots'),exist_ok=True)
# A Ponte do Corvo no navegador: sem IA até um final, e com IA simulada propondo efeitos.
import sys, re, random
from playwright.sync_api import sync_playwright
src=open((''+RAIZ+'/testes/nav2.py'),encoding='utf-8').read(); MOCK=re.search(r"MOCK = r'''(.*?)'''", src, re.S).group(1)
URL=('file://'+RAIZ+'/dist/index.html'); erros=[]
def espera(pg, sel, txt, ms=9000):
    try: pg.wait_for_function("([s,t]) => { const e=document.querySelector(s); return !!e && e.innerText.includes(t); }", arg=[sel, txt], timeout=ms); return True
    except Exception: return False
def livre(pg):
    try: pg.wait_for_function("() => !document.querySelector('#opcoes .pensando')", timeout=9000)
    except Exception: pass
def abrir(b, mock, w=1280, h=860):
    pg=b.new_context(viewport={'width':w,'height':h}).new_page()
    if mock: pg.add_init_script("window.__UID='u1';"+MOCK)
    pg.on('pageerror', lambda e: erros.append('pageerror: '+str(e)))
    pg.goto(URL+'#aventuras'); pg.wait_for_timeout(400); assert pg.is_visible('text=A Ponte do Corvo'), 'aventura nova não aparece'
    pg.locator('article:has-text("A Ponte do Corvo") button:has-text("Jogar esta aventura")').click(); pg.wait_for_timeout(300)
    pg.click('button:has-text("Usar heróis prontos")'); pg.wait_for_timeout(100)
    ids=pg.evaluate("JSON.parse(localStorage.getItem('cronica2.herois')).map(x=>x.id)"); pg.check('#mh-'+ids[0], force=True); pg.check('#mh-'+ids[2], force=True); pg.click('#btn-abrir-mesa'); pg.wait_for_selector('#jogo'); pg.wait_for_timeout(200); return pg
def diz(pg, t):
    pg.fill('#texto', t); pg.press('#texto','Enter'); pg.wait_for_timeout(350); livre(pg)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    pg=abrir(b, False); assert 'Vau do Corvo' in pg.inner_text('#topo-cena'), pg.inner_text('#topo-cena')
    pg.screenshot(path=(''+RAIZ+'/shots/v11-ponte.png'))
    diz(pg,'/cena'); assert 'Se você demorar' in pg.inner_text('#painel') or 'Se você demorar' in pg.inner_text('body')
    rnd=random.Random(3); fim=False
    for i in range(700):
        bts=pg.query_selector_all('#opcoes button'); rot=[x.inner_text() for x in bts]
        if 'Sair da mesa' in rot:
            if 'Voltar ao último ponto seguro' in rot: bts[rot.index('Voltar ao último ponto seguro')].click(); pg.wait_for_timeout(80); continue
            fim=True; break
        pref=[k for k,r in enumerate(rot) if any(w in r for w in ('confiança','rastros','Revistar','Confrontar','trilha escondida','Enfrentar',' em ','sulcos','Espiar','Atacar o bando','Levar Osric','Entregar Osric','já se foi','Voltar à vila','Voltar à ponte','Ir até a ponte','Falar com'))]
        k=rnd.choice(pref) if pref and rnd.random()<0.85 else rnd.randrange(len(bts))
        bts[k].click(); pg.wait_for_timeout(25)
    print('D: sem IA, chegou a um final:', fim, '·', re.search(r'Fim da aventura', pg.inner_text('#log')) is not None); assert fim
    pg.screenshot(path=(''+RAIZ+'/shots/v11-ponte-fim.png'))
    # com IA simulada
    pg=abrir(b, True)
    pg.evaluate("window.__iaResp={tipo:'improviso',veredito:'decara',sucesso:'Halda ri sem humor e lhe entrega o caixa da taverna.',falha:'',motivo:'',fato:'',efeitos:[{final:'resgate'},{revelar:'osric'},{marca:'acordo'}]}")
    diz(pg,'convenço a taverneira a me pagar adiantado'); assert espera(pg,'#log','O motor não aceitou'), 'efeitos sem base deveriam ser recusados'; assert 'Fim da aventura' not in pg.inner_text('#log')
    pr=pg.evaluate('window.__prompts[0]'); assert 'MATERIAL DO MESTRE' in pr and '- luz:' in pr and '- osric:' not in pr
    pg.evaluate("window.__iaResp={tipo:'improviso',veredito:'decara',sucesso:'A noite cai enquanto você discute preços.',falha:'',motivo:'',fato:'',efeitos:[{relogio:1}]}")
    diz(pg,'passo a tarde pechinchando'); assert espera(pg,'#log','Ameaça · o bando levanta acampamento: 1 de 6'), pg.inner_text('#log')[-400:]
    pg.evaluate("window.__iaResp={tipo:'acao',id:'ir:ponte'}"); diz(pg,'vou até a ponte'); assert espera(pg,'#topo-cena','Ponte Velha')
    pg.evaluate("window.__iaResp={tipo:'luta',alvos:['tobin'],narracao:'Você agarra o cobrador pelo avental.'}"); diz(pg,'ataco o cobrador'); assert espera(pg,'#log','Combate! Iniciativa') and pg.locator('button.ficha-acao:has-text("em Tobin")').count()>0
    pg.screenshot(path=(''+RAIZ+'/shots/v11-ponte-briga.png'))
    m=abrir(b, False, 390, 780); assert m.evaluate("document.documentElement.scrollWidth<=window.innerWidth"); m.screenshot(path=(''+RAIZ+'/shots/v11-cel.png'))
    b.close()
print('ERROS:', erros if erros else 'nenhum'); sys.exit(1 if erros else 0)
