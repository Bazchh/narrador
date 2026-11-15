  /* ================= ENCAIXES =================
     Este é o ÚNICO arquivo que sabe quem atende o mestre por IA e quem guarda as mesas compartilhadas.
     O resto do jogo só conhece dois serviços neutros:

       mestre.perguntar(pedido, sinal)  -> promessa com a resposta do mestre (um objeto)
       mesas.*                          -> ler, gravar, escutar e travar mesas; ponto seguro; índice; elenco

     Erros chegam sempre com um destes códigos, venham de onde vierem:
       mestre: cancelado | limite | sessao | recusou | fora | falha
       mesas : prazo | sem_permissao | cheio | sem_acesso | sumiu | falha

     Para mudar o jogo de casa, basta preencher ENDERECO_DO_SERVIDOR. Nada mais no jogo precisa mudar. */

  var ENDERECO_DO_SERVIDOR = '';   // vazio = usa o que a página oferecer; ex.: 'https://cronica.exemplo.com/api'

  /* ---------- versão de teste: escolher o modelo e medir o tamanho das consultas ---------- */
  var MODO_TESTE = false;
  // preços em dólar por milhão de tokens (entrada, saída), para a estimativa do medidor
  var MODELOS = [
    { id: '', nome: 'Rápido (padrão do jogo)', tier: 'quick' },
    { id: 'claude-haiku-5-5', nome: 'Haiku 5.5', tier: 'quick', ent: 0.10, sai: 0.50 },
    { id: 'claude-sonnet-5-5', nome: 'Sonnet 5.5', tier: 'default', ent: 2, sai: 10 },
    { id: 'claude-opus-5-5', nome: 'Opus 5.5', tier: 'complex', ent: 4, sai: 20 }
  ];
  var NIVEL = { quick: 'rápido', 'default': 'intermediário', complex: 'mais capaz' };
  var LETRAS_POR_TOKEN = 3.3;
  var medidor = { n: 0, enviado: 0, recebido: 0, ultimo: null };
  function modeloDe(id) { for (var i = 0; i < MODELOS.length; i++) if (MODELOS[i].id === id) return MODELOS[i]; return MODELOS[0]; }
  function custoEstimado(m) { return (medidor.enviado / LETRAS_POR_TOKEN * m.ent + medidor.recebido / LETRAS_POR_TOKEN * m.sai) / 1e6; }
  function lerJSON(t) {
    t = String(t == null ? '' : t).trim();
    try { return JSON.parse(t); } catch (e) { /* tenta os outros formatos */ }
    var c = t.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (c) { try { return JSON.parse(c[1]); } catch (e2) { /* segue */ } }
    var a = t.indexOf('{'), b = t.lastIndexOf('}');
    if (a >= 0 && b > a) { try { return JSON.parse(t.slice(a, b + 1)); } catch (e3) { /* sem JSON */ } }
    return undefined;
  }

  function erroCom(mapa, padrao) {
    return function (e) { throw { code: (e && mapa[e.code]) || padrao }; };
  }

  /* ---------- encaixe 1: página publicada no Claude ---------- */
  function encaixeClaude(cl) {
    var IA = { cancelled: 'cancelado', rate_limited: 'limite', session_expired: 'sessao', refused: 'recusou', not_granted: 'fora', sampling_disabled: 'fora', not_declared: 'fora', capability_disabled: 'fora', capability_removed: 'fora' };
    var DB = { invalid_argument: 'sem_permissao', quota_exceeded: 'cheio', revoked: 'sem_acesso', not_granted: 'sem_acesso' };
    var erroIA = erroCom(IA, 'falha'), erroDB = erroCom(DB, 'falha');
    function dado(snap) { return snap && snap.exists ? snap.data() : null; }
    function ligarMestre() {
      return Promise.resolve().then(function () { return cl.use('sample'); }).then(function (s) {
        if (typeof s !== 'function') return null;
        return {
          perguntar: function (pedido, sinal, modeloId) {
            var o = { modelTier: 'quick' };
            if (sinal) o.signal = sinal;
            if (!MODO_TESTE) return Promise.resolve().then(function () { return s.json(pedido, o); }).catch(erroIA);
            // na versão de teste: modelo escolhido na tela, e a resposta vem como texto para poder medir
            var m = modeloDe(modeloId || ''), t0 = Date.now();
            o.modelTier = m.tier;
            if (m.id) { o.model = m.id; o.effort = 'low'; }
            return Promise.resolve().then(function () { return s(pedido + '\n\nResponda somente com o JSON pedido, sem nenhum texto antes ou depois.', o); }).catch(erroIA).then(function (r) {
              var texto = r && typeof r.text === 'string' ? r.text : '';
              medidor.n++; medidor.enviado += pedido.length; medidor.recebido += texto.length;
              medidor.ultimo = { pedido: m.nome, respondeu: r && r.modelApplied ? m.nome : 'nível ' + (NIVEL[r && r.modelTierApplied] || '?'), atendido: !m.id || !!(r && r.modelApplied), ms: Date.now() - t0, enviado: pedido.length, recebido: texto.length };
              var v = lerJSON(texto);
              if (v === undefined) throw { code: 'falha' };
              return v;
            });
          }
        };
      });
    }
    function ligarMesas() {
      return Promise.resolve().then(function () { return Promise.all([cl.use('db'), cl.use('user')]); }).then(function (r) {
        var db = r[0], user = r[1];
        if (!db || !user || typeof user.id !== 'function') return null;
        return Promise.resolve(user.id()).then(function (id) {
          if (typeof id !== 'string' || !id) return null;
          function mesa(i) { return db.doc('mesas/' + i); }
          function ponto(i) { return mesa(i).collection('extra').doc('ckpt'); }
          function elenco() { return db.doc('data/users/' + id + '/cronica'); }
          function faz(fn) { return Promise.resolve().then(fn).catch(erroDB); }
          return {
            quem: id,
            mesas: {
              lerMesa: function (i) { return faz(function () { return mesa(i).get().then(dado); }); },
              gravarMesa: function (i, d) { return faz(function () { return mesa(i).set(d); }); },
              escutarMesa: function (i, fn, erro) {
                return mesa(i).onSnapshot(function (snap) { fn(dado(snap)); }, function () { erro(); });
              },
              travarMesa: function (i, quem, ms) {
                return faz(function () { return mesa(i).acquire({ holder: quem, ttlMs: ms }); }).then(function (x) { return !(x && x.acquired === false); });
              },
              lerPonto: function (i) { return faz(function () { return ponto(i).get().then(dado); }); },
              gravarPonto: function (i, d) { return faz(function () { return ponto(i).set(d); }); },
              gravarIndice: function (i, d) { return faz(function () { return db.doc('indice/' + i).set(d); }); },
              listarIndice: function (n) {
                return faz(function () {
                  return db.collection('indice').limit(n).get().then(function (snap) {
                    return (snap && snap.docs ? snap.docs : []).map(function (x) { return { id: x.id, dado: x.data ? x.data() : null }; });
                  });
                });
              },
              lerElenco: function () { return faz(function () { return elenco().get().then(dado); }); },
              gravarElenco: function (d) { return faz(function () { return elenco().set(d); }); }
            }
          };
        });
      });
    }
    return { origem: 'claude', ligarMestre: ligarMestre, ligarMesas: ligarMesas };
  }

  /* ---------- encaixe 2: servidor próprio ----------
     O servidor precisa responder a estes endereços (tudo em JSON):
       GET  /estado                  -> { mestre: true|false, mesas: true|false }
       POST /mestre   { pedido }     -> a resposta do mestre (objeto)
       GET  /mesas/ID                -> a mesa, ou 404
       PUT  /mesas/ID                -> grava a mesa
       POST /mesas/ID/trava { quem, ms } -> { livre: true|false }
       GET  /mesas/ID/ponto , PUT /mesas/ID/ponto
       PUT  /indice/ID ; GET /indice?n=30 -> [ { id, dado } ]
       GET  /elenco/QUEM , PUT /elenco/QUEM
     Respostas de erro: 401 sessão, 403 sem permissão, 413 cheio, 422 recusou, 429 limite.
     A identidade ("quem") por enquanto é um código do aparelho; contas de verdade entram numa etapa futura. */
  function encaixeServidor(base) {
    base = String(base).replace(/\/+$/, '');
    var HTTP = { 401: 'sessao', 403: 'sem_permissao', 413: 'cheio', 422: 'recusou', 429: 'limite' };
    var quem = ler('cronica2.aparelho', null);
    if (typeof quem !== 'string' || !/^a[a-z0-9]{8,40}$/.test(quem)) { quem = 'a' + codigo(16); gravar('cronica2.aparelho', quem); }
    function pedir(metodo, caminho, corpo, sinal) {
      var o = { method: metodo, headers: { 'X-Cronica-Quem': quem } };
      if (corpo !== undefined) { o.headers['Content-Type'] = 'application/json'; o.body = JSON.stringify(corpo); }
      if (sinal) o.signal = sinal;
      return Promise.resolve().then(function () { return fetch(base + caminho, o); }).then(function (r) {
        if (r.status === 404) return null;
        if (!r.ok) throw { code: HTTP[r.status] || 'falha' };
        if (r.status === 204) return true;
        return r.json().catch(function () { throw { code: 'falha' }; });
      }, function (e) { throw { code: e && e.name === 'AbortError' ? 'cancelado' : 'falha' }; });
    }
    var estado = null;
    function verEstado() {
      if (!estado) estado = pedir('GET', '/estado').then(function (e) { return e && typeof e === 'object' ? e : {}; }, function () { return {}; });
      return estado;
    }
    function ligarMestre() {
      return verEstado().then(function (e) {
        if (!e.mestre) return null;
        return {
          perguntar: function (pedido, sinal) {
            return pedir('POST', '/mestre', { pedido: pedido }, sinal).then(function (r) {
              if (!r || typeof r !== 'object') throw { code: 'fora' };
              return r;
            });
          }
        };
      });
    }
    function ligarMesas() {
      return verEstado().then(function (e) {
        if (!e.mesas) return null;
        function m(i) { return '/mesas/' + encodeURIComponent(i); }
        return {
          quem: quem,
          mesas: {
            lerMesa: function (i) { return pedir('GET', m(i)); },
            gravarMesa: function (i, d) { return pedir('PUT', m(i), d); },
            escutarMesa: function (i, fn, erro) {
              var vivo = true, falhas = 0, avisou = false, t = null;
              function volta() {
                if (!vivo) return;
                pedir('GET', m(i)).then(function (d) { falhas = 0; avisou = false; if (vivo) fn(d); }, function () {
                  if (++falhas >= 4 && !avisou && vivo) { avisou = true; erro(); }
                }).then(function () { if (vivo) t = setTimeout(volta, 2500); });
              }
              t = setTimeout(volta, 2500);
              return function () { vivo = false; if (t) clearTimeout(t); };
            },
            travarMesa: function (i, q, ms) { return pedir('POST', m(i) + '/trava', { quem: q, ms: ms }).then(function (x) { return !(x && x.livre === false); }); },
            lerPonto: function (i) { return pedir('GET', m(i) + '/ponto'); },
            gravarPonto: function (i, d) { return pedir('PUT', m(i) + '/ponto', d); },
            gravarIndice: function (i, d) { return pedir('PUT', '/indice/' + encodeURIComponent(i), d); },
            listarIndice: function (n) { return pedir('GET', '/indice?n=' + (n | 0)).then(function (l) { return Array.isArray(l) ? l : []; }); },
            lerElenco: function () { return pedir('GET', '/elenco/' + quem); },
            gravarElenco: function (d) { return pedir('PUT', '/elenco/' + quem, d); }
          }
        };
      });
    }
    return { origem: 'servidor', ligarMestre: ligarMestre, ligarMesas: ligarMesas };
  }

  /* ---------- a escolha, num lugar só ---------- */
  function escolherEncaixe() {
    var end = typeof window.CRONICA_SERVIDOR === 'string' ? window.CRONICA_SERVIDOR : ENDERECO_DO_SERVIDOR;
    if (end && typeof fetch === 'function') return encaixeServidor(end);
    var cl = window.claude;
    if (cl && typeof cl.use === 'function') return encaixeClaude(cl);
    return null;
  }
