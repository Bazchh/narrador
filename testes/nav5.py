import os
RAIZ=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(RAIZ,'shots'),exist_ok=True)
# Modos de fala e luta contra moradores, no navegador.
import sys, re
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
    pg.goto(URL+'#jogar'); pg.wait_for_timeout(400); pg.click('button:has-text("Usar heróis prontos")'); pg.wait_for_timeout(100)
    ids=pg.evaluate("JSON.parse(localStorage.getItem('cronica2.herois')).map(x=>x.id)"); pg.check('#mh-'+ids[0], force=True); pg.click('#btn-abrir-mesa'); pg.wait_for_selector('#jogo'); pg.wait_for_timeout(200); return pg
def diz(pg, t, modo=None):
    if modo: pg.select_option('#modo', modo)
    pg.fill('#texto', t); pg.press('#texto','Enter'); pg.wait_for_timeout(350); livre(pg)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    # sem IA
    pg=abrir(b, False)
    assert pg.is_visible('#modo') and pg.get_attribute('#texto','placeholder')=='O que você faz?'
    pg.select_option('#modo','falar'); assert pg.get_attribute('#texto','placeholder')=='O que você diz?'
    diz(pg,'boa noite a todos'); assert '“boa noite a todos”' in pg.inner_text('#log'); assert pg.input_value('#modo')=='falar', 'falar deveria continuar escolhido'
    diz(pg,'o que sei sobre o sino','perguntar'); assert '(ao mestre)' in pg.inner_text('#log') and pg.input_value('#modo')=='agir', 'perguntar deveria voltar para agir'
    diz(pg,'quero atacar Dona Marga com minha espada'); assert espera(pg,'#log','Combate! Iniciativa'), 'sem IA: ataque não começou luta'
    assert pg.locator('button.ficha-acao:has-text("em Dona Marga")').count()>0, pg.inner_text('#opcoes')
    for i in range(40):
        bt=pg.query_selector('button.ficha-acao:has-text("em Dona Marga")') or pg.query_selector('button.ficha-acao:has-text("Encerrar")')
        if not bt: break
        bt.click(); pg.wait_for_timeout(120)
        if 'Fim do combate' in pg.inner_text('#log'): break
    assert espera(pg,'#log','Pedra-Funda não tem guarda'), 'faltou a consequência'; pg.wait_for_timeout(300)
    assert pg.locator('button.ficha-acao:has-text("Falar com Dona Marga")').count()==0
    pg.screenshot(path=(''+RAIZ+'/shots/v10-briga.png'))
    # com IA simulada
    pg=abrir(b, True); pg.evaluate("window.__iaResp={tipo:'luta',alvos:['bento'],narracao:'Você cruza a sala em dois passos.'}")
    diz(pg,'parto para cima do velho'); assert espera(pg,'#log','Você cruza a sala em dois passos') and espera(pg,'#log','Combate! Iniciativa'), 'IA: luta não começou'
    pr=pg.evaluate('window.__prompts[0]'); assert 'PODEM SER ATACADOS: marga = Dona Marga; bento = Bento' in pr and 'MODO ESCOLHIDO PELO JOGADOR: AGIR' in pr
    assert pg.locator('button.ficha-acao:has-text("em Bento")').count()>0
    pg2=abrir(b, True); pg2.evaluate("window.__iaResp={tipo:'luta',alvos:['marga']}")
    diz(pg2,'vou acabar com você','falar'); assert 'Combate!' not in pg2.inner_text('#log'), 'fala iniciou luta'
    assert 'MODO ESCOLHIDO PELO JOGADOR: FALAR' in pg2.evaluate('window.__prompts[0]')
    pg2.evaluate("window.__iaResp={tipo:'pergunta',resposta:'O sino é de pedra.'}"); diz(pg2,'o que é o sino','perguntar'); assert 'O sino é de pedra.' in pg2.inner_text('#log') and 'PERGUNTAR AO MESTRE' in pg2.evaluate('window.__prompts[1]')
    # celular
    m=abrir(b, False, 390, 780); m.screenshot(path=(''+RAIZ+'/shots/v10-cel.png'))
    assert m.evaluate("document.documentElement.scrollWidth<=window.innerWidth"), 'rolagem lateral no celular'
    bx=m.evaluate("(()=>{const a=document.getElementById('modo').getBoundingClientRect(),b=document.getElementById('texto').getBoundingClientRect(),c=document.getElementById('btn-enviar').getBoundingClientRect();return [a.width,b.width,c.right]})()"); print('celular: modo %dpx, texto %dpx'%(bx[0],bx[1])); assert bx[1]>=120 and bx[2]<=390
    b.close()
print('ERROS:', erros if erros else 'nenhum'); sys.exit(1 if erros else 0)
