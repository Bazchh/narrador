import os
RAIZ=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(RAIZ,'shots'),exist_ok=True)
# Versão de teste (teste.html): seletor de modelo e medidor, com o Claude simulado.
import sys, re
from playwright.sync_api import sync_playwright
sys.path.insert(0,(''+RAIZ+'/test'))
src=open((''+RAIZ+'/testes/nav2.py'),encoding='utf-8').read()
MOCK=re.search(r"MOCK = r'''(.*?)'''", src, re.S).group(1)
# nesta versão o jogo chama sample() (texto), não sample.json()
MOCK=MOCK.replace("const sample=Object.assign(async()=>({text:'x',truncated:false}),", "const sample=Object.assign(async(prompt,opts)=>{ (window.__ops=window.__ops||[]).push({model:opts.model,tier:opts.modelTier,effort:opts.effort}); await new Promise(r=>setTimeout(r,80)); if(window.__iaErro) throw {code:window.__iaErro}; const j=JSON.stringify({tipo:'improviso',veredito:'teste',pericia:'atuacao',cd:10,sucesso:'A sala relaxa um pouco.',falha:'Ninguém repara.',fato:'Alguém assobiou.'}); return {text: window.__cru||('Claro!\\n```json\\n'+j+'\\n```'), truncated:false, modelTierApplied: opts.modelTier, modelApplied: window.__semModelo?undefined:opts.model}; },")
URL=('file://'+RAIZ+'/dist/teste.html'); erros=[]
def espera(pg, sel, txt, ms=9000):
    try: pg.wait_for_function("([s,t]) => { const e=document.querySelector(s); return !!e && e.innerText.includes(t); }", arg=[sel, txt], timeout=ms); return True
    except Exception: return False
def livre(pg):
    try: pg.wait_for_function("() => !document.querySelector('#opcoes .pensando')", timeout=9000)
    except Exception: pass
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    pg=b.new_context(viewport={'width':1280,'height':900}).new_page(); pg.add_init_script("window.__UID='u1';"+MOCK)
    pg.on('pageerror', lambda e: erros.append('pageerror: '+str(e)))
    pg.goto(URL+'#jogar'); pg.wait_for_timeout(400); pg.click('button:has-text("Usar heróis prontos")'); pg.wait_for_timeout(100)
    ids=pg.evaluate("JSON.parse(localStorage.getItem('cronica2.herois')).map(x=>x.id)"); pg.check('#mh-'+ids[0], force=True); pg.click('#btn-abrir-mesa'); pg.wait_for_selector('#jogo')
    pg.fill('#texto','/mesa'); pg.press('#texto','Enter'); pg.wait_for_timeout(200)
    assert pg.is_visible('#bloco-teste') and pg.is_visible('#sel-modelo'), 'bloco de teste não apareceu'
    pg.fill('#texto','assobio uma canção de ninar bem baixinho'); pg.press('#texto','Enter'); assert espera(pg,'#log','Veredito: teste de Atuação'), 'resposta com cerca de código não foi lida'; livre(pg)
    assert pg.evaluate('window.__ops[0]')=={'model':None,'tier':'quick','effort':None}, pg.evaluate('window.__ops[0]')
    pg.select_option('#sel-modelo','claude-sonnet-5-5'); pg.fill('#texto','dou uma cambalhota de costas'); pg.press('#texto','Enter'); pg.wait_for_timeout(400); livre(pg)
    assert pg.evaluate('window.__ops[1]')=={'model':'claude-sonnet-5-5','tier':'default','effort':'low'}, pg.evaluate('window.__ops[1]')
    pg.fill('#texto','/mesa'); pg.press('#texto','Enter'); pg.wait_for_timeout(200); t=pg.inner_text('#bloco-teste')
    assert 'Consultas nesta sessão: 2' in t and 'respondeu Sonnet 5.5' in t and 'por mil jogadas' in t, t
    pg.evaluate("window.__semModelo=true"); pg.select_option('#sel-modelo','claude-opus-5-5'); pg.fill('#texto','imito um galo'); pg.press('#texto','Enter'); pg.wait_for_timeout(400); livre(pg)
    pg.fill('#texto','/mesa'); pg.press('#texto','Enter'); pg.wait_for_timeout(200); t=pg.inner_text('#bloco-teste'); assert 'não estava disponível' in t and 'nível mais capaz' in t, t
    pg.evaluate("window.__cru='desculpe, não sei'"); pg.fill('#texto','planto bananeira'); pg.press('#texto','Enter'); assert espera(pg,'#opcoes','não respondeu desta vez'), pg.inner_text('#opcoes'); livre(pg)
    pg.screenshot(path=(''+RAIZ+'/shots/v9-teste.png'))
    print(t); b.close()
print('ERROS:', erros if erros else 'nenhum'); sys.exit(1 if erros else 0)
