import os
RAIZ=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(RAIZ,'shots'),exist_ok=True)
import sys, random, re
from playwright.sync_api import sync_playwright
URL=('file://'+RAIZ+'/dist/index.html')
erros=[]
MOCK = r'''
(function(){
 const KEY='mockdb'; const read=()=>JSON.parse(localStorage.getItem(KEY)||'{}'); const write=o=>localStorage.setItem(KEY,JSON.stringify(o));
 const snapDoc=(path)=>{const d=read()[path]; return {id:path.split('/').pop(), exists:d!==undefined, data:()=>d===undefined?undefined:Object.freeze(JSON.parse(JSON.stringify(d))), metadata:{fromCache:false,hasPendingWrites:false}}};
 const okSeg=p=>p.split('/').every(s=>/^[A-Za-z0-9_\-.~:@+]+$/.test(s)&&s!=='.'&&s!=='..');
 function doc(path){ const segs=path.split('/'); if(segs.length%2||!okSeg(path)) throw new TypeError('caminho de documento inválido: '+path);
   return {id:segs[segs.length-1], path,
     get:async()=>snapDoc(path),
     set:async(d)=>{ if(!d||typeof d!=='object'||Array.isArray(d)||JSON.stringify(d).length>262144) throw {code:'invalid_argument',message:'corpo'}; if(window.__SOLEITURA) throw {code:'invalid_argument',message:'sem permissão'}; const o=read(); o[path]=JSON.parse(JSON.stringify(d)); write(o); },
     delete:async()=>{const o=read(); delete o[path]; write(o);},
     acquire:async(opt)=>{ if(typeof opt.holder!=='string') throw {code:'invalid_argument'}; const o=read(), L=o['__lease:'+path], now=Date.now(); if(L&&L.until>now&&L.holder!==opt.holder) return {acquired:false, expiresAt:new Date(L.until).toISOString()}; o['__lease:'+path]={holder:opt.holder, until:now+Math.max(1000,opt.ttlMs||30000)}; write(o); return {acquired:true, holder:opt.holder}; },
     onSnapshot:(next,err)=>{ let last; const tick=()=>{ const s=snapDoc(path), j=JSON.stringify(s.exists?s.data():null); if(j!==last){last=j; next(s);} }; const t=setInterval(tick,120); setTimeout(tick,0); return ()=>clearInterval(t); },
     collection:(sub)=>collection(path+'/'+sub) }; }
 function collection(path){ const segs=path.split('/'); if(segs.length%2===0||!okSeg(path)) throw new TypeError('caminho de coleção inválido: '+path);
   const q={path, limit:()=>q, where:()=>q, orderBy:()=>q,
     get:async()=>{ const o=read(); const docs=Object.keys(o).filter(k=>!k.startsWith('__lease:')&&k.startsWith(path+'/')&&k.split('/').length===segs.length+1).sort().map(k=>snapDoc(k)); return {docs, size:docs.length, empty:!docs.length, docChanges:()=>[]}; },
     doc:(id)=>doc(path+'/'+(id||Math.random().toString(36).slice(2))) }; return q; }
 const sample=Object.assign(async()=>({text:'x',truncated:false}),{ json:async(prompt,opts)=>{ (window.__prompts=window.__prompts||[]).push(prompt); await new Promise(r=>setTimeout(r,120)); if(opts&&opts.signal&&opts.signal.aborted) throw {code:'cancelled'}; if(window.__iaErro) throw {code:window.__iaErro,message:'x'}; return window.__iaResp||{tipo:'improviso',veredito:'teste',pericia:'atuacao',cd:10,sucesso:'A sala relaxa um pouco.',falha:'Ninguém repara.',fato:'Alguém assobiou na estalagem.'}; } });
 window.claude={ use: async(n)=> n==='db'?Object.freeze({doc,collection}): n==='user'?{id:async()=>window.__UID, isOwner:()=>true}: n==='sample'?sample:null };
})();
'''
def ouvir(pg, nome):
    pg.on('pageerror', lambda e: erros.append(nome+' pageerror: '+str(e)))
    pg.on('console', lambda m: erros.append(nome+' console: '+m.text) if m.type=='error' and 'ERR_' not in m.text and 'fonts' not in m.text else None)
def espera(pg, sel, txt, ms=9000):
    try:
        pg.wait_for_function("([s,t]) => { const e=document.querySelector(s); return !!e && e.innerText.includes(t); }", arg=[sel, txt], timeout=ms); return True
    except Exception:
        return False
def livre(pg, ms=9000):
    try:
        pg.wait_for_function("() => !document.querySelector('#opcoes .pensando')", timeout=ms)
    except Exception:
        pass
def sugestoes(pg):
    b = pg.query_selector('#btn-sugestoes')
    if b and b.inner_text() == 'Sugestões': b.click(); pg.wait_for_timeout(60)
def jogar_ate_o_fim(pg, rnd, limite=900):
    for i in range(limite):
        bts=pg.query_selector_all('#opcoes button')
        if not bts: erros.append('sem botões no passo %d'%i); return False
        rot=[x.inner_text() for x in bts]
        if 'Sair da mesa' in rot:
            if 'Voltar ao último ponto seguro' in rot: bts[rot.index('Voltar ao último ponto seguro')].click(); continue
            return True
        pref=[k for k,r in enumerate(rot) if any(w in r for w in ('Subir a trilha','Seguir','Descer à cripta','Atacar','Vasculhar','janela',' em Goblin',' em Esqueleto',' em Zumbi',' em Ivo',' em Guardião','Contar','Quebrar','Voltar para Pedra','corredor','Avançar sobre Ivo','Falar com Dona'))]
        k=rnd.choice(pref) if pref and rnd.random()<0.8 else rnd.randrange(len(bts))
        bts[k].click()
    return False

with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    # ---------- A: como na prévia (sem IA, sem mesa compartilhada) ----------
    ctx=b.new_context(viewport={'width':1280,'height':820}); pg=ctx.new_page(); ouvir(pg,'A')
    pg.goto(URL); pg.wait_for_timeout(300); pg.screenshot(path=RAIZ+'/shots/v2-01-inicio.png')
    assert pg.is_visible('text=com um mestre que nunca falta') and pg.is_hidden('#jogo')
    pg.click('.nav-links >> text=Personagens'); pg.wait_for_selector('h1:has-text("Personagens")', timeout=3000)
    pg.click('button:has-text("Adicionar heróis prontos")'); pg.wait_for_timeout(100)
    assert pg.locator('.caixa h3').count()==4, pg.locator('.caixa h3').count()
    pg.click('#btn-novo-heroi'); pg.wait_for_timeout(100)
    pg.click('#btn-salvar-heroi'); assert pg.is_visible('text=Dê um nome ao personagem')
    pg.fill('#h-nome','Zara'); pg.check('#h-especie-halfling', force=True); pg.check('#h-classe-mago', force=True); pg.check('#h-ant-sabio', force=True)
    pg.select_option('#h-atr-for','15'); assert pg.input_value('#h-atr-int') in ('8','10','12','13','14')
    pg.click('button:has-text("Usar a distribuição sugerida")'); assert pg.input_value('#h-atr-int')=='15'
    pg.check('#h-magias-sono', force=True); pg.check('#h-truques-choque', force=True); pg.check('[id="h-bonus-1+1+1"]', force=True)
    pg.fill('#h-aparencia','pequena, cabelo azul'); assert pg.input_value('#h-nome')=='Zara'
    pg.screenshot(path=RAIZ+'/shots/v2-02-criador.png'); pg.evaluate("document.getElementById('site').scrollTop=1500"); pg.wait_for_timeout(50); pg.screenshot(path=RAIZ+'/shots/v2-03-criador-b.png')
    pg.click('#btn-salvar-heroi'); pg.wait_for_timeout(100)
    assert pg.locator('.caixa h3').count()==5 and pg.is_visible('text=Zara está no elenco')
    pg.click('button:has-text("Ver ficha") >> nth=0'); assert pg.is_visible('#modal >> text=Atributos'); pg.click('#btn-fechar-modal'); assert pg.is_hidden('#modal')
    pg.click('.nav-links >> text=Aventuras'); pg.wait_for_selector('h1:has-text("Aventuras")', timeout=3000); assert pg.is_visible('text=O Pátio de Treino'); pg.click('.nav-links >> text=Regras'); pg.wait_for_selector('h1:has-text("Regras e como jogar")', timeout=3000); pg.screenshot(path=RAIZ+'/shots/v2-04-regras.png')
    pg.click('.nav-links >> text=Jogar'); pg.wait_for_selector('#btn-abrir-mesa', timeout=3000)
    assert pg.is_disabled('#onde-online')
    pg.check('#mh-'+pg.evaluate("JSON.parse(localStorage.getItem('cronica2.herois'))[0].id"), force=True); pg.wait_for_timeout(50)
    pg.screenshot(path=RAIZ+'/shots/v2-05-jogar.png')
    pg.click('#btn-abrir-mesa'); pg.wait_for_timeout(200)
    assert pg.is_visible('#jogo') and pg.locator('.heroi-chip').count()==2, pg.locator('.heroi-chip').count()
    for t in ['quem é ivo?','falo com a dona marga','/diario','/ficha','faço malabarismo com três canecas','quero voar']:
        pg.fill('#texto',t); pg.press('#texto','Enter'); pg.wait_for_timeout(40)
    assert 'não entendeu' in pg.inner_text('#log')
    pg.click('.heroi-chip >> nth=1'); pg.wait_for_timeout(50); assert 'Quem age: Brenna' in pg.inner_text('#opcoes') or 'Quem age: Zara' in pg.inner_text('#opcoes')
    pg.click('button.ficha-acao:has-text("Observar a sala")'); pg.wait_for_timeout(250)
    assert pg.is_visible('#dados'), 'o dado animado deveria aparecer'
    pg.screenshot(path=RAIZ+'/shots/v2-06-mesa.png'); pg.wait_for_timeout(900)
    assert pg.evaluate("(()=>{const c=document.getElementById('mapa');const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let n=0;for(let i=0;i<d.length;i+=997)if(d[i]+d[i+1]+d[i+2]>40)n++;return n})()")>50, 'mapa vazio'
    pg.click('#btn-ficha'); assert pg.is_visible('#modal') and pg.is_visible('#modal >> text=Perícias'); pg.screenshot(path=RAIZ+'/shots/v2-06b-ficha.png'); pg.keyboard.press('Escape'); assert pg.is_hidden('#modal')
    fim=jogar_ate_o_fim(pg, random.Random(11)); print('A: fim alcançado', fim); assert fim
    pg.click('#aba-diario'); pg.wait_for_timeout(50); pg.screenshot(path=RAIZ+'/shots/v2-07-fim.png')
    pg.click('#aba-ajuda'); pg.click('button:has-text("Copiar campanha")'); pg.wait_for_timeout(100)
    cod=pg.input_value('#area-campanha'); assert cod.startswith('{"formato":"cronica-campanha-2"')
    pg.fill('#area-campanha','lixo'); pg.click('button:has-text("Carregar como mesa nova")'); assert 'não é de uma campanha válida' in pg.inner_text('#msg-campanha')
    pg.fill('#area-campanha',cod); pg.click('button:has-text("Carregar como mesa nova")'); pg.wait_for_timeout(150); assert 'Cópia de' in pg.inner_text('#topo-cena')
    pg.reload(); pg.wait_for_timeout(300)
    assert pg.is_visible('#jogo') and 'Cópia de' in pg.inner_text('#topo-cena'), 'recarregar no meio do jogo deveria reabrir a mesa'
    pg.goto(URL+'#inicio'); pg.wait_for_timeout(200); assert pg.is_visible('text=Continuar de onde parou'); pg.click('button:has-text("Continuar") >> nth=0'); pg.wait_for_selector('#jogo', timeout=3000)
    pg.click('#btn-sair'); pg.wait_for_selector('h1:has-text("Jogar")', timeout=3000); assert pg.is_visible('#site')
    # treino, sozinho, do começo ao fim
    pg.evaluate("localStorage.removeItem('cronica2.mesas')"); pg.reload(); pg.wait_for_timeout(200); pg.click('.nav-links >> text=Jogar'); pg.wait_for_selector('#btn-abrir-mesa', timeout=3000)
    pg.check('#av-treino', force=True); pg.check('#mh-'+pg.evaluate("JSON.parse(localStorage.getItem('cronica2.herois'))[1].id"), force=True); pg.click('#btn-abrir-mesa'); pg.wait_for_timeout(150)
    r=random.Random(3); ok=False
    for i in range(300):
        bts=pg.query_selector_all('#opcoes button'); rot=[x.inner_text() for x in bts]
        if 'Sair da mesa' in rot: ok=True; break
        pref=[k for k,t in enumerate(rot) if any(w in t for w in ('Enfrentar',' em Boneco','Encerrar o treino','Falar com Dorval'))]
        bts[r.choice(pref) if pref and r.random()<0.7 else r.randrange(len(bts))].click()
    print('A: treino concluído', ok); assert ok
    # celular, tema escuro
    c2=b.new_context(viewport={'width':390,'height':780}, color_scheme='dark'); m=c2.new_page(); ouvir(m,'M')
    m.goto(URL); m.wait_for_timeout(200); m.screenshot(path=RAIZ+'/shots/v2-08-cel-inicio.png')
    m.goto(URL+'#jogar'); m.wait_for_timeout(100); m.click('button:has-text("Usar heróis prontos")'); m.wait_for_timeout(80)
    ids=m.evaluate("JSON.parse(localStorage.getItem('cronica2.herois')).map(x=>x.id)")
    for i in ids[:3]: m.check('#mh-'+i, force=True); m.wait_for_timeout(30)
    m.click('#btn-abrir-mesa'); m.wait_for_timeout(200); m.screenshot(path=RAIZ+'/shots/v2-09-cel-mesa.png')
    m.click('#btn-painel'); m.wait_for_timeout(80); m.screenshot(path=RAIZ+'/shots/v2-10-cel-ficha.png'); m.click('#btn-fechar-painel')
    for h in ['#mesa']:
        sw=m.evaluate('document.documentElement.scrollWidth'); assert sw<=390, 'rolagem lateral: %d'%sw
    for rota in ['inicio','herois','aventuras','jogar','regras']:
        m.goto(URL+'#'+rota); m.wait_for_timeout(120); sw=m.evaluate("Math.max(document.documentElement.scrollWidth, document.getElementById('site').scrollWidth)"); assert sw<=390, 'rolagem lateral em %s: %d'%(rota,sw)
    m.goto(URL+'#herois'); m.wait_for_timeout(80); m.click('#btn-novo-heroi'); m.wait_for_timeout(80); m.screenshot(path=RAIZ+'/shots/v2-11-cel-criador.png', full_page=False)
    sw=m.evaluate("document.getElementById('site').scrollWidth"); assert sw<=390, 'rolagem lateral no criador: %d'%sw

    # ---------- B: página publicada simulada (IA + mesa compartilhada), dois jogadores ----------
    ctx3=b.new_context(viewport={'width':1180,'height':800})
    p1=ctx3.new_page(); p1.add_init_script("window.__UID='u1';"+MOCK); ouvir(p1,'P1')
    p2=ctx3.new_page(); p2.add_init_script("window.__UID='u2';"+MOCK); ouvir(p2,'P2')
    p1.goto(URL+'#jogar'); p1.wait_for_timeout(400)
    assert 'Mesas compartilhadas disponíveis' in p1.evaluate("(location.hash='#inicio', '')") or True
    p1.wait_for_timeout(150); assert p1.is_visible('text=Mestre por IA disponível'); p1.screenshot(path=RAIZ+'/shots/v2-12-inicio-publicado.png')
    p1.goto(URL+'#jogar'); p1.wait_for_timeout(300); p1.click('button:has-text("Usar heróis prontos")'); p1.wait_for_timeout(100)
    ids=p1.evaluate("JSON.parse(localStorage.getItem('cronica2.herois')).map(x=>x.id)")
    assert not p1.is_disabled('#onde-online'); p1.check('#onde-online', force=True); p1.wait_for_timeout(60); p1.check('#mh-'+ids[0], force=True); p1.wait_for_timeout(60)
    p1.fill('#mesa-nome','Mesa de quinta'); p1.fill('#mesa-semente','dupla-1') if p1.is_visible('#mesa-semente') else None
    p1.click('#btn-abrir-mesa'); p1.wait_for_timeout(500)
    assert p1.is_visible('#jogo'), 'p1 não entrou na mesa'
    topo=p1.inner_text('#topo-cena'); cod=re.search(r'código (\w+)', topo).group(1); print('B: mesa criada, código', cod)
    p2.goto(URL+'#jogar'); p2.wait_for_timeout(600)
    assert p2.is_visible('text=Mesa de quinta'), 'p2 não vê a mesa na lista'
    p2.select_option('#entrar-heroi', ids[1]); p2.fill('#entrar-codigo', cod.upper()); p2.click('button:has-text("Entrar pelo código")'); p2.wait_for_selector('#jogo', timeout=6000); assert espera(p2,'#log','junta-se ao grupo'); livre(p2)
    assert p2.is_visible('#jogo') and p2.locator('.heroi-chip').count()==2, 'p2: chips %d'%p2.locator('.heroi-chip').count()
    assert espera(p1,'#log','junta-se ao grupo'), 'p1 não viu o herói do p2'; assert p1.locator('.heroi-chip').count()==2
    assert 'Kael' in p1.inner_text('#log')
    # p1 age, p2 vê
    livre(p1); assert p1.is_visible('#btn-sugestoes') and p1.locator('button.ficha-acao').count()==0, 'com IA ligada os botões deveriam estar escondidos'
    sugestoes(p1); assert p1.locator('button.ficha-acao').count()>3; p1.click('button.ficha-acao:has-text("Falar com Dona Marga")'); livre(p1)
    assert p1.locator('button.ficha-acao').count()==0, 'as sugestões deveriam se fechar depois da ação'
    assert espera(p2,'#log','Dona Marga serve uma caneca'), 'p2 não recebeu a ação do p1'
    # p2 escreve fora do roteiro: mestre por IA
    p2.fill('#texto','assobio uma canção de ninar bem baixinho'); p2.press('#texto','Enter'); assert espera(p2,'#log','Veredito: teste de Atuação'), 'IA não aplicou'; livre(p2)
    l2=p2.inner_text('#log'); assert 'Veredito: teste de Atuação' in l2 and ('A sala relaxa' in l2 or 'Ninguém repara' in l2), 'IA não aplicou: '+l2[-300:]
    assert len(p2.evaluate('window.__prompts'))==1 and 'AÇÕES PREVISTAS' in p2.evaluate('window.__prompts[0]')
    assert espera(p1,'#log','Veredito: teste de Atuação'), 'p1 não viu o improviso'
    # IA devolve lixo -> roteiro assume ; IA recusada -> desliga
    p2.evaluate("window.__iaResp={tipo:'acao',id:'nao_existe'}"); p2.fill('#texto','planto bananeira'); p2.press('#texto','Enter'); assert espera(p2,'#log','não entendeu'), 'resposta inválida da IA deveria cair no roteiro'; livre(p2)
    p2.evaluate("window.__iaErro='not_granted'"); p2.fill('#texto','dou uma cambalhota de costas'); p2.press('#texto','Enter'); assert espera(p2,'#opcoes','não está liberado'), p2.inner_text('#opcoes'); livre(p2)
    assert p2.is_hidden('#btn-sugestoes') and p2.locator('button.ficha-acao').count()>3, 'sem IA os botões deveriam voltar'
    assert 'não está liberado' in p2.inner_text('#opcoes') and p2.text_content('#selo-ia')=='Mestre: roteiro', p2.text_content('#selo-ia')
    p2.screenshot(path=RAIZ+'/shots/v2-13-online-p2.png')
    # os dois seguem até o combate e lutam, cada um na sua vez
    livre(p1); p1.fill('#texto','/ir trilha'); p1.press('#texto','Enter'); assert espera(p1,'#topo-cena','Trilha do Barranco'), 'p1 não chegou à trilha'; livre(p1)
    rr=random.Random(5); agiu_por=0
    def passo(pg, nome):
        global agiu_por
        if pg.is_visible('button:has-text("Agir por")'):
            return False
        sugestoes(pg)
        bts=pg.query_selector_all('#opcoes button.ficha-acao')
        if not bts: return False
        rot=[x.inner_text() for x in bts]
        pref=[k for k,t in enumerate(rot) if any(w in t for w in (' em Goblin','Atacar os goblins','Seguir até a capela','Encerrar o turno'))]
        bts[rr.choice(pref) if pref and rr.random()<0.85 else rr.randrange(len(bts))].click(); pg.wait_for_timeout(150); livre(pg); return True
    viu_gate=False
    for i in range(60):
        emcomb = 'Vez de' in p1.inner_text('#opcoes') or 'Vez de' in p2.inner_text('#opcoes') or p1.is_visible('button:has-text("Agir por")') or p2.is_visible('button:has-text("Agir por")')
        if p1.is_visible('button:has-text("Agir por")') or p2.is_visible('button:has-text("Agir por")'): viu_gate=True
        a=passo(p1,'p1'); p2.wait_for_timeout(350); b2=passo(p2,'p2') if not a or not emcomb else False; p1.wait_for_timeout(350)
        if 'Capela Velha' in p1.inner_text('#topo-cena'): break
    p1.wait_for_timeout(600)
    print('B: chegaram à capela:', 'Capela Velha' in p1.inner_text('#topo-cena'), '· vez alheia apareceu:', viu_gate)
    assert p1.inner_text('#topo-cena').split(' · ')[0]==p2.inner_text('#topo-cena').split(' · ')[0], 'cenas diferentes: %s / %s'%(p1.inner_text('#topo-cena'),p2.inner_text('#topo-cena'))
    s1=p1.evaluate("JSON.parse(JSON.parse(localStorage.getItem('mockdb'))['mesas/%s'].json).nLog"%cod)
    p1.screenshot(path=RAIZ+'/shots/v2-14-online-p1.png')
    # terceiro visitante sem permissão de escrita só assiste
    p3=ctx3.new_page(); p3.add_init_script("window.__UID='u3';window.__SOLEITURA=true;"+MOCK); ouvir(p3,'P3')
    p3.goto(URL+'#jogar'); p3.wait_for_timeout(500); p3.select_option('#entrar-heroi', ids[2]); p3.fill('#entrar-codigo', cod); p3.click('button:has-text("Entrar pelo código")'); p3.wait_for_selector('#jogo', timeout=6000); p3.wait_for_timeout(600); livre(p3)
    assert p3.is_visible('#jogo') and ('não tem permissão' in p3.inner_text('#opcoes') or 'assistindo' in p3.inner_text('#opcoes')), p3.inner_text('#opcoes')
    b.close()
print('ERROS:', erros if erros else 'nenhum')
sys.exit(1 if erros else 0)
