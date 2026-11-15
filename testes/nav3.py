import os
RAIZ=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(RAIZ,'shots'),exist_ok=True)
# O mesmo jogo, agora plugado num servidor próprio (de mentira). Dois jogadores em aparelhos diferentes.
import sys, re, json, subprocess, time, urllib.request
from playwright.sync_api import sync_playwright
URL=('file://'+RAIZ+'/dist/index.html'); SRV='http://127.0.0.1:8791'
erros=[]
def ouvir(pg, nome):
    pg.on('pageerror', lambda e: erros.append(nome+' pageerror: '+str(e)))
    pg.on('console', lambda m: erros.append(nome+' console: '+m.text) if m.type=='error' and 'ERR_' not in m.text and 'fonts' not in m.text and 'status of 4' not in m.text else None)
def espera(pg, sel, txt, ms=9000):
    try:
        pg.wait_for_function("([s,t]) => { const e=document.querySelector(s); return !!e && e.innerText.includes(t); }", arg=[sel, txt], timeout=ms); return True
    except Exception: return False
def livre(pg, ms=9000):
    try: pg.wait_for_function("() => !document.querySelector('#opcoes .pensando')", timeout=ms)
    except Exception: pass
def sugestoes(pg):
    b = pg.query_selector('#btn-sugestoes')
    if b and b.inner_text() == 'Sugestões': b.click(); pg.wait_for_timeout(60)
def teste(o):
    r=urllib.request.Request(SRV+'/_teste', data=json.dumps(o).encode(), headers={'Content-Type':'application/json'}, method='POST'); return json.loads(urllib.request.urlopen(r).read())
srv=subprocess.Popen([sys.executable,(''+RAIZ+'/testes/servidor_falso.py'),'8791']); time.sleep(0.8)
try:
  with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    INI="window.CRONICA_SERVIDOR='%s';"%SRV
    c1=b.new_context(viewport={'width':1180,'height':800}); p1=c1.new_page(); p1.add_init_script(INI); ouvir(p1,'P1')
    c2=b.new_context(viewport={'width':1180,'height':800}); p2=c2.new_page(); p2.add_init_script(INI); ouvir(p2,'P2')
    p1.goto(URL+'#inicio'); p1.wait_for_timeout(500)
    assert p1.is_visible('text=Mestre por IA disponível'), 'servidor: IA não ligou'
    assert p1.is_visible('text=Mesas compartilhadas disponíveis'), 'servidor: mesas não ligaram'
    assert 'conta Claude' not in p1.inner_text('body'), 'texto do Claude apareceu fora do Claude'
    p1.goto(URL+'#jogar'); p1.wait_for_timeout(300); p1.click('button:has-text("Usar heróis prontos")'); p1.wait_for_timeout(100)
    ids=p1.evaluate("JSON.parse(localStorage.getItem('cronica2.herois')).map(x=>x.id)")
    p1.check('#onde-online', force=True); p1.wait_for_timeout(60); p1.check('#mh-'+ids[0], force=True); p1.wait_for_timeout(60)
    p1.fill('#mesa-nome','Mesa do servidor')
    if p1.is_visible('#mesa-semente'): p1.fill('#mesa-semente','srv-1')
    p1.click('#btn-abrir-mesa'); p1.wait_for_selector('#jogo', timeout=6000)
    cod=re.search(r'código (\w+)', p1.inner_text('#topo-cena')).group(1); print('C: mesa criada no servidor, código', cod)
    q1=p1.evaluate("JSON.parse(localStorage.getItem('cronica2.aparelho'))")
    p2.goto(URL+'#jogar'); p2.wait_for_timeout(700); p2.click('button:has-text("Usar heróis prontos")'); p2.wait_for_timeout(300)
    ids2=p2.evaluate("JSON.parse(localStorage.getItem('cronica2.herois')).map(x=>x.id)")
    q2=p2.evaluate("JSON.parse(localStorage.getItem('cronica2.aparelho'))"); assert q1 and q2 and q1!=q2, 'aparelhos deveriam ter códigos diferentes'
    assert p2.is_visible('text=Mesa do servidor'), 'p2 não vê a mesa na lista'
    p2.select_option('#entrar-heroi', ids2[1]); p2.fill('#entrar-codigo', cod.upper()); p2.click('button:has-text("Entrar pelo código")'); p2.wait_for_selector('#jogo', timeout=6000)
    assert espera(p2,'#log','junta-se ao grupo'); livre(p2)
    assert espera(p1,'#log','junta-se ao grupo',12000), 'p1 não viu o herói do p2'
    assert p1.locator('.heroi-chip').count()==2 and p2.locator('.heroi-chip').count()==2
    livre(p1); assert p1.is_visible('#btn-sugestoes') and p1.locator('button.ficha-acao').count()==0
    sugestoes(p1); p1.click('button.ficha-acao:has-text("Falar com Dona Marga")'); livre(p1)
    assert espera(p2,'#log','Dona Marga serve uma caneca',12000), 'p2 não recebeu a ação do p1'
    p2.fill('#texto','assobio uma canção de ninar bem baixinho'); p2.press('#texto','Enter'); assert espera(p2,'#log','Veredito: teste de Atuação'), 'mestre do servidor não aplicou'; livre(p2)
    t=teste({}); assert t['pedidos']==1 and 'AÇÕES PREVISTAS' in t['ultimo'], 'pedido ao mestre não chegou ao servidor'
    assert espera(p1,'#log','Veredito: teste de Atuação',12000), 'p1 não viu o improviso'
    teste({'erro_ia':429}); p2.fill('#texto','planto bananeira'); p2.press('#texto','Enter'); assert espera(p2,'#opcoes','limite de uso'), p2.inner_text('#opcoes'); livre(p2)
    assert p2.is_visible('#btn-sugestoes'), 'limite de uso não deveria desligar a IA'
    teste({'erro_ia':0})
    # ponto seguro e elenco chegaram ao servidor
    assert urllib.request.urlopen(SRV+'/mesas/'+cod+'/ponto').status==200
    assert urllib.request.urlopen(SRV+'/elenco/'+q1).status==200
    # aparelho sem permissão de escrita só assiste
    c3=b.new_context(); p3=c3.new_page(); p3.add_init_script(INI); ouvir(p3,'P3')
    p3.goto(URL+'#jogar'); p3.wait_for_timeout(500); q3=p3.evaluate("JSON.parse(localStorage.getItem('cronica2.aparelho'))"); teste({'soleitura':q3})
    p3.click('button:has-text("Usar heróis prontos")'); p3.wait_for_timeout(200); ids3=p3.evaluate("JSON.parse(localStorage.getItem('cronica2.herois')).map(x=>x.id)")
    p3.select_option('#entrar-heroi', ids3[2]); p3.fill('#entrar-codigo', cod); p3.click('button:has-text("Entrar pelo código")'); p3.wait_for_selector('#jogo', timeout=6000); p3.wait_for_timeout(700); livre(p3)
    assert 'não tem permissão' in p3.inner_text('#opcoes') or 'assistindo' in p3.inner_text('#opcoes'), p3.inner_text('#opcoes')
    print('C: dois aparelhos sincronizados, mestre pelo servidor, limite tratado, espectador só assiste')
    # servidor fora do ar: o jogo abre e roda sem IA
    srv.terminate(); srv.wait(); time.sleep(0.3)
    c4=b.new_context(); p4=c4.new_page(); p4.add_init_script(INI); p4.on('pageerror', lambda e: erros.append('P4 pageerror: '+str(e)))
    p4.goto(URL+'#inicio'); p4.wait_for_timeout(900)
    assert p4.is_visible('text=Mestre por IA indisponível'), 'sem servidor deveria avisar que não há IA'
    p4.goto(URL+'#jogar'); p4.wait_for_timeout(300); p4.click('button:has-text("Usar heróis prontos")'); p4.wait_for_timeout(100)
    i4=p4.evaluate("JSON.parse(localStorage.getItem('cronica2.herois')).map(x=>x.id)"); assert p4.is_disabled('#onde-online')
    p4.check('#mh-'+i4[0], force=True); p4.click('#btn-abrir-mesa'); p4.wait_for_selector('#jogo', timeout=6000)
    assert p4.locator('button.ficha-acao').count()>3, 'sem servidor os botões deveriam aparecer'
    print('C: com o servidor fora do ar, o jogo abre e segue pelo roteiro')
    b.close()
finally:
    try: srv.terminate()
    except Exception: pass
print('ERROS:', erros if erros else 'nenhum'); sys.exit(1 if erros else 0)
