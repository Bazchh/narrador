  /* ---------------- mesa compartilhada: o estado mora na página, um jogador escreve por vez ---------------- */
  var QUEM = 'j' + codigo(10), carregandoIndice = false;

  function comPrazo(p, ms) {
    return new Promise(function (ok, falha) {
      var t = setTimeout(function () { falha({ code: 'prazo' }); }, ms);
      Promise.resolve(p).then(function (v) { clearTimeout(t); ok(v); }, function (e) { clearTimeout(t); falha(e); });
    });
  }
  function lerEstado(d) {
    if (!d || typeof d.json !== 'string') return null;
    var S;
    try { S = JSON.parse(d.json); } catch (e) { return null; }
    return C.validar(S) ? S : null;
  }
  function empacotar(S) {
    var j = JSON.stringify(C.compactar(S, 150, 80));
    if (j.length > 200000) j = JSON.stringify(C.compactar(S, 70, 30));
    return j;
  }
  function erroOnline(e) {
    var c = e && e.code;
    if (c === 'prazo') return 'A mesa demorou demais para responder. Confira a internet e tente de novo.';
    if (c === 'sem_permissao') return 'Você pode ver esta mesa, mas não tem permissão para mudar nada nela. Peça a quem abriu a mesa para liberar a sua participação.';
    if (c === 'cheio') return 'O jogo atingiu o limite de dados guardados. Apague mesas antigas e tente de novo.';
    if (c === 'sem_acesso') return 'O acesso a esta mesa foi retirado.';
    if (c === 'sumiu') return 'Esta mesa não existe mais.';
    return 'Não foi possível falar com a mesa agora. Tente de novo em instantes.';
  }
  function gravarIndice(id, nome, S) {
    try {
      cap.mesas.gravarIndice(id, { nome: nome, av: S.av, herois: S.herois.map(function (h) { return h.nome; }).join(', '), fim: !!S.fim }).catch(nada);
    } catch (e) { /* o índice é só uma lista de conveniência */ }
  }
  function assinaturaIndice(S) { return S.herois.map(function (h) { return h.nome; }).join(',') + '|' + (S.fim ? 1 : 0); }
  function gravarPontoSeguro(id, S) {
    if (!S.ckpt) return;
    try { cap.mesas.gravarPonto(id, { json: JSON.stringify(C.compactar(S.ckpt, 60, 30)) }).catch(nada); } catch (e) { /* segue sem ponto seguro */ }
  }
  // Trava curta de "um por vez". Se outro jogador acabou de agir, espera a trava dele vencer e tenta de novo.
  function travar(id, tentativa) {
    tentativa = tentativa || 0;
    var p;
    try { p = Promise.resolve(cap.mesas.travarMesa(id, QUEM, 2500)); } catch (e) { return Promise.resolve(true); }
    return p.then(function (livre) {
      if (livre !== false) return true;
      if (tentativa >= 4) return false;
      return new Promise(function (ok) { setTimeout(ok, 900); }).then(function () { return travar(id, tentativa + 1); });
    }, function () { return true; });
  }
  function assinar(m) {
    try {
      m.parar = cap.mesas.escutarMesa(m.id, function (d) {
        if (M !== m) return;
        if (!d || typeof d.rev !== 'number' || d.rev <= m.rev) return;
        if (ocupado) { m.pendente = true; return; }
        var S = lerEstado(d);
        if (!S) return;
        m.S = S; m.rev = d.rev;
        if (rotaDesenhada === 'mesa') desenharMesa(false);
      }, function () {
        if (M !== m) return;
        avisoMesa = 'A ligação ao vivo com a mesa caiu. Suas ações continuam valendo; para ver as dos outros, saia e entre de novo na mesa.';
        if (rotaDesenhada === 'mesa') desenharOpcoes();
      });
    } catch (e) { m.parar = null; }
  }

  function aplicarOnline(fn) {
    var m = M, id = m.id, loja = cap.mesas;
    ocupado = true; avisoMesa = null;
    desenharOpcoes();
    function fim(msg) {
      ocupado = false;
      if (msg) avisoMesa = msg;
      if (M !== m) return;
      if (m.pendente) { m.pendente = false; loja.lerMesa(id).then(function (d) { var S = d && d.rev > m.rev ? lerEstado(d) : null; if (S && M === m && !ocupado) { m.S = S; m.rev = d.rev; desenharMesa(false); } }).catch(nada); }
      desenharMesa(false);
    }
    return comPrazo(travar(id, 0), 15000).then(function (livre) {
      if (!livre) { fim('Outro jogador está agindo neste instante. Tente de novo em alguns segundos.'); return; }
      return comPrazo(loja.lerMesa(id), 12000).then(function (d) {
        if (!d) throw { code: 'sumiu' };
        var S = lerEstado(d);
        if (!S) throw { code: 'sumiu' };
        var r = fn(S);
        if (r && C.validar(r)) S = r;
        var novo = { v: 2, rev: (d.rev | 0) + 1, nome: d.nome || m.nome, json: empacotar(S) };
        return comPrazo(loja.gravarMesa(id, novo), 12000).then(function () {
          if ((S.nCkpt || 0) !== m.nCkpt) { m.nCkpt = S.nCkpt || 0; gravarPontoSeguro(id, S); }
          var as = assinaturaIndice(S);
          if (as !== m.assinatura) { m.assinatura = as; gravarIndice(m.id, novo.nome, S); }
          m.S = JSON.parse(novo.json); m.rev = novo.rev;
          fim(avisoMesa);
        });
      });
    }).catch(function (e) { fim(erroOnline(e)); });
  }

  function criarMesaOnline(nome, o, fichas) {
    if (!onlineOk() || ocupado) return;
    ocupado = true;
    o.herois = fichas.map(function (f) { var c = JSON.parse(JSON.stringify(f)); c.dono = cap.uid; return c; });
    var S = C.novo(o), id = codigo(6);
    comPrazo(cap.mesas.lerMesa(id), 12000).then(function (ja) {
      if (ja) id = codigo(7);
      return comPrazo(cap.mesas.gravarMesa(id, { v: 2, rev: 1, nome: nome, json: empacotar(S) }), 12000);
    }).then(function () {
      ocupado = false;
      gravarIndice(id, nome, S); gravarPontoSeguro(id, S);
      lembrarOnline(id, nome); indiceOnline = null;
      rascunhoMesa.nome = ''; rascunhoMesa.semente = '';
      var m = { tipo: 'online', id: id, nome: nome, S: JSON.parse(empacotar(S)), rev: 1, nCkpt: S.nCkpt || 0, assinatura: assinaturaIndice(S) };
      assinar(m);
      entrarNaMesa(m);
    }).catch(function (e) { ocupado = false; msgJogar = { ok: false, x: erroOnline(e) }; redesenharPagina(); });
  }

  function abrirMesaOnline(id, heroiId) {
    if (!onlineOk() || ocupado) return;
    id = String(id || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    if (!id) return;
    ocupado = true;
    comPrazo(cap.mesas.lerMesa(id), 12000).then(function (d) {
      ocupado = false;
      var S = lerEstado(d);
      if (!S) { esquecerOnline(id); msgJogar = { ok: false, x: 'Não achei uma mesa com o código ' + id + '. Confira com quem abriu a mesa.' }; if (rotaDesenhada !== 'jogar') irPara('jogar'); else redesenharPagina(); return; }
      var m = { tipo: 'online', id: id, nome: String(d.nome || 'Mesa').slice(0, 40), S: S, rev: d.rev | 0, nCkpt: S.nCkpt || 0, assinatura: assinaturaIndice(S) };
      lembrarOnline(id, m.nome);
      assinar(m);
      entrarNaMesa(m);
      var p = heroiId ? doElenco(heroiId) : null;
      if (p && !meus().length && !S.fim && !S.combate && S.herois.length < C.MAX_HEROIS) {
        var ficha = JSON.parse(JSON.stringify(p.ficha)); ficha.dono = cap.uid;
        aplicar(function (X) { var er = C.entrarHeroi(X, ficha); if (er) avisoMesa = er; });
      } else if (p && !meus().length && !S.fim) {
        avisoMesa = S.combate ? 'O grupo está em combate. Quando a luta acabar, entre com seu personagem pela aba Mesa.' : 'A mesa já está cheia. Você pode assistir.';
        desenharOpcoes();
      }
    }).catch(function (e) { ocupado = false; msgJogar = { ok: false, x: erroOnline(e) }; if (rotaDesenhada !== 'jogar') irPara('jogar'); else redesenharPagina(); });
  }

  function voltarOnline() {
    var m = M;
    ocupado = true; desenharOpcoes();
    comPrazo(cap.mesas.lerPonto(m.id), 12000).then(function (d) {
      ocupado = false;
      var base = d ? lerEstado(d) : null;
      if (!base) { avisoMesa = 'Não há ponto seguro guardado para esta mesa.'; if (M === m) desenharOpcoes(); return; }
      return aplicar(function (S) { return C.voltarPontoSeguro(S, base); }).then(function () { if (M === m) desenharMesa(true); });
    }).catch(function (e) { ocupado = false; avisoMesa = erroOnline(e); if (M === m) desenharOpcoes(); });
  }

  function carregarIndice(forcar) {
    if (!onlineOk() || carregandoIndice || (!forcar && indiceOnline !== null)) return;
    carregandoIndice = true;
    var q;
    try { q = cap.mesas.listarIndice(30); } catch (e) { carregandoIndice = false; indiceErro = true; indiceOnline = []; return; }
    comPrazo(q, 12000).then(function (lista) {
      var l = [];
      (Array.isArray(lista) ? lista : []).forEach(function (d) {
        var x = d ? d.dado : null;
        if (x && typeof x.nome === 'string') l.push({ id: d.id, nome: x.nome.slice(0, 40), av: x.av, herois: String(x.herois || '').slice(0, 80), fim: !!x.fim });
      });
      indiceOnline = l; indiceErro = false;
    }).catch(function () { indiceOnline = []; indiceErro = true; }).then(function () {
      carregandoIndice = false;
      if (rotaDesenhada === 'jogar') redesenharPagina();
    });
  }
