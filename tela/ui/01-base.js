  /* Crônica 2 — o site. Só desenha e repassa a entrada: nenhuma regra mora aqui. */
  var C = window.Cronica;
  var K_HEROIS = 'cronica2.herois', K_MESAS = 'cronica2.mesas', K_MESA = 'cronica2.mesa.', K_ONLINE = 'cronica2.online', K_PREFS = 'cronica2.prefs';
  var MAX_ELENCO = 12, MAX_MESAS = 6;

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }
  function limpar(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function por(pai) { for (var i = 1; i < arguments.length; i++) if (arguments[i]) pai.appendChild(arguments[i]); return pai; }
  function botao(txt, cls, fn) {
    var b = el('button', 'botao' + (cls ? ' ' + cls : ''), txt);
    b.type = 'button';
    if (fn) b.addEventListener('click', fn);
    return b;
  }
  function link(txt, rota, cls) { var a = el('a', cls || null, txt); a.href = '#' + rota; return a; }
  function nada() {}
  function codigo(n) {
    var abc = 'abcdefghjkmnpqrstuvwxyz23456789', s = '';
    for (var i = 0; i < n; i++) s += abc.charAt(Math.floor(Math.random() * abc.length));
    return s;
  }
  function avatar(nome, cor, pequeno) {
    var a = el('span', 'avatar cor-' + (C.CORES.indexOf(cor) >= 0 ? cor : 'verde') + (pequeno ? ' pequeno' : ''), (String(nome || '?').trim().charAt(0) || '?').toUpperCase());
    a.setAttribute('aria-hidden', 'true');
    return a;
  }

  /* ---------------- guardar no navegador (com reserva em memória) ---------------- */
  var memoria = {}, armazenaOk = true;
  function ler(k, padrao) {
    try {
      var t = window.localStorage.getItem(k);
      if (t == null) return Object.prototype.hasOwnProperty.call(memoria, k) ? memoria[k] : padrao;
      return JSON.parse(t);
    } catch (e) { return Object.prototype.hasOwnProperty.call(memoria, k) ? memoria[k] : padrao; }
  }
  function gravar(k, v) {
    memoria[k] = v;
    try { window.localStorage.setItem(k, JSON.stringify(v)); armazenaOk = true; }
    catch (e) { armazenaOk = false; }
  }
  function apagar(k) {
    delete memoria[k];
    try { window.localStorage.removeItem(k); } catch (e) { /* sem armazenamento */ }
  }

  var prefs = ler(K_PREFS, {});
  if (!prefs || typeof prefs !== 'object') prefs = {};

  /* ---------------- elenco: os personagens do jogador ---------------- */
  var elenco = ler(K_HEROIS, []);
  if (!Array.isArray(elenco)) elenco = [];
  elenco = elenco.filter(function (p) { return p && typeof p.id === 'string' && p.ficha && typeof p.ficha === 'object'; }).slice(0, MAX_ELENCO);
  function salvarElenco() { gravar(K_HEROIS, elenco); elencoParaNuvem(); }
  function doElenco(id) { for (var i = 0; i < elenco.length; i++) if (elenco[i].id === id) return elenco[i]; return null; }
  var PRONTOS = [
    { nome: 'Brenna', especie: 'anao', classe: 'guerreiro', kit: 'escudo', antecedente: 'soldado', cor: 'bronze', aparencia: 'baixa, ombros largos, trança ruiva presa com arame', historia: 'Guardou portões de mina por dez anos e cansou de ficar parada.' },
    { nome: 'Kael', especie: 'halfling', classe: 'ladino', kit: 'rapieira', antecedente: 'criminoso', cor: 'cinza', aparencia: 'pequeno, capuz puído, sorriso rápido demais', historia: 'Abria fechaduras por encomenda na cidade grande até abrir a errada.' },
    { nome: 'Maud', especie: 'humano', classe: 'clerigo', kit: 'protetor', antecedente: 'acolito', cor: 'azul', aparencia: 'alta, cabelo raspado, um sino pequeno pendurado no cinto', historia: 'Saiu do mosteiro para ver se a fé aguenta o mundo de fora.' },
    { nome: 'Orim', especie: 'elfo', classe: 'mago', kit: 'cajado', antecedente: 'sabio', cor: 'roxo', aparencia: 'magro, dedos manchados de tinta, olhos claros', historia: 'Copiava livros alheios e decidiu que era hora de viver algo que valesse um.' }
  ];

  /* ---------------- o que esta cópia do jogo tem ligado: mestre por IA, mesas compartilhadas, quem está jogando ---------------- */
  var cap = { mestre: null, mesas: null, uid: null, pronto: false, iaFalhou: false, origem: 'nenhuma' };
  function onlineOk() { return !!(cap.mesas && cap.uid); }
  function iaDisponivel() { return !!cap.mestre && !cap.iaFalhou; }
  function iaLigada() { return iaDisponivel() && prefs.ia !== false; }
  function contaIA() { return cap.origem === 'claude' ? ' Cada consulta usa a conta Claude de quem está jogando.' : ''; }
  function carregarCapacidades() {
    var e = null;
    try { e = escolherEncaixe(); } catch (x) { e = null; }
    if (!e) { cap.pronto = true; return; }
    cap.origem = e.origem;
    var falta = 2;
    function fim() { if (--falta <= 0) { cap.pronto = true; } capMudou(); }
    Promise.resolve().then(e.ligarMestre).then(function (m) { cap.mestre = m || null; }).catch(nada).then(fim);
    Promise.resolve().then(e.ligarMesas).then(function (r) {
      if (r && r.mesas && typeof r.quem === 'string' && r.quem) { cap.mesas = r.mesas; cap.uid = r.quem; }
      if (onlineOk()) elencoDaNuvem();
    }).catch(nada).then(fim);
  }

  /* ---------------- elenco na conta (quando a página tem onde guardar) ---------------- */
  var nuvemTimer = null, nuvemOk = true;
  function elencoDaNuvem() {
    try {
      cap.mesas.lerElenco().then(function (d) {
        var remoto = [];
        if (d) { try { remoto = JSON.parse(d.json || '[]'); } catch (e) { remoto = []; } }
        if (!Array.isArray(remoto)) remoto = [];
        var mudou = false;
        remoto.forEach(function (p) {
          if (p && typeof p.id === 'string' && p.ficha && !doElenco(p.id) && elenco.length < MAX_ELENCO) { elenco.push({ id: p.id, ficha: C.normalizarFicha(p.ficha) }); mudou = true; }
        });
        if (mudou) { gravar(K_HEROIS, elenco); capMudou(); }
        if (elenco.some(function (p) { return !remoto.some(function (q) { return q && q.id === p.id; }); })) elencoParaNuvem();
      }).catch(function () { nuvemOk = false; });
    } catch (e) { nuvemOk = false; }
  }
  function elencoParaNuvem() {
    if (!onlineOk() || !nuvemOk) return;
    if (nuvemTimer) clearTimeout(nuvemTimer);
    nuvemTimer = setTimeout(function () {
      nuvemTimer = null;
      try { cap.mesas.gravarElenco({ json: JSON.stringify(elenco) }).catch(function () { nuvemOk = false; }); } catch (e) { nuvemOk = false; }
    }, 1500);
  }

  /* ---------------- mesas guardadas neste navegador ---------------- */
  function indiceMesas() {
    var l = ler(K_MESAS, []);
    return Array.isArray(l) ? l.filter(function (m) { return m && typeof m.id === 'string'; }) : [];
  }
  function resumoMesa(id, nome, S) {
    return { id: id, nome: nome, av: S.av, herois: S.herois.map(function (h) { return h.nome; }).join(', '), cena: S.fim ? (S.fim.tipo === 'vitoria' ? 'Aventura concluída' : 'Derrota') : C.infoCena(S).nome, quando: Date.now() };
  }
  function salvarMesaLocal(id, nome, S) {
    gravar(K_MESA + id, S);
    var l = indiceMesas().filter(function (m) { return m.id !== id; });
    l.unshift(resumoMesa(id, nome, S));
    l.slice(MAX_MESAS).forEach(function (m) { apagar(K_MESA + m.id); });
    gravar(K_MESAS, l.slice(0, MAX_MESAS));
  }
  function lerMesaLocal(id) {
    var S = ler(K_MESA + id, null);
    return C.validar(S) ? S : null;
  }
  function apagarMesaLocal(id) {
    apagar(K_MESA + id);
    gravar(K_MESAS, indiceMesas().filter(function (m) { return m.id !== id; }));
  }
  function mesasOnline() {
    var l = ler(K_ONLINE, []);
    return Array.isArray(l) ? l.filter(function (m) { return m && typeof m.id === 'string'; }) : [];
  }
  function lembrarOnline(id, nome) {
    var l = mesasOnline().filter(function (m) { return m.id !== id; });
    l.unshift({ id: id, nome: nome });
    gravar(K_ONLINE, l.slice(0, 8));
  }
  function esquecerOnline(id) { gravar(K_ONLINE, mesasOnline().filter(function (m) { return m.id !== id; })); }

  /* ---------------- estado da mesa aberta e navegação ---------------- */
  // M: { tipo: 'local'|'online', id, nome, S, sel (herói escolhido), rev, ref, parar, nCkpt }
  var M = null, ocupado = false, avisoMesa = null;
  var ROTAS = ['inicio', 'herois', 'aventuras', 'jogar', 'regras', 'mesa'];
  var paginas = {};
  function rota() {
    var h = String(window.location.hash || '').replace(/^#/, '');
    return ROTAS.indexOf(h) >= 0 ? h : 'inicio';
  }
  function irPara(r) {
    if (rota() === r) { desenharRota(); return; }
    try { window.location.hash = '#' + r; } catch (e) { desenharRota(); }
    // se o navegador não avisar a mudança, desenha assim mesmo
    setTimeout(function () { if (rotaDesenhada !== rota()) desenharRota(); }, 60);
  }
  var rotaDesenhada = null;
  function desenharRota() {
    var r = rota();
    if (r === 'mesa' && !M) {
      // página recarregada no meio do jogo: reabre a última mesa deste aparelho
      var ult = ler('cronica2.ultima', null), Su = typeof ult === 'string' ? lerMesaLocal(ult) : null;
      if (Su) { var reg = indiceMesas().filter(function (x) { return x.id === ult; })[0]; M = { tipo: 'local', id: ult, nome: reg ? reg.nome : 'Mesa', S: Su, sel: null, liberado: null }; }
      else { r = 'jogar'; try { window.location.hash = '#jogar'; } catch (e) { /* segue */ } }
    }
    rotaDesenhada = r;
    if (r === 'mesa') { $('site').hidden = true; $('jogo').hidden = false; desenharMesa(true); return; }
    if (M) fecharMesa();
    document.body.classList.remove('painel-aberto');
    $('jogo').hidden = true; $('site').hidden = false;
    var links = document.querySelectorAll('.nav-links a');
    for (var i = 0; i < links.length; i++) {
      if (links[i].getAttribute('data-rota') === r) links[i].setAttribute('aria-current', 'page'); else links[i].removeAttribute('aria-current');
    }
    var pg = $('pagina');
    limpar(pg);
    paginas[r](pg);
    $('site').scrollTop = 0;
  }
  function redesenharPagina() {
    if (rotaDesenhada && rotaDesenhada !== 'mesa') {
      var topo = $('site').scrollTop, pg = $('pagina'), foco = document.activeElement && document.activeElement.id;
      limpar(pg); paginas[rotaDesenhada](pg);
      $('site').scrollTop = topo;
      if (foco && $(foco) && pg.contains($(foco))) { try { $(foco).focus({ preventScroll: true }); } catch (e) { /* sem foco */ } }
    }
  }
  function capMudou() {
    if (rotaDesenhada === 'mesa') { if (M) desenharMesa(false); }
    else if (rotaDesenhada === 'inicio' || rotaDesenhada === 'jogar' || (rotaDesenhada === 'herois' && !editor)) redesenharPagina();
  }
