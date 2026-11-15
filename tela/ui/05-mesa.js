  /* ---------------- a mesa de jogo ---------------- */
  var ultimoN = 0, aba = 'ficha', fichaDe = null, confirmarSaida = false, mensagemCampanha = null, pensando = null;

  function entrarNaMesa(m) {
    if (M && M !== m) fecharMesa();
    M = m; M.sel = M.sel || null; M.liberado = null;
    if (m.tipo === 'local') gravar('cronica2.ultima', m.id); else apagar('cronica2.ultima');
    ultimoN = 0; aba = 'ficha'; fichaDe = null; confirmarSaida = false; mensagemCampanha = null; avisoMesa = null; ocupado = false; pensando = null;
    if (rota() === 'mesa') desenharRota(); else irPara('mesa');
  }
  function fecharMesa() {
    if (M && M.parar) { try { M.parar(); } catch (e) { /* já parado */ } }
    if (pensando && pensando.ctl) { try { pensando.ctl.abort(); } catch (e2) { /* nada */ } }
    M = null; ocupado = false; pensando = null;
    fecharDados(); fecharFicha();
  }
  function ehMeu(h) { return !M || M.tipo !== 'online' || (h.dono && h.dono === cap.uid); }
  function meus() { return M.S.herois.filter(ehMeu); }
  function heroiPorId(id) { var l = M.S.herois; for (var i = 0; i < l.length; i++) if (l[i].id === id) return l[i]; return null; }
  function vivo(h) { return h && !h.morto && h.pv > 0; }
  function heroiAtivoId() {
    if (M.S.combate) return C.vez(M.S);
    var s = heroiPorId(M.sel);
    if (vivo(s)) return s.id;
    var m = meus().filter(vivo)[0];
    return C.quemAge(M.S, m ? m.id : null);
  }

  /* ---------------- narração ---------------- */
  function linhaLog(l) {
    var e;
    if (l.t === 'narra') { e = el('div', 'l-narra'); l.x.split(/\n\n+/).forEach(function (p) { e.appendChild(el('p', null, p)); }); return e; }
    if (l.t === 'titulo') return el('h2', 'l-titulo', l.x);
    if (l.t === 'jogador') return el('p', 'l-jogador', l.x);
    if (l.t === 'dado') return el('p', 'l-dado', l.x);
    if (l.t === 'veredito') return el('p', 'l-veredito', l.x);
    if (l.t === 'fato') return null;
    if (l.t === 'combate') return el('p', 'l-combate', l.x);
    return el('p', 'l-sistema', l.x);
  }
  function desenharLog(inicial) {
    var log = $('log');
    if (inicial) { limpar(log); ultimoN = 0; }
    var novos = M.S.log.filter(function (l) { return l.n > ultimoN; });
    if (ultimoN === 0 && novos.length > 160) novos = novos.slice(novos.length - 160);
    var primeiro = null, comeco = ultimoN === 0;
    novos.forEach(function (l) { var n = linhaLog(l); ultimoN = l.n; if (!n) return; if (!primeiro) primeiro = n; log.appendChild(n); });
    while (log.childNodes.length > 400) log.removeChild(log.firstChild);
    if (primeiro) {
      var alturaNova = log.scrollHeight - primeiro.offsetTop;
      if (!comeco && alturaNova > log.clientHeight) log.scrollTop = Math.max(0, primeiro.offsetTop - 8);
      else log.scrollTop = log.scrollHeight;
    }
  }

  /* ---------------- topo: cena e grupo ---------------- */
  function desenharTopo() {
    var S = M.S, info = C.infoCena(S), g = $('grupo'), ativo = S.fim ? null : heroiAtivoId();
    $('topo-cena').textContent = info.nome + ' · ' + M.nome + (M.tipo === 'online' ? ' · código ' + M.id : '');
    limpar(g);
    S.herois.forEach(function (h) {
      var b = el('button', 'heroi-chip' + (h.id === ativo ? (S.combate ? ' vez' : ' sel') : '') + (vivo(h) ? '' : ' fora'));
      b.type = 'button'; b.id = 'chip-' + h.id;
      var f = h.pvMax ? h.pv / h.pvMax : 0, barra = el('span', 'pv-barra'), fill = el('span', 'pv-fill' + (f <= 0.25 ? ' baixo' : f <= 0.5 ? ' meio' : ''));
      fill.style.width = Math.round(f * 100) + '%'; barra.appendChild(fill);
      por(b, avatar(h.nome, h.cor, true), el('b', null, h.nome), barra, el('span', null, C.estadoHeroi(h) || (h.pv + '/' + h.pvMax)));
      b.title = h.nome + ' · CA ' + C.ca(h) + (S.combate && h.id === ativo ? ' · é a vez' : '') + (M.tipo === 'online' && !ehMeu(h) ? ' · de outro jogador' : '');
      b.addEventListener('click', function () { if (vivo(h) && !M.S.combate) M.sel = h.id; fichaDe = h.id; aba = 'ficha'; desenharMesa(false); });
      g.appendChild(b);
    });
    var selo = $('selo-ia');
    selo.textContent = iaLigada() ? 'Mestre: roteiro + IA' : 'Mestre: roteiro';
    selo.title = iaLigada() ? 'O que sair do roteiro é interpretado por IA. Dá para desligar na aba Mesa.' : (iaDisponivel() ? 'IA desligada na aba Mesa.' : 'Mestre por IA indisponível nesta cópia do jogo.');
  }

  /* ---------------- botões de ação ---------------- */
  function desenharOpcoes() {
    var box = $('opcoes'), S = M.S, g, b;
    limpar(box);
    $('texto').disabled = ocupado; $('btn-enviar').disabled = ocupado;
    if (avisoMesa) box.appendChild(el('p', 'nota-vez erro', avisoMesa));
    if (ocupado) {
      g = el('div', 'pensando');
      g.appendChild(el('span', null, pensando ? 'O mestre está pensando…' : 'Registrando a ação na mesa…'));
      if (pensando) g.appendChild(botao('Cancelar', 'pequeno', function () { if (pensando && pensando.ctl) { try { pensando.ctl.abort(); } catch (e) { /* nada */ } } }));
      box.appendChild(g);
      return;
    }
    if (S.fim) {
      g = el('div', 'grupo');
      g.appendChild(el('span', 'grupo-nome', S.fim.tipo === 'morte' ? 'O grupo caiu' : 'Aventura concluída'));
      if (S.fim.tipo === 'morte') g.appendChild(botao('Voltar ao último ponto seguro', 'primario', voltarAoPontoSeguro));
      g.appendChild(botao('Ver o diário', null, function () { abrirAba('diario'); }));
      g.appendChild(botao('Sair da mesa', null, function () { irPara('jogar'); }));
      box.appendChild(g);
      return;
    }
    var hid = heroiAtivoId(), h = heroiPorId(hid);
    if (M.tipo === 'online' && !meus().length) {
      g = el('div', 'nota-vez');
      g.appendChild(el('span', null, 'Você está assistindo a esta mesa. Para jogar, entre com um personagem pela aba Mesa.'));
      g.appendChild(botao('Abrir a aba Mesa', 'pequeno', function () { abrirAba('ajuda'); }));
      box.appendChild(g);
      return;
    }
    if (M.tipo === 'online' && S.combate && h && !ehMeu(h) && M.liberado !== h.id + ':' + S.combate.rodada) {
      g = el('div', 'nota-vez');
      g.appendChild(el('span', null, 'É a vez de ' + h.nome + ', de outro jogador. Se ele não estiver por perto, você pode agir por ele para a mesa não parar.'));
      g.appendChild(botao('Agir por ' + h.nome, 'pequeno', function () { M.liberado = h.id + ':' + M.S.combate.rodada; desenharOpcoes(); }));
      box.appendChild(g);
      return;
    }
    // Com o mestre por IA ligado, fora de combate, a mesa não entrega um cardápio: só o campo de texto e "Sugestões".
    if (iaLigada() && !S.combate) {
      g = el('div', 'nota-vez');
      if (S.herois.length > 1 && h) g.appendChild(el('span', null, 'Quem age: ' + h.nome + '.'));
      b = botao(M.sugestoes ? 'Esconder sugestões' : 'Sugestões', 'pequeno discreto', function () { M.sugestoes = !M.sugestoes; desenharOpcoes(); });
      b.id = 'btn-sugestoes';
      g.appendChild(b);
      if (!M.sugestoes) g.appendChild(el('span', null, 'Escreva o que seu personagem faz. O mestre entende texto livre.'));
      box.appendChild(g);
      if (!M.sugestoes) return;
    }
    var ops = C.opcoes(S, hid), grupos = [], mapa = {};
    if (S.herois.length > 1 && h && !(iaLigada() && !S.combate)) box.appendChild(el('p', 'nota-vez', (S.combate ? 'Vez de ' : 'Quem age: ') + h.nome + (S.combate ? ' (' + (h.linha === 'frente' ? 'na linha de frente' : 'na linha de trás') + ')' : '')));
    ops.forEach(function (o) { if (!mapa[o.grupo]) { mapa[o.grupo] = []; grupos.push(o.grupo); } mapa[o.grupo].push(o); });
    var calmo = !S.combate, unico = calmo ? el('div', 'grupo') : null;
    grupos.forEach(function (nome) {
      g = unico || el('div', 'grupo');
      if (!calmo) g.appendChild(el('span', 'grupo-nome', nome));
      mapa[nome].forEach(function (o) {
        b = el('button', 'ficha-acao' + (nome === 'Ir para' ? ' ir' : nome === 'Turno' ? ' fim-turno' : nome === 'Personagem' ? ' pessoal' : ''), (nome === 'Ir para' ? '→ ' : '') + o.rot);
        b.type = 'button';
        b.addEventListener('click', function () { enviar(o.cmd); });
        g.appendChild(b);
      });
      if (!calmo) box.appendChild(g);
    });
    if (unico) box.appendChild(unico);
    box.scrollTop = 0;
  }

  /* ---------------- painel ---------------- */
  function bloco(titulo) {
    var b = el('section', 'bloco');
    if (titulo) b.appendChild(el('div', 'bloco-titulo', titulo));
    return b;
  }
  function linha(ul, a, b, cls) { var li = el('li', cls || null); por(li, el('span', null, a), el('span', null, b)); ul.appendChild(li); }
  function pips(tem, max) {
    var s = el('span', 'pips');
    for (var i = 0; i < max; i++) s.appendChild(el('span', 'pip' + (i < tem ? ' cheio' : '')));
    s.setAttribute('aria-label', tem + ' de ' + max);
    return s;
  }
  function linhaPips(ul, rot, tem, max) { var li = el('li'); por(li, el('span', null, rot), pips(tem, max)); ul.appendChild(li); }

  // Monta a ficha completa de um herói. S pode ser null (personagem do elenco, fora de uma mesa).
  function montarFicha(box, h, S, largo) {
    var cl = C.CLASSES[h.classe], b, ul;
    function sec(titulo, larga) { var x = bloco(titulo); if (largo && larga) x.className += ' larga'; box.appendChild(x); return x; }
    b = sec(null, true);
    var topo = el('div', 'heroi-topo'), t = el('div');
    por(t, el('h3', null, h.nome), el('p', 'sub', C.ESPECIES[h.especie].nome + ' · ' + cl.nome + ' de nível ' + h.nivel + ' · ' + C.ANTECEDENTES[h.antecedente].nome + ' · proficiência ' + C.sinal(h.pb)));
    por(topo, avatar(h.nome, h.cor), t); b.appendChild(topo);
    if (h.aparencia) b.appendChild(el('p', 'sub', h.aparencia));
    if (h.historia) b.appendChild(el('p', 'sub', h.historia));
    if (S && M && M.tipo === 'online') b.appendChild(el('p', 'sub', ehMeu(h) ? 'Personagem seu.' : 'Personagem de outro jogador.'));

    b = sec('Estado');
    ul = el('ul', 'linhas');
    linha(ul, 'Pontos de vida', h.pv + ' / ' + h.pvMax + (C.estadoHeroi(h) ? ' (' + C.estadoHeroi(h) + ')' : ''));
    linha(ul, 'Classe de armadura (' + C.caTexto(h) + ')', String(C.ca(h)));
    linha(ul, 'Dados de Vida (d' + cl.dv + ')', h.dv + ' / ' + h.dvTotal);
    if (h.espacosMax) linhaPips(ul, 'Espaços de magia (1º círculo)', h.espacos, h.espacosMax);
    if (h.classe === 'guerreiro') linhaPips(ul, 'Retomar o Fôlego', h.folego, 2);
    if (h.classe === 'guerreiro' && h.nivel >= 2) linhaPips(ul, 'Surto de Ação', h.surto, 1);
    if (h.classe === 'clerigo' && h.nivel >= 2) linhaPips(ul, 'Canalizar Divindade', h.canalizar, 2);
    if (h.classe === 'mago') linhaPips(ul, 'Recuperação Arcana', h.recArcana, 1);
    if (h.especie === 'orc') linhaPips(ul, 'Resistência implacável', h.implacavel, 1);
    b.appendChild(ul);

    b = sec('Atributos');
    var grade = el('div', 'atributos');
    C.ATR_ORDEM.forEach(function (a) {
      var c = el('div', 'atributo');
      por(c, el('small', null, C.ATR[a]), el('b', null, C.sinal(C.mod(h.atr[a]))), el('span', null, 'valor ' + h.atr[a] + (h.salv.indexOf(a) >= 0 ? ' · salv. ' + C.sinal(C.bonusSalv(h, a)) : '')));
      grade.appendChild(c);
    });
    b.appendChild(grade);

    b = sec('Ataques');
    ul = el('ul', 'linhas');
    C.armas(h).forEach(function (w) {
      var md = C.modArma(h, w);
      linha(ul, w.nome + (w.alcance === 'perto' ? ' (corpo a corpo)' : w.alcance === 'dist' ? ' (à distância)' : ' (corpo a corpo ou arremesso)'), C.sinal(C.bonusArma(h, w)) + ' · ' + w.n + 'd' + w.l + (md ? C.sinal(md) : '') + ' ' + C.TIPO_DANO[w.tipo]);
    });
    b.appendChild(ul);
    if (C.temMaestria(h)) {
      var lm0 = el('ul', 'lista');
      C.armas(h).forEach(function (w) { if (w.maestria) lm0.appendChild(el('li', null, w.nome + ': ' + C.MAESTRIA[w.maestria] + '.')); });
      b.appendChild(lm0);
    }

    b = sec('Perícias');
    ul = el('ul', 'linhas');
    C.PERICIAS_ORDEM.forEach(function (p) {
      var treinada = h.pericias.indexOf(p) >= 0;
      linha(ul, C.PERICIAS[p].nome + (h.dobro.indexOf(p) >= 0 ? ' (especialista)' : treinada ? ' (treinada)' : ''), C.sinal(C.bonusPericia(h, p)), treinada ? 'treinada' : 'apagada');
    });
    b.appendChild(ul);

    if (h.magias.length) {
      b = sec('Magias · ataque ' + C.sinal(C.atqMagia(h)) + ' · CD ' + C.cdMagia(h), true);
      var lm = el('ul', 'lista');
      h.magias.forEach(function (id) {
        var mg = C.MAGIAS[id], li = el('li');
        por(li, el('strong', null, mg.nome + (mg.truque ? ' (truque). ' : '. ')), document.createTextNode(mg.texto.replace(/^Truque\.\s*/, '')));
        lm.appendChild(li);
      });
      b.appendChild(lm);
    }

    if (S) {
      b = sec(S.herois.length > 1 ? 'Mochila do grupo' : 'Mochila');
      ul = el('ul', 'linhas');
      linha(ul, 'Peças de ouro', String(S.ouro));
      linha(ul, 'Poções de cura (2d4+2)', String(S.pocoes));
      if (h.ferramentas) linha(ul, 'Ferramentas de ladrão (' + h.nome + ')', 'sim');
      if (S.f.chave) linha(ul, 'Chave da cripta', 'sim');
      if (S.f.achouDiario) linha(ul, 'Caderno de Ivo', S.f.segredo ? 'lido' : 'não lido');
      if (S.f.sino === 'levado') linha(ul, 'Badalo do sino de pedra', 'sim');
      b.appendChild(ul);
    }

    b = sec('Habilidades', !S);
    var lt = el('ul', 'lista');
    [C.ESPECIES[h.especie].traco, cl.kitTitulo + ': ' + cl.kits[h.kit].nome + '. ' + cl.kits[h.kit].resumo].concat(cl.tracos, h.nivel >= 2 ? cl.tracos2 : []).forEach(function (t2) { lt.appendChild(el('li', null, t2)); });
    if (h.ferramentas && !S) lt.appendChild(el('li', null, 'Leva ferramentas de ladrão.'));
    b.appendChild(lt);
  }
  function heroiDaFicha() { return heroiPorId(fichaDe) || heroiPorId(heroiAtivoId()) || M.S.herois[0]; }
  function painelFicha(box) {
    var S = M.S, h = heroiDaFicha();
    if (S.herois.length > 1) {
      var m = el('div', 'marcas');
      S.herois.forEach(function (x) { m.appendChild(opcaoMarca('radio', 'ficha-de', x.id, x.nome, x.id === h.id, false, function (v) { fichaDe = v; desenharPainel(); })); });
      box.appendChild(m);
    }
    box.appendChild(por(el('div', 'fila'), botao('Abrir a ficha em tela cheia', 'pequeno', function () { abrirFicha(heroiDaFicha(), M.S); })));
    montarFicha(box, h, S, false);
  }
  function abrirFicha(h, S) {
    var corpo = $('modal-corpo');
    limpar(corpo);
    montarFicha(corpo, h, S || null, true);
    $('modal').hidden = false;
    $('btn-fechar-modal').focus();
  }
  function fecharFicha() { $('modal').hidden = true; }

  function painelCena(box) {
    var S = M.S, i = C.infoCena(S), b, ul;
    b = bloco();
    por(b, el('h3', null, i.nome), el('p', 'sub', i.lugar + ' · dia ' + S.dia), el('p', null, i.desc));
    box.appendChild(b);
    if (i.inimigos.length) {
      b = bloco('Combate · rodada ' + i.rodada);
      i.inimigos.forEach(function (e) {
        var c = el('div', 'inimigo'), t = el('div', 'inimigo-topo'), barra = el('div', 'inimigo-barra'), f = el('span');
        por(t, el('strong', null, e.nome), el('span', 'sub', e.zona + ' · ' + e.estado));
        f.style.width = Math.max(4, Math.round(e.fracao * 100)) + '%'; barra.appendChild(f);
        por(c, t, barra); b.appendChild(c);
      });
      if (S.herois.length > 1) {
        var fr = S.herois.filter(function (h) { return vivo(h) && h.linha === 'frente'; }).map(function (h) { return h.nome; }), tr = S.herois.filter(function (h) { return vivo(h) && h.linha === 'tras'; }).map(function (h) { return h.nome; });
        b.appendChild(el('p', null, 'Linha de frente: ' + (fr.join(', ') || 'ninguém') + '.' + (tr.length ? ' Atrás: ' + tr.join(', ') + '.' : '')));
      }
      b.appendChild(el('p', 'sub', 'Distâncias: corpo a corpo, média distância e longe. Ataques corpo a corpo exigem estar na frente, junto do alvo.'));
      box.appendChild(b);
    }
    if (i.ameaca) {
      b = bloco('Ameaça');
      b.appendChild(el('p', null, i.ameaca.cumprida ? 'Aconteceu: ' + i.ameaca.nome + '.' : 'Se você demorar: ' + i.ameaca.nome + '. Avanço: ' + i.ameaca.n + ' de ' + i.ameaca.max + '.'));
      box.appendChild(b);
    }
    if (i.presentes.length) {
      b = bloco('Quem está aqui');
      ul = el('ul', 'lista');
      i.presentes.forEach(function (p) { ul.appendChild(el('li', null, p)); });
      b.appendChild(ul); box.appendChild(b);
    }
    b = bloco('Saídas');
    if (!i.saidas.length) b.appendChild(el('p', 'sub', 'Esta cena não tem saídas.'));
    else { ul = el('ul', 'linhas'); i.saidas.forEach(function (s) { linha(ul, s.nome, s.livre ? 'livre' : 'bloqueada'); }); b.appendChild(ul); }
    box.appendChild(b);
    b = bloco('Descanso');
    b.appendChild(el('p', null, i.longo ? 'Aqui dá para fazer um descanso longo (uma noite), que recupera tudo.' : i.seguro ? 'Lugar seguro para um descanso curto (uma hora): gasta Dados de Vida para recuperar PV.' : 'Não é seguro descansar aqui.'));
    box.appendChild(b);
  }

  function painelDiario(box) {
    var S = M.S, b, ul;
    b = bloco();
    por(b, el('h3', null, 'Diário da campanha'), el('p', 'sub', 'O que entra aqui é verdade para sempre: a história não volta atrás.'));
    box.appendChild(b);
    b = bloco('Fatos estabelecidos (' + S.fatos.length + ')');
    if (!S.fatos.length) b.appendChild(el('p', 'sub', 'Nenhum fato ainda.'));
    else { ul = el('ol', 'lista numerada'); S.fatos.forEach(function (f) { ul.appendChild(el('li', null, f.x)); }); b.appendChild(ul); }
    box.appendChild(b);
    b = bloco('Desvios do roteiro (' + S.desvios.length + ')');
    if (!S.desvios.length) b.appendChild(el('p', 'sub', 'Quando a história sair do caminho previsto pela aventura, o desvio fica anotado aqui, com o motivo.'));
    else { ul = el('ul', 'lista'); S.desvios.forEach(function (d) { ul.appendChild(el('li', null, 'O roteiro previa ' + d.previsto + '; ' + d.feito + ' Motivo: ' + d.motivo)); }); b.appendChild(ul); }
    box.appendChild(b);
    var ids = Object.keys(S.vereditos);
    b = bloco('Vereditos do mestre (' + ids.length + ')');
    if (!ids.length) b.appendChild(el('p', 'sub', 'Cada tentativa recebe um veredito: consegue de cara, impossível, ou um teste com dificuldade definida. A mesma situação recebe sempre o mesmo veredito.'));
    else {
      ul = el('ul', 'linhas');
      ids.forEach(function (id) { var v = S.vereditos[id]; linha(ul, v.rot, v.tipo === 'teste' ? C.PERICIAS[v.per].nome + ' CD ' + v.cd : v.tipo === 'impossivel' ? 'impossível' : 'de cara'); });
      b.appendChild(ul);
    }
    box.appendChild(b);
    b = bloco('Resumo');
    var p = el('p', null, C.resumo(S)); p.style.whiteSpace = 'pre-line';
    b.appendChild(p); box.appendChild(b);
  }

  function painelRolagens(box) {
    var S = M.S, b = bloco();
    por(b, el('h3', null, 'Rolagens do motor'), el('p', 'sub', 'Todo dado do jogo sai daqui. Semente: ' + S.semente + ' · total de rolagens: ' + S.nRol + '.'));
    box.appendChild(b);
    b = bloco('Mais recentes primeiro');
    if (!S.rolagens.length) b.appendChild(el('p', 'sub', 'Nenhum dado rolado ainda.'));
    S.rolagens.slice(-80).reverse().forEach(function (r) {
      var p = el('p', 'rol');
      por(p, el('b', null, '#' + r.n), document.createTextNode(r.resumo || r.motivo));
      b.appendChild(p);
    });
    box.appendChild(b);
  }

  function painelMesa(box) {
    var S = M.S, b, ul, f, bt;
    b = bloco();
    por(b, el('h3', null, M.nome), el('p', 'sub', C.AVENTURAS[S.av].titulo + ' · modo ' + (S.dificuldade === 'classico' ? 'Clássico' : 'Tranquilo') + ' · ' + (M.tipo === 'online' ? 'mesa compartilhada' : 'neste aparelho')));
    if (M.tipo === 'online') por(b, el('p', 'codigo-mesa', M.id), el('p', 'sub', 'Passe este código a quem vai jogar. A pessoa abre esta mesma página, vai em Jogar e entra pelo código, com o personagem dela.'));
    box.appendChild(b);

    b = bloco('Tela');
    b.appendChild(por(el('div', 'fila'), botao(prefs.dados === false ? 'Ligar a animação dos dados' : 'Desligar a animação dos dados', 'pequeno', function () { prefs.dados = prefs.dados === false; gravar(K_PREFS, prefs); desenharPainel(); })));
    box.appendChild(b);

    b = bloco('Mestre');
    if (!iaDisponivel()) b.appendChild(el('p', null, cap.pronto ? 'Esta mesa é conduzida pelo roteiro da aventura. O mestre por IA não está disponível nesta cópia do jogo.' : 'Verificando se o mestre por IA está disponível…'));
    else {
      b.appendChild(el('p', null, iaLigada() ? 'Roteiro + IA: o que você escrever fora do previsto é interpretado por IA. O motor continua rolando e conferindo tudo.' + contaIA() : 'IA desligada: a mesa segue só o roteiro e os botões.'));
      b.appendChild(por(el('div', 'fila'), botao(iaLigada() ? 'Desligar a IA' : 'Ligar a IA', 'pequeno', function () { prefs.ia = !iaLigada(); gravar(K_PREFS, prefs); desenharMesa(false); })));
    }
    box.appendChild(b);
    if (MODO_TESTE && iaDisponivel()) box.appendChild(blocoTeste());

    b = bloco('Heróis da mesa (' + S.herois.length + ' de ' + C.MAX_HEROIS + ')');
    ul = el('ul', 'linhas');
    S.herois.forEach(function (h) {
      var li = el('li'), dir = el('span');
      li.appendChild(el('span', null, h.nome + ' · ' + C.CLASSES[h.classe].nome + (M.tipo === 'online' ? (ehMeu(h) ? ' · seu' : ' · de outro jogador') : '')));
      if (S.herois.length > 1 && !S.combate && !S.fim && ehMeu(h)) { bt = botao('Tirar', 'pequeno perigo', function () { aplicar(function (X) { var e = C.sairHeroi(X, h.id); if (e) avisoMesa = e; }); }); dir.appendChild(bt); }
      li.appendChild(dir); ul.appendChild(li);
    });
    b.appendChild(ul);
    if (S.herois.length < C.MAX_HEROIS && !S.fim) {
      var livres = elenco.filter(function (p) { return !S.herois.some(function (h) { return h.nome === p.ficha.nome && ehMeu(h); }); });
      if (S.combate) b.appendChild(el('p', 'sub', 'Novos heróis entram depois do combate.'));
      else if (!livres.length) b.appendChild(el('p', 'sub', 'Para trazer mais um herói, crie-o em Personagens e volte a esta mesa.'));
      else {
        var sel = document.createElement('select'); sel.id = 'mesa-novo-heroi'; sel.setAttribute('aria-label', 'Personagem para entrar na mesa');
        livres.forEach(function (p) { var op = el('option', null, p.ficha.nome + ' (' + C.CLASSES[p.ficha.classe].nome + ')'); op.value = p.id; sel.appendChild(op); });
        bt = botao('Entrar na mesa', 'pequeno primario', function () {
          var p = doElenco(sel.value);
          if (!p) return;
          var ficha = JSON.parse(JSON.stringify(p.ficha)); ficha.dono = cap.uid || null;
          aplicar(function (X) { var e = C.entrarHeroi(X, ficha); if (e) avisoMesa = e; });
        });
        bt.id = 'btn-entrar-heroi';
        b.appendChild(por(el('div', 'fila'), sel, bt));
      }
    }
    box.appendChild(b);

    b = bloco('Guardar e levar a campanha');
    b.appendChild(el('p', armazenaOk || M.tipo === 'online' ? 'sub' : 'erro', M.tipo === 'online' ? 'Esta mesa fica guardada na página, para todos os participantes. O botão abaixo gera uma cópia para jogar à parte, num aparelho só.' : (armazenaOk ? 'O progresso é salvo neste navegador a cada ação. Para levar a campanha a outro aparelho, ou guardar uma cópia, use os botões abaixo.' : 'Este navegador não está guardando o progresso. Copie a campanha antes de fechar a página.')));
    var area = document.createElement('textarea');
    area.className = 'texto-area'; area.id = 'area-campanha'; area.setAttribute('aria-label', 'Código da campanha');
    area.placeholder = 'O código da campanha aparece aqui. Para carregar outra campanha, cole o código dela e toque em Carregar.';
    b.appendChild(area);
    f = el('div', 'fila');
    f.appendChild(botao('Copiar campanha', 'pequeno', function () {
      area.value = C.exportar(M.S);
      area.focus(); area.select();
      var fim = function (okc) { mensagemCampanha = { ok: true, x: okc ? 'Código copiado. Guarde-o num lugar seguro.' : 'Código gerado e selecionado: copie com Ctrl+C (ou toque e segure).' }; mostrarMensagem(); };
      try { navigator.clipboard.writeText(area.value).then(function () { fim(true); }, function () { fim(false); }); } catch (e) { fim(false); }
    }));
    f.appendChild(botao('Carregar como mesa nova', 'pequeno', function () {
      var N = C.importar(area.value.trim());
      if (!N) { mensagemCampanha = { ok: false, x: 'Esse código não é de uma campanha válida. Cole o código inteiro, como foi copiado.' }; mostrarMensagem(); return; }
      N.herois.forEach(function (h) { h.dono = null; });
      var id = codigo(8), nome = 'Cópia de ' + N.herois[0].nome;
      salvarMesaLocal(id, nome, N);
      entrarNaMesa({ tipo: 'local', id: id, nome: nome, S: N });
    }));
    b.appendChild(f);
    var msg = el('p', null); msg.id = 'msg-campanha'; b.appendChild(msg);
    box.appendChild(b);

    b = bloco('Como jogar, em resumo');
    ul = el('ul', 'lista');
    ['Toque numa sugestão ou escreva o que seu personagem faz. Perguntar não gasta nada.',
      'Teste: d20 + bônus contra a dificuldade (CD). Vantagem rola dois dados e fica com o maior.',
      'Combate: um movimento, uma ação e, às vezes, uma ação bônus por turno. Quem está na linha de trás fica protegido enquanto houver alguém na frente.',
      'Comandos: /ficha, /cena, /diario, /rolagens, /resumo, /ir lugar, /descansar, /sair.'
    ].forEach(function (t) { ul.appendChild(el('li', null, t)); });
    b.appendChild(ul);
    b.appendChild(el('p', 'sub', 'As regras completas e a licença estão na página Regras do site. A mesa fica salva se você sair para ler.'));
    box.appendChild(b);

    b = bloco('Sair');
    f = el('div', 'fila');
    f.appendChild(botao('Sair da mesa (fica salva)', 'pequeno', function () { irPara('jogar'); }));
    if (M.tipo === 'local') {
      if (!confirmarSaida) f.appendChild(botao('Apagar esta mesa', 'pequeno perigo', function () { confirmarSaida = true; desenharPainel(); }));
      else {
        f.appendChild(el('span', 'erro', 'Apagar de vez?'));
        f.appendChild(botao('Sim, apagar', 'pequeno perigo', function () { var id = M.id; fecharMesa(); apagarMesaLocal(id); irPara('jogar'); }));
        f.appendChild(botao('Não', 'pequeno', function () { confirmarSaida = false; desenharPainel(); }));
      }
    }
    b.appendChild(f); box.appendChild(b);
    mostrarMensagem();
  }
  function mostrarMensagem() {
    var m = $('msg-campanha');
    if (!m) return;
    m.textContent = mensagemCampanha ? mensagemCampanha.x : '';
    m.className = mensagemCampanha ? (mensagemCampanha.ok ? 'ok' : 'erro') : '';
  }

  function desenharPainel() {
    var box = $('painel-corpo'), rolagem = box.scrollTop, mesma = box.getAttribute('data-aba') === aba;
    var txt = $('area-campanha') ? $('area-campanha').value : '';
    limpar(box);
    box.setAttribute('data-aba', aba);
    var abas = document.querySelectorAll('.aba[data-aba]');
    for (var i = 0; i < abas.length; i++) abas[i].setAttribute('aria-selected', abas[i].getAttribute('data-aba') === aba ? 'true' : 'false');
    if (aba === 'ficha') painelFicha(box);
    else if (aba === 'cena') painelCena(box);
    else if (aba === 'diario') painelDiario(box);
    else if (aba === 'rolagens') painelRolagens(box);
    else { painelMesa(box); if (mesma && txt && $('area-campanha')) $('area-campanha').value = txt; }
    box.scrollTop = mesma ? rolagem : 0;
  }
  function abrirAba(nome) {
    aba = nome;
    document.body.classList.add('painel-aberto');
    desenharPainel();
  }
  function desenharMesa(inicial) {
    if (!M) return;
    desenharLog(!!inicial); desenharTopo(); desenharOpcoes(); desenharPainel(); desenharMapa(); mostrarRolagens(!!inicial);
  }

  /* ---------------- entrada: do jogador ao motor ---------------- */
  var ABRE = { '/ficha': 'ficha', '/cena': 'cena', '/diario': 'diario', '/fatos': 'diario', '/rolagens': 'rolagens', '/dados': 'rolagens', '/ajuda': 'ajuda', '/sobre': 'ajuda', '/mesa': 'ajuda' };
  function guardarLocal() { if (M && M.tipo === 'local') salvarMesaLocal(M.id, M.nome, M.S); }

  // Aplica uma mudança ao estado da mesa. fn recebe o estado e o altera; pode devolver um estado novo inteiro.
  function aplicar(fn) {
    if (!M || ocupado) return Promise.resolve();
    if (M.tipo === 'online') return aplicarOnline(fn);
    try {
      var r = fn(M.S);
      if (r && C.validar(r)) M.S = r;
    } catch (e) {
      var salvo = lerMesaLocal(M.id);
      if (salvo) M.S = salvo;
      avisoMesa = 'O mestre se atrapalhou com essa ação e ela foi desfeita. A campanha está intacta: tente de outro jeito.';
      desenharMesa(false);
      return Promise.resolve();
    }
    guardarLocal();
    desenharMesa(false);
    return Promise.resolve();
  }
  function blocoTeste() {
    var b = bloco('Teste de modelos'), sel = document.createElement('select'), u = medidor.ultimo, ul = el('ul', 'linhas');
    b.id = 'bloco-teste';
    b.appendChild(el('p', 'sub', 'Só existe nesta versão de teste. Escolha qual IA faz o papel de mestre e compare.'));
    sel.id = 'sel-modelo';
    MODELOS.forEach(function (m) { var o = document.createElement('option'); o.value = m.id; o.textContent = m.nome; if ((prefs.modelo || '') === m.id) o.selected = true; sel.appendChild(o); });
    sel.addEventListener('change', function () { prefs.modelo = sel.value; gravar(K_PREFS, prefs); });
    b.appendChild(sel);
    b.appendChild(el('p', 'sub', 'Sonnet e Opus pensam antes de responder: podem levar de alguns segundos a um minuto.'));
    b.appendChild(el('p', null, 'Consultas nesta sessão: ' + medidor.n + ' · enviado: ' + medidor.enviado + ' letras · recebido: ' + medidor.recebido + ' letras'));
    if (u) b.appendChild(el('p', u.atendido ? null : 'erro', 'Última: pedido a ' + u.pedido + ', respondeu ' + u.respondeu + ' em ' + (u.ms / 1000).toFixed(1) + ' s (' + u.enviado + ' letras enviadas, ' + u.recebido + ' recebidas).' + (u.atendido ? '' : ' O modelo pedido não estava disponível nesta conta.')));
    if (medidor.n) {
      b.appendChild(el('p', 'sub', 'Quanto estas mesmas consultas custariam na versão paga por uso (estimativa):'));
      MODELOS.forEach(function (m) {
        if (!m.id) return;
        var li = el('li'), c = custoEstimado(m);
        li.appendChild(el('span', null, m.nome)); li.appendChild(el('span', null, 'US$ ' + c.toFixed(4) + ' no total · US$ ' + (c / medidor.n * 1000).toFixed(2) + ' por mil jogadas'));
        ul.appendChild(li);
      });
      b.appendChild(ul);
      b.appendChild(el('p', 'sub', 'A conta converte letras em tokens de forma aproximada e não inclui o que o modelo gasta pensando.'));
      b.appendChild(por(el('div', 'fila'), botao('Zerar o medidor', 'pequeno', function () { medidor.n = 0; medidor.enviado = 0; medidor.recebido = 0; medidor.ultimo = null; desenharPainel(); })));
    }
    return b;
  }
  var MSG_IA = { limite: 'O mestre por IA atingiu o limite de uso por agora. O roteiro assumiu esta resposta; tente a IA de novo mais tarde.', sessao: 'Sua sessão expirou. Entre de novo para usar o mestre por IA; por enquanto, o roteiro assume.', recusou: 'O mestre por IA preferiu não responder a isso. O roteiro assumiu.' };
  var DICA_MODO = { agir: 'O que você faz?', falar: 'O que você diz?', perguntar: 'O que quer saber do mestre?' };
  function modoAtual() { var m = $('modo') ? $('modo').value : 'agir'; return DICA_MODO[m] ? m : 'agir'; }
  function mostrarModo() { $('texto').placeholder = DICA_MODO[modoAtual()]; }
  function consultarIA(txt, hid, modo) {
    var ctl = null, prompt;
    try { ctl = new AbortController(); } catch (e) { ctl = null; }
    try { prompt = C.promptIA(M.S, txt, hid, modo); } catch (e2) { return aplicar(function (S) { C.agir(S, txt, hid, { modo: modo }); }); }
    ocupado = true; pensando = { ctl: ctl }; avisoMesa = null;
    desenharOpcoes();
    var mesa = M;
    function soltar() { ocupado = false; pensando = null; }
    return Promise.resolve().then(function () { return cap.mestre.perguntar(prompt, ctl ? ctl.signal : null, prefs.modelo || ''); }).then(function (resp) {
      if (M !== mesa) return;
      soltar();
      return aplicar(function (S) { if (!C.aplicarIA(S, txt, hid, resp, modo)) C.semIA(S, txt, hid, modo); });
    }, function (err) {
      if (M !== mesa) return;
      soltar();
      var code = err && err.code;
      if (code === 'cancelado') { $('texto').value = txt; desenharMesa(false); return; }
      if (code === 'fora') { cap.iaFalhou = true; avisoMesa = 'O mestre por IA não está liberado aqui. A mesa segue pelo roteiro.'; }
      else avisoMesa = MSG_IA[code] || 'O mestre por IA não respondeu desta vez. O roteiro assumiu.';
      var aviso = avisoMesa;
      return aplicar(function (S) { C.semIA(S, txt, hid, modo); }).then(function () { avisoMesa = aviso; if (M === mesa) desenharOpcoes(); });
    });
  }
  function enviar(txt) {
    if (!M || ocupado) return;
    txt = String(txt == null ? '' : txt).trim();
    if (!txt) return;
    var cmd = C.norm(txt).split(' ')[0];
    if (ABRE[cmd]) { abrirAba(ABRE[cmd]); return; }
    avisoMesa = null; M.sugestoes = false;
    if (M.S.fim) { desenharOpcoes(); return; }
    var hid = heroiAtivoId();
    var livre = txt.charAt(0) !== '#' && txt.charAt(0) !== '/', modo = livre ? modoAtual() : 'agir';
    if (livre && modo === 'perguntar') { $('modo').value = 'agir'; mostrarModo(); }
    if (livre && iaLigada() && C.podeIA(M.S, txt, hid)) { consultarIA(txt, hid, modo); return; }
    aplicar(function (S) { C.agir(S, txt, hid, { modo: modo }); });
  }
  function voltarAoPontoSeguro() {
    if (!M || ocupado) return;
    if (M.tipo === 'online') { voltarOnline(); return; }
    var N = C.voltarPontoSeguro(M.S);
    if (!N) { avisoMesa = 'Não há ponto seguro guardado para esta mesa.'; desenharOpcoes(); return; }
    M.S = N; guardarLocal(); desenharMesa(true);
  }
