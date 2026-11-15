  /* ---------------- página Personagens: elenco e criador ---------------- */
  var editor = null, msgHerois = null, excluindo = null;

  function novoEditor(p) {
    editor = { id: p ? p.id : null, f: C.normalizarFicha(p ? p.ficha : {}), atrManual: !!p, bonusManual: !!p, erro: null };
    if (!p) editor.f.nome = '';
  }
  function fichaDoEditor() {
    var f = editor.f;
    if (!editor.atrManual) f.atr = C.sugerirAtributos(f.classe, f.kit);
    if (!editor.bonusManual) f.bonus = C.sugerirBonus(f.classe, f.kit, f.antecedente);
    var nome = f.nome;
    editor.f = C.normalizarFicha(f);
    editor.f.nome = nome;
    if (!editor.atrManual) editor.f.atr = C.sugerirAtributos(editor.f.classe, editor.f.kit);
    if (!editor.bonusManual) editor.f.bonus = C.sugerirBonus(editor.f.classe, editor.f.kit, editor.f.antecedente);
    return editor.f;
  }
  function mudarEditor(fn) { fn(editor.f); fichaDoEditor(); redesenharPagina(); }
  function trocar(lista, v, n) {
    lista = (lista || []).slice();
    if (lista.indexOf(v) >= 0) return lista;
    lista.push(v);
    while (lista.length > n) lista.shift();
    return lista;
  }

  paginas.herois = function (pg) {
    if (editor) { desenharEditor(pg); return; }
    var s = por(el('section', 'secao'), el('h1', null, 'Personagens'), el('p', 'lead', 'Seus heróis ficam guardados aqui e podem entrar em qualquer mesa. Cada um começa no nível 1.'));
    if (msgHerois) { s.appendChild(el('p', msgHerois.ok ? 'ok' : 'erro', msgHerois.x)); msgHerois = null; }
    var f = el('div', 'fila');
    var novo = botao('Novo personagem', 'primario', function () { novoEditor(null); redesenharPagina(); $('site').scrollTop = 0; });
    novo.id = 'btn-novo-heroi'; novo.disabled = elenco.length >= MAX_ELENCO;
    por(f, novo, PRONTOS.some(function (p) { return !elenco.some(function (x) { return x.ficha.nome === p.nome; }); }) && elenco.length < MAX_ELENCO ? botao('Adicionar heróis prontos', null, function () { usarProntos(); redesenharPagina(); }) : null);
    s.appendChild(f);
    if (!elenco.length) s.appendChild(el('p', 'aviso-caixa', 'Nenhum personagem ainda. Crie o primeiro, ou adicione os quatro heróis prontos para começar a jogar já.'));
    else {
      var g = el('div', 'grade');
      elenco.forEach(function (p) {
        var h = C.criarPC(p.ficha), c = el('article', 'caixa'), topo = el('div', 'heroi-topo'), t = el('div');
        por(t, el('h3', null, h.nome), el('p', 'sub', resumoFicha(p.ficha)));
        por(topo, avatar(h.nome, h.cor), t);
        por(c, topo, el('p', 'meta', 'PV ' + h.pvMax + ' · CA ' + C.ca(h) + ' · ' + C.CLASSES[h.classe].kits[h.kit].nome));
        if (h.aparencia) c.appendChild(el('p', 'sub', h.aparencia));
        var ff = el('div', 'fila');
        if (excluindo === p.id) {
          por(ff, el('span', 'erro', 'Apagar ' + h.nome + '?'), botao('Sim, apagar', 'perigo pequeno', function () { elenco = elenco.filter(function (x) { return x.id !== p.id; }); excluindo = null; salvarElenco(); redesenharPagina(); }), botao('Não', 'pequeno', function () { excluindo = null; redesenharPagina(); }));
        } else {
          por(ff, botao('Ver ficha', 'pequeno primario', function () { abrirFicha(C.criarPC(p.ficha), null); }), botao('Editar', 'pequeno', function () { novoEditor(p); redesenharPagina(); $('site').scrollTop = 0; }), botao('Apagar', 'perigo pequeno', function () { excluindo = p.id; redesenharPagina(); }));
        }
        c.appendChild(ff); g.appendChild(c);
      });
      s.appendChild(g);
      s.appendChild(el('p', 'dica', 'Editar um personagem não muda as mesas em que ele já entrou: lá vale a ficha do dia da entrada. ' + (onlineOk() ? 'Nesta página, o elenco também fica guardado na sua conta.' : 'O elenco fica guardado neste navegador.')));
    }
    pg.appendChild(s);
  };

  function desenharEditor(pg) {
    var f = fichaDoEditor(), cl = C.CLASSES[f.classe], an = C.ANTECEDENTES[f.antecedente], h = C.criarPC(f);
    var s = por(el('section', 'secao'), el('h1', null, editor.id ? 'Editar personagem' : 'Novo personagem'));
    var grade = el('div', 'criador'), form = el('div', 'form'), g, c;

    /* identidade */
    c = por(el('fieldset', 'campo'), el('legend', null, '1. Quem é'));
    var cn = campoTexto('h-nome', 'Nome', f.nome, 24, 'Ex.: Mirela, Tobias, Kael', function (v) { editor.f.nome = v; var p = $('previa-nome'); if (p) p.textContent = v.trim() || 'Sem nome'; });
    cn.lastChild.classList.add('estreito');
    c.appendChild(cn);
    var cores = el('div', 'cores');
    C.CORES.forEach(function (cor) {
      var l = el('label', 'cor-op'), i = document.createElement('input');
      i.type = 'radio'; i.name = 'h-cor'; i.value = cor; i.id = 'h-cor-' + cor; i.checked = f.cor === cor; i.setAttribute('aria-label', 'Cor ' + cor);
      i.addEventListener('change', function () { mudarEditor(function (x) { x.cor = cor; }); });
      por(l, i, el('span', 'cor-' + cor)); cores.appendChild(l);
    });
    c.appendChild(por(el('div', 'campo'), el('span', 'rotulo', 'Cor do marcador'), cores));
    var ca = campoTexto('h-aparencia', 'Aparência (opcional)', f.aparencia, 160, 'Ex.: alta, cicatriz no queixo, capa verde remendada', function (v) { editor.f.aparencia = v; });
    c.appendChild(ca);
    c.appendChild(campoTexto('h-historia', 'História em uma ou duas frases (opcional)', f.historia, 240, 'De onde vem e por que saiu de casa. O mestre por IA usa isto na narração.', function (v) { editor.f.historia = v; }, true));
    form.appendChild(c);

    /* espécie */
    c = por(el('fieldset', 'campo'), el('legend', null, '2. Espécie'));
    g = el('div', 'cartoes tres-col');
    Object.keys(C.ESPECIES).forEach(function (id) { g.appendChild(opcaoCartao('h-especie', id, C.ESPECIES[id].nome, C.ESPECIES[id].resumo, null, f.especie === id, false, function (v) { mudarEditor(function (x) { x.especie = v; }); })); });
    c.appendChild(g); form.appendChild(c);

    /* classe */
    c = por(el('fieldset', 'campo'), el('legend', null, '3. Classe'));
    g = el('div', 'cartoes');
    Object.keys(C.CLASSES).forEach(function (id) {
      var k = C.CLASSES[id], p = C.criarPC({ classe: id });
      g.appendChild(opcaoCartao('h-classe', id, k.nome, k.resumo, 'Dado de vida d' + k.dv + ' · PV ' + p.pvMax, f.classe === id, false, function (v) { mudarEditor(function (x) { x.classe = v; x.kit = null; }); }));
    });
    c.appendChild(g); form.appendChild(c);

    /* kit */
    if (Object.keys(cl.kits).length > 1) {
      c = por(el('fieldset', 'campo'), el('legend', null, '4. ' + cl.kitTitulo));
      g = el('div', 'cartoes' + (Object.keys(cl.kits).length === 3 ? ' tres-col' : ''));
      Object.keys(cl.kits).forEach(function (id) {
        var k = cl.kits[id];
        g.appendChild(opcaoCartao('h-kit', id, k.nome, k.resumo, null, f.kit === id, false, function (v) { mudarEditor(function (x) { x.kit = v; }); }));
      });
      c.appendChild(g); form.appendChild(c);
    }

    /* antecedente */
    c = por(el('fieldset', 'campo'), el('legend', null, '5. Antecedente'));
    g = el('div', 'cartoes');
    Object.keys(C.ANTECEDENTES).forEach(function (id) {
      var a = C.ANTECEDENTES[id];
      g.appendChild(opcaoCartao('h-ant', id, a.nome, a.resumo, 'Perícias: ' + a.pericias.map(function (p) { return C.PERICIAS[p].nome; }).join(' e ') + ' · bônus em ' + a.atr.map(function (k) { return C.ATR[k]; }).join(', '), f.antecedente === id, false, function (v) { mudarEditor(function (x) { x.antecedente = v; }); }));
    });
    c.appendChild(g); form.appendChild(c);

    /* atributos */
    c = por(el('fieldset', 'campo'), el('legend', null, '6. Atributos'));
    c.appendChild(el('p', 'dica', 'Distribua os valores 15, 14, 13, 12, 10 e 8. Escolher um valor que já está em outro atributo troca os dois de lugar. O número grande é o modificador: é ele que entra nas rolagens.'));
    g = el('div', 'atr-grade');
    C.ATR_ORDEM.forEach(function (k) {
      var cx = el('div', 'atr-caixa'), lb = el('label', null, C.ATR[k]), sel = document.createElement('select');
      sel.id = 'h-atr-' + k; lb.htmlFor = sel.id;
      C.CONJUNTO.forEach(function (v) { var op = el('option', null, String(v)); op.value = String(v); sel.appendChild(op); });
      sel.value = String(f.atr[k]);
      sel.addEventListener('change', function () {
        var v = Number(sel.value);
        mudarEditor(function (x) {
          var outro = C.ATR_ORDEM.filter(function (o) { return x.atr[o] === v; })[0];
          if (outro && outro !== k) x.atr[outro] = x.atr[k];
          x.atr[k] = v; editor.atrManual = true;
        });
      });
      var dif = h.atr[k] - f.atr[k];
      por(cx, lb, sel, el('b', null, C.sinal(C.mod(h.atr[k]))), el('small', null, 'final ' + h.atr[k] + (dif ? ' (+' + dif + ')' : '')));
      g.appendChild(cx);
    });
    c.appendChild(g);
    var bm = el('div', 'marcas');
    bm.appendChild(opcaoMarca('radio', 'h-bonus', '2+1', '+2 em um, +1 em outro', f.bonus.modo !== '1+1+1', false, function () { mudarEditor(function (x) { var sg = C.sugerirBonus(x.classe, x.kit, x.antecedente); x.bonus = { modo: '2+1', a: sg.a, b: sg.b }; editor.bonusManual = true; }); }));
    bm.appendChild(opcaoMarca('radio', 'h-bonus', '1+1+1', '+1 em ' + an.atr.map(function (k) { return C.ATR[k]; }).join(', '), f.bonus.modo === '1+1+1', false, function () { mudarEditor(function (x) { x.bonus = { modo: '1+1+1' }; editor.bonusManual = true; }); }));
    c.appendChild(por(el('div', 'campo'), el('span', 'rotulo', 'Bônus do antecedente (' + an.nome + ')'), bm));
    if (f.bonus.modo !== '1+1+1') {
      var fl = el('div', 'fila');
      [['a', '+2 em'], ['b', '+1 em']].forEach(function (par) {
        var lb = el('label', null, par[1]), sel = document.createElement('select');
        sel.id = 'h-bonus-' + par[0]; lb.htmlFor = sel.id; sel.style.width = 'auto';
        an.atr.forEach(function (k) { var op = el('option', null, C.ATR[k]); op.value = k; sel.appendChild(op); });
        sel.value = f.bonus[par[0]];
        sel.addEventListener('change', function () {
          mudarEditor(function (x) {
            var outra = par[0] === 'a' ? 'b' : 'a';
            if (x.bonus[outra] === sel.value) x.bonus[outra] = x.bonus[par[0]];
            x.bonus[par[0]] = sel.value; editor.bonusManual = true;
          });
        });
        por(fl, lb, sel);
      });
      c.appendChild(fl);
    }
    c.appendChild(por(el('div', 'fila'), botao('Usar a distribuição sugerida para a classe', 'pequeno', function () { editor.atrManual = false; editor.bonusManual = false; mudarEditor(nada); })));
    form.appendChild(c);

    /* perícias */
    c = por(el('fieldset', 'campo'), el('legend', null, '7. Perícias'));
    var fixas = an.pericias.slice();
    if (f.especie === 'elfo' && fixas.indexOf('percepcao') < 0) fixas.push('percepcao');
    var mf = el('div', 'marcas');
    fixas.forEach(function (p) { mf.appendChild(el('span', 'marca-fixa', C.PERICIAS[p].nome)); });
    c.appendChild(por(el('div', 'campo'), el('span', 'rotulo', 'Já vêm com o antecedente' + (f.especie === 'elfo' ? ' e a espécie' : '')), mf));
    var mc = el('div', 'marcas');
    cl.listaPericias.forEach(function (p) {
      if (fixas.indexOf(p) >= 0) return;
      mc.appendChild(opcaoMarca('checkbox', 'h-per', p, C.PERICIAS[p].nome, f.pericias.indexOf(p) >= 0, false, function (v) { mudarEditor(function (x) { x.pericias = trocar(x.pericias, v, cl.nPericias); }); }));
    });
    c.appendChild(por(el('div', 'campo'), el('span', 'rotulo', 'Da classe: ' + cl.nPericias + ' à sua escolha (tocar em outra troca a mais antiga)'), mc));
    if (f.especie === 'humano') {
      var se = document.createElement('select'); se.id = 'h-extra'; se.className = 'estreito';
      C.PERICIAS_ORDEM.forEach(function (p) {
        if (fixas.indexOf(p) >= 0 || f.pericias.indexOf(p) >= 0) return;
        var op = el('option', null, C.PERICIAS[p].nome); op.value = p; se.appendChild(op);
      });
      se.value = f.periciaExtra;
      se.addEventListener('change', function () { mudarEditor(function (x) { x.periciaExtra = se.value; }); });
      var le = el('label', null, 'Perícia extra de humano'); le.htmlFor = 'h-extra';
      c.appendChild(por(el('div', 'campo'), le, se));
    }
    if (cl.nDobro) {
      var md = el('div', 'marcas');
      h.pericias.forEach(function (p) {
        md.appendChild(opcaoMarca('checkbox', 'h-dobro', p, C.PERICIAS[p].nome, f.dobro.indexOf(p) >= 0, false, function (v) { mudarEditor(function (x) { x.dobro = trocar(x.dobro, v, cl.nDobro); }); }));
      });
      c.appendChild(por(el('div', 'campo'), el('span', 'rotulo', 'Especialização: ' + cl.nDobro + ' perícias com bônus dobrado'), md));
    }
    form.appendChild(c);

    /* magias */
    if (cl.conj) {
      c = por(el('fieldset', 'campo'), el('legend', null, '8. Magias'));
      var fixos = h.magias.filter(function (m) { return cl.listaTruques.indexOf(m) < 0 && cl.listaMagias.indexOf(m) < 0; });
      if (fixos.length) {
        var mx = el('div', 'marcas');
        fixos.forEach(function (m) { mx.appendChild(el('span', 'marca-fixa', C.MAGIAS[m].nome)); });
        c.appendChild(por(el('div', 'campo'), el('span', 'rotulo', 'Truques que já vêm com a classe'), mx));
      }
      function listaMagias(titulo, ids, escolhidas, n, campo) {
        var gm = el('div', 'cartoes');
        ids.forEach(function (m) {
          var l = el('label', 'cartao'), i = document.createElement('input'), cc = el('span', 'cartao-corpo');
          i.type = 'checkbox'; i.name = 'h-' + campo; i.value = m; i.id = 'h-' + campo + '-' + m; i.checked = escolhidas.indexOf(m) >= 0;
          i.addEventListener('change', function () { mudarEditor(function (x) { x[campo] = trocar(x[campo], m, n); }); });
          por(cc, el('span', 'cartao-nome', C.MAGIAS[m].nome), el('span', 'cartao-texto', C.MAGIAS[m].texto));
          por(l, i, cc); gm.appendChild(l);
        });
        c.appendChild(por(el('div', 'campo'), el('span', 'rotulo', titulo + ' (tocar em outra troca a mais antiga)'), gm));
      }
      if (cl.nTruques) listaMagias('Truques: ' + cl.nTruques + ' à sua escolha', cl.listaTruques, f.truques, cl.nTruques, 'truques');
      listaMagias('Magias de 1º círculo: ' + cl.nMagias + ' à sua escolha', cl.listaMagias, f.magias, cl.nMagias, 'magias');
      form.appendChild(c);
    }

    if (editor.erro) form.appendChild(el('p', 'erro', editor.erro));
    var salvar = botao(editor.id ? 'Salvar alterações' : 'Salvar personagem', 'primario grande', function () {
      var nome = String(editor.f.nome || '').replace(/\s+/g, ' ').trim();
      if (!nome) { editor.erro = 'Dê um nome ao personagem antes de salvar.'; redesenharPagina(); var cx = $('h-nome'); if (cx) cx.focus(); return; }
      var pronta = C.normalizarFicha(fichaDoEditor());
      if (editor.id && doElenco(editor.id)) doElenco(editor.id).ficha = pronta;
      else if (elenco.length < MAX_ELENCO) { var id = 'p' + codigo(8); elenco.push({ id: id, ficha: pronta }); if (rascunhoMesa.herois.length < C.MAX_HEROIS) rascunhoMesa.herois.push(id); }
      salvarElenco();
      msgHerois = { ok: true, x: pronta.nome + ' está no elenco.' };
      editor = null; redesenharPagina(); $('site').scrollTop = 0;
    });
    salvar.id = 'btn-salvar-heroi';
    form.appendChild(por(el('div', 'fila'), salvar, botao('Cancelar', null, function () { editor = null; redesenharPagina(); $('site').scrollTop = 0; })));

    /* prévia da ficha */
    var pv = el('aside', 'previa caixa'), topo = el('div', 'heroi-topo'), t = el('div'), nomeP = el('h3', null, String(f.nome || '').trim() || 'Sem nome');
    nomeP.id = 'previa-nome';
    por(t, nomeP, el('p', 'sub', resumoFicha(f)));
    por(topo, avatar(f.nome || '?', f.cor), t);
    pv.appendChild(topo);
    var ul = el('ul', 'linhas');
    function li(a, b) { var x = el('li'); por(x, el('span', null, a), el('span', null, b)); ul.appendChild(x); }
    li('Pontos de vida', String(h.pvMax));
    li('Classe de armadura', String(C.ca(h)));
    C.armas(h).forEach(function (w) { var m = C.modArma(h, w); li(w.nome, C.sinal(C.bonusArma(h, w)) + ' · ' + w.n + 'd' + w.l + (m ? C.sinal(m) : '')); });
    if (cl.conj) { li('Ataque mágico', C.sinal(C.atqMagia(h))); li('Dificuldade das magias', 'CD ' + C.cdMagia(h)); }
    li('Perícias treinadas', String(h.pericias.length));
    pv.appendChild(ul);
    por(pv, el('p', 'sub', 'Salvaguardas fortes: ' + h.salv.map(function (k) { return C.ATR[k]; }).join(' e ') + '.'), el('p', 'sub', 'Armadura: ' + C.caTexto(h) + '.'), el('p', 'sub', C.ESPECIES[h.especie].traco));
    por(grade, form, pv);
    s.appendChild(grade);
    pg.appendChild(s);
  }
