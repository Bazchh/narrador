  /* ---------------- página Jogar: continuar, abrir mesa nova, entrar em mesa compartilhada ---------------- */
  var rascunhoMesa = { av: 'sino', dif: 'tranquilo', onde: 'local', herois: [], nome: '', semente: '', codigo: '', heroiEntrar: '' };
  var indiceOnline = null, indiceErro = false, msgJogar = null;

  function opcaoCartao(grupo, valor, nome, txt, dados, marcado, desligado, aoMudar) {
    var l = el('label', 'cartao'), i = document.createElement('input');
    i.type = 'radio'; i.name = grupo; i.value = valor; i.id = grupo + '-' + valor; i.checked = !!marcado; i.disabled = !!desligado;
    i.addEventListener('change', function () { if (i.checked) aoMudar(valor); });
    var c = el('span', 'cartao-corpo');
    por(c, el('span', 'cartao-nome', nome), txt ? el('span', 'cartao-texto', txt) : null, dados ? el('span', 'cartao-dados', dados) : null);
    por(l, i, c);
    return l;
  }
  function opcaoMarca(tipo, grupo, valor, rot, marcado, desligado, aoMudar) {
    var l = el('label', 'marca-op'), i = document.createElement('input');
    i.type = tipo; i.name = grupo; i.value = valor; i.id = grupo + '-' + valor; i.checked = !!marcado; i.disabled = !!desligado;
    i.addEventListener('change', function () { aoMudar(valor, i.checked); });
    por(l, i, el('span', null, rot));
    return l;
  }
  function campoTexto(id, rot, valor, max, dica, aoMudar, multilinha) {
    var c = el('div', 'campo'), lb = el('label', null, rot), i = document.createElement(multilinha ? 'textarea' : 'input');
    lb.htmlFor = id; i.id = id; if (!multilinha) i.type = 'text';
    i.maxLength = max; i.value = valor || ''; if (dica) i.placeholder = dica;
    i.addEventListener('input', function () { aoMudar(i.value); });
    por(c, lb, i);
    return c;
  }
  function resumoFicha(f) {
    return C.ESPECIES[f.especie].nome + ' · ' + C.CLASSES[f.classe].nome + ' · ' + C.ANTECEDENTES[f.antecedente].nome;
  }

  function usarProntos() {
    PRONTOS.forEach(function (p) {
      if (elenco.length < MAX_ELENCO && !elenco.some(function (x) { return x.ficha.nome === p.nome; })) elenco.push({ id: 'p' + codigo(8), ficha: C.normalizarFicha(p) });
    });
    salvarElenco();
  }

  paginas.jogar = function (pg) {
    var s, g, f;
    rascunhoMesa.herois = rascunhoMesa.herois.filter(function (id) { return !!doElenco(id); });
    pg.appendChild(por(el('section', 'secao'), el('h1', null, 'Jogar'), el('p', 'lead', 'Continue uma mesa, abra uma nova ou entre na mesa de outra pessoa.')));
    if (msgJogar) { pg.appendChild(el('p', msgJogar.ok ? 'ok' : 'erro', msgJogar.x)); msgJogar = null; }

    /* continuar */
    var locais = indiceMesas(), conhecidas = onlineOk() ? mesasOnline() : [];
    if (locais.length || conhecidas.length) {
      s = secao('Continuar');
      g = el('div', 'grade');
      locais.forEach(function (m) {
        var c = el('article', 'caixa');
        por(c, el('span', 'rotulo', ((C.AVENTURAS[m.av] || {}).titulo || 'Aventura') + ' · neste aparelho'), el('h3', null, m.nome), el('p', 'sub', m.herois + ' · ' + m.cena));
        f = el('div', 'fila');
        por(f, botao('Continuar', 'primario', function () { abrirMesaLocal(m.id); }), botao('Apagar', 'perigo pequeno', function () { apagarMesaLocal(m.id); redesenharPagina(); }));
        c.appendChild(f); g.appendChild(c);
      });
      conhecidas.forEach(function (m) {
        var c = el('article', 'caixa');
        por(c, el('span', 'rotulo', 'Mesa compartilhada'), el('h3', null, m.nome), el('p', 'sub', 'Código ' + m.id));
        f = el('div', 'fila');
        por(f, botao('Abrir', 'primario', function () { abrirMesaOnline(m.id); }), botao('Tirar da lista', 'pequeno', function () { esquecerOnline(m.id); redesenharPagina(); }));
        c.appendChild(f); g.appendChild(c);
      });
      s.appendChild(g); pg.appendChild(s);
    }

    /* nova mesa */
    s = secao('Abrir uma mesa nova');
    var form = el('div', 'form');
    var cAv = por(el('fieldset', 'campo'), el('legend', null, 'Aventura'));
    g = el('div', 'cartoes');
    Object.keys(C.AVENTURAS).forEach(function (id) {
      var a = C.AVENTURAS[id];
      g.appendChild(opcaoCartao('av', id, a.titulo, a.resumo, a.duracao + ' · ' + a.nivel, rascunhoMesa.av === id, false, function (v) { rascunhoMesa.av = v; }));
    });
    cAv.appendChild(g); form.appendChild(cAv);

    var cDif = por(el('fieldset', 'campo'), el('legend', null, 'Modo de jogo'));
    g = el('div', 'cartoes');
    g.appendChild(opcaoCartao('dif', 'tranquilo', 'Tranquilo', 'Os inimigos causam metade do dano e ninguém morre. Para curtir a história e aprender as regras.', null, rascunhoMesa.dif === 'tranquilo', false, function (v) { rascunhoMesa.dif = v; }));
    g.appendChild(opcaoCartao('dif', 'classico', 'Clássico', 'Dano normal, e heróis podem morrer. Sozinho, exige tática; em grupo, pesa menos.', null, rascunhoMesa.dif === 'classico', false, function (v) { rascunhoMesa.dif = v; }));
    cDif.appendChild(g); form.appendChild(cDif);

    var cOnde = por(el('fieldset', 'campo'), el('legend', null, 'Onde a mesa fica'));
    g = el('div', 'cartoes');
    if (!onlineOk() && rascunhoMesa.onde === 'online') rascunhoMesa.onde = 'local';
    g.appendChild(opcaoCartao('onde', 'local', 'Neste aparelho', 'Sozinho, ou em grupo passando a vez na mesma tela. Funciona sem internet.', null, rascunhoMesa.onde === 'local', false, function (v) { rascunhoMesa.onde = v; redesenharPagina(); }));
    g.appendChild(opcaoCartao('onde', 'online', 'Mesa compartilhada', onlineOk() ? 'Cada pessoa entra com o próprio personagem, de onde estiver, e joga quando puder.' : (cap.pronto ? 'Indisponível nesta cópia do jogo. Precisa de um lugar na internet que guarde as mesas.' : 'Verificando se está disponível…'), null, rascunhoMesa.onde === 'online', !onlineOk(), function (v) { rascunhoMesa.onde = v; redesenharPagina(); }));
    cOnde.appendChild(g); form.appendChild(cOnde);

    var cH = por(el('fieldset', 'campo'), el('legend', null, 'Heróis (de 1 a ' + C.MAX_HEROIS + ')'));
    if (!elenco.length) {
      var av = el('div', 'aviso-caixa');
      av.appendChild(el('p', null, 'Você ainda não tem personagens. Crie o seu, do seu jeito, ou comece com quatro heróis prontos.'));
      f = el('div', 'fila'); f.style.marginTop = '10px';
      por(f, link('Criar personagem', 'herois', 'botao primario'), botao('Usar heróis prontos', null, function () { usarProntos(); redesenharPagina(); }));
      av.appendChild(f); cH.appendChild(av);
    } else {
      var m = el('div', 'marcas'), cheio = rascunhoMesa.herois.length >= C.MAX_HEROIS;
      elenco.forEach(function (p) {
        var marcado = rascunhoMesa.herois.indexOf(p.id) >= 0;
        m.appendChild(opcaoMarca('checkbox', 'mh', p.id, p.ficha.nome + ' (' + C.CLASSES[p.ficha.classe].nome + ')', marcado, cheio && !marcado, function (v, on) {
          rascunhoMesa.herois = rascunhoMesa.herois.filter(function (x) { return x !== v; });
          if (on && rascunhoMesa.herois.length < C.MAX_HEROIS) rascunhoMesa.herois.push(v);
          redesenharPagina();
        }));
      });
      cH.appendChild(m);
      f = el('div', 'fila');
      por(f, link('Criar ou editar personagens', 'herois'), elenco.length < 4 ? botao('Adicionar heróis prontos', 'pequeno', function () { usarProntos(); redesenharPagina(); }) : null);
      cH.appendChild(f);
      if (rascunhoMesa.onde === 'online') cH.appendChild(el('p', 'dica', 'Na mesa compartilhada, escolha só os heróis que você mesmo vai jogar. Os outros jogadores entram com os deles.'));
    }
    form.appendChild(cH);

    var cNome = campoTexto('mesa-nome', 'Nome da mesa (opcional)', rascunhoMesa.nome, 40, 'Ex.: Mesa de quinta', function (v) { rascunhoMesa.nome = v; });
    cNome.lastChild.classList.add('estreito');
    form.appendChild(cNome);
    var det = el('details');
    det.appendChild(el('summary', 'sub', 'Opção avançada: semente dos dados'));
    var cS = campoTexto('mesa-semente', 'Semente (em branco para sortear)', rascunhoMesa.semente, 40, 'Qualquer palavra ou número', function (v) { rascunhoMesa.semente = v; });
    cS.lastChild.classList.add('estreito'); cS.style.marginTop = '10px';
    cS.appendChild(el('p', 'dica', 'Com a mesma semente e as mesmas ações, os dados saem iguais. Serve para conferir que o jogo é justo.'));
    det.appendChild(cS); form.appendChild(det);

    var abrir = botao('Abrir a mesa', 'primario grande', function () {
      var ids = rascunhoMesa.herois.slice();
      if (!ids.length) { msgJogar = { ok: false, x: 'Escolha pelo menos um herói para abrir a mesa.' }; redesenharPagina(); return; }
      var fichas = ids.map(function (id) { return doElenco(id).ficha; });
      var nome = String(rascunhoMesa.nome || '').replace(/\s+/g, ' ').trim().slice(0, 40) || 'Mesa de ' + fichas[0].nome;
      var o = { av: rascunhoMesa.av, dificuldade: rascunhoMesa.dif, semente: String(rascunhoMesa.semente || '').trim() };
      if (rascunhoMesa.onde === 'online' && onlineOk()) { criarMesaOnline(nome, o, fichas); return; }
      o.herois = fichas;
      var S = C.novo(o), id = codigo(8);
      salvarMesaLocal(id, nome, S);
      rascunhoMesa.nome = ''; rascunhoMesa.semente = '';
      entrarNaMesa({ tipo: 'local', id: id, nome: nome, S: S });
    });
    abrir.id = 'btn-abrir-mesa';
    abrir.disabled = !elenco.length;
    form.appendChild(abrir);
    s.appendChild(form); pg.appendChild(s);

    /* entrar em mesa compartilhada */
    if (onlineOk()) {
      s = secao('Entrar numa mesa compartilhada');
      s.appendChild(el('p', 'lead', 'Peça o código a quem abriu a mesa, ou escolha uma da lista. Você entra com um personagem seu, na cena em que o grupo estiver.'));
      var sel = document.createElement('select'); sel.id = 'entrar-heroi'; sel.className = 'estreito';
      var vazio = el('option', null, elenco.length ? 'Só assistir, por enquanto' : 'Sem personagens: só assistir'); vazio.value = ''; sel.appendChild(vazio);
      elenco.forEach(function (p) { var op = el('option', null, 'Entrar com ' + p.ficha.nome + ' (' + C.CLASSES[p.ficha.classe].nome + ')'); op.value = p.id; sel.appendChild(op); });
      sel.value = doElenco(rascunhoMesa.heroiEntrar) ? rascunhoMesa.heroiEntrar : (elenco[0] ? elenco[0].id : '');
      rascunhoMesa.heroiEntrar = sel.value;
      sel.addEventListener('change', function () { rascunhoMesa.heroiEntrar = sel.value; });
      var lb = el('label', null, 'Seu personagem'); lb.htmlFor = 'entrar-heroi';
      s.appendChild(por(el('div', 'campo'), lb, sel));
      var cC = campoTexto('entrar-codigo', 'Código da mesa', rascunhoMesa.codigo, 12, 'Ex.: k7m2xq', function (v) { rascunhoMesa.codigo = v; });
      cC.lastChild.classList.add('estreito');
      s.appendChild(cC);
      f = el('div', 'fila');
      por(f, botao('Entrar pelo código', 'primario', function () {
        var cod = String(rascunhoMesa.codigo || '').toLowerCase().replace(/[^a-z0-9]/g, '');
        if (!cod) { msgJogar = { ok: false, x: 'Digite o código da mesa.' }; redesenharPagina(); return; }
        abrirMesaOnline(cod, rascunhoMesa.heroiEntrar);
      }), botao('Atualizar a lista', 'pequeno', function () { carregarIndice(true); }));
      s.appendChild(f);
      if (indiceErro) s.appendChild(el('p', 'dica', 'Não foi possível ler a lista de mesas agora. O código continua funcionando.'));
      else if (indiceOnline === null) { s.appendChild(el('p', 'dica', 'Procurando mesas abertas…')); carregarIndice(false); }
      else if (!indiceOnline.length) s.appendChild(el('p', 'dica', 'Nenhuma mesa compartilhada aberta nesta página ainda.'));
      else {
        g = el('div', 'grade');
        indiceOnline.forEach(function (m) {
          var c = el('article', 'caixa');
          por(c, el('span', 'rotulo', ((C.AVENTURAS[m.av] || {}).titulo || 'Aventura') + (m.fim ? ' · encerrada' : '')), el('h3', null, m.nome), el('p', 'sub', (m.herois || 'Sem heróis') + ' · código ' + m.id));
          var ff = el('div', 'fila');
          ff.appendChild(botao('Entrar', 'primario', function () { abrirMesaOnline(m.id, rascunhoMesa.heroiEntrar); }));
          c.appendChild(ff); g.appendChild(c);
        });
        s.appendChild(g);
      }
      pg.appendChild(s);
    }
  };

  function abrirMesaLocal(id) {
    var S = lerMesaLocal(id), reg = indiceMesas().filter(function (m) { return m.id === id; })[0];
    if (!S) { apagarMesaLocal(id); msgJogar = { ok: false, x: 'Essa mesa não pôde ser lida e foi tirada da lista.' }; irPara('jogar'); return; }
    entrarNaMesa({ tipo: 'local', id: id, nome: reg ? reg.nome : 'Mesa', S: S });
  }
