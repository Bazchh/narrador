  /* ---------------- páginas: início, aventuras, regras ---------------- */
  function secao(titulo, nivel) {
    var s = el('section', 'secao');
    if (titulo) s.appendChild(el(nivel || 'h2', null, titulo));
    return s;
  }
  function cartaoAventura(id, comBotao) {
    var a = C.AVENTURAS[id], c = el('article', 'caixa');
    c.className += ' aventura av-' + id;
    por(c, el('div', 'aventura-capa', a.tipo), el('h3', null, a.titulo), el('p', null, a.resumo), el('p', 'meta', a.duracao + ' · ' + a.nivel + ' · 1 a ' + C.MAX_HEROIS + ' heróis'));
    if (comBotao) {
      var f = el('div', 'fila');
      f.appendChild(botao('Jogar esta aventura', 'primario', function () { rascunhoMesa.av = id; irPara('jogar'); }));
      c.appendChild(f);
    }
    return c;
  }
  function linhaEstado(ok, txt) {
    var li = el('li');
    por(li, el('span', 'ponto ' + (ok ? 'sim' : 'nao')), el('span', null, txt));
    return li;
  }

  /* ---------------- capa animada: a capela no morro, o sino que toca sozinho, alguém subindo a trilha ---------------- */
  var capaQuadro = null;
  function pintarCapa(cv, tempo) {
    var larg = cv.clientWidth || 520, alt = cv.clientHeight || 440, dpr = Math.min(2, window.devicePixelRatio || 1);
    if (cv.width !== Math.round(larg * dpr) || cv.height !== Math.round(alt * dpr)) { cv.width = Math.round(larg * dpr); cv.height = Math.round(alt * dpr); }
    var g = cv.getContext('2d');
    if (!g) return;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, larg, alt);
    var W = larg, H = alt, t = tempo / 1000, i2, k;
    var ceu = g.createLinearGradient(0, 0, 0, H);
    ceu.addColorStop(0, '#120C26'); ceu.addColorStop(0.55, '#2A1D55'); ceu.addColorStop(1, '#3B2A66');
    g.fillStyle = ceu; g.fillRect(0, 0, W, H);
    // estrelas
    for (i2 = 0; i2 < 70; i2++) {
      var sx = ruido(i2, 1, 3) * W, sy = ruido(i2, 2, 5) * H * 0.62, br = 0.35 + 0.65 * Math.abs(Math.sin(t * (0.4 + ruido(i2, 3, 1)) + i2));
      g.fillStyle = 'rgba(236,231,247,' + (0.75 * br) + ')';
      g.fillRect(sx, sy, ruido(i2, 4, 2) > 0.85 ? 2 : 1, ruido(i2, 4, 2) > 0.85 ? 2 : 1);
    }
    // lua
    var lx = W * 0.74, ly = H * 0.24, lr = Math.min(W, H) * 0.15;
    var halo = g.createRadialGradient(lx, ly, lr * 0.6, lx, ly, lr * 3.4);
    halo.addColorStop(0, 'rgba(184,146,255,0.38)'); halo.addColorStop(1, 'rgba(184,146,255,0)');
    g.fillStyle = halo; g.fillRect(0, 0, W, H);
    g.fillStyle = '#F1ECFB'; g.beginPath(); g.arc(lx, ly, lr, 0, 6.2832); g.fill();
    g.fillStyle = 'rgba(184,170,220,0.5)';
    [[-0.3, -0.2, 0.2], [0.25, 0.1, 0.14], [-0.05, 0.4, 0.1], [0.35, -0.4, 0.08]].forEach(function (c) { g.beginPath(); g.arc(lx + c[0] * lr, ly + c[1] * lr, c[2] * lr, 0, 6.2832); g.fill(); });
    // nuvens passando
    for (k = 0; k < 4; k++) {
      var nx = ((t * (6 + k * 3) + k * 260) % (W + 320)) - 160, ny = H * (0.18 + k * 0.09);
      g.fillStyle = 'rgba(24,18,42,' + (0.5 - k * 0.08) + ')';
      g.beginPath(); g.ellipse(nx, ny, 120 + k * 20, 15 + k * 3, 0, 0, 6.2832); g.ellipse(nx + 70, ny + 7, 80, 12, 0, 0, 6.2832); g.fill();
    }
    // serra ao fundo
    g.fillStyle = '#231848'; g.beginPath(); g.moveTo(0, H * 0.7);
    for (i2 = 0; i2 <= 12; i2++) g.lineTo(W * i2 / 12, H * (0.62 + 0.08 * Math.sin(i2 * 1.7) + 0.03 * Math.sin(i2 * 4.1)));
    g.lineTo(W, H); g.lineTo(0, H); g.closePath(); g.fill();
    // morro da capela
    var topoX = W * 0.6, topoY = H * 0.52;
    function morro(x) { var d = (x - topoX) / W; return topoY + H * 0.95 * d * d + H * 0.02 * Math.sin(x * 0.03); }
    g.fillStyle = '#140E28'; g.beginPath(); g.moveTo(0, H);
    for (i2 = 0; i2 <= 40; i2++) { var mx = W * i2 / 40; g.lineTo(mx, Math.min(H, morro(mx))); }
    g.lineTo(W, H); g.closePath(); g.fill();
    // capela e campanário
    var u = Math.min(W, H) / 13, bx = topoX - u * 1.7, by = topoY + u * 0.1;
    g.fillStyle = '#0A0716';
    g.fillRect(bx, by - u * 1.5, u * 2.6, u * 1.6);
    g.beginPath(); g.moveTo(bx - u * 0.2, by - u * 1.5); g.lineTo(bx + u * 1.3, by - u * 2.5); g.lineTo(bx + u * 2.8, by - u * 1.5); g.closePath(); g.fill();
    var tx = bx + u * 2.5;
    g.fillRect(tx, by - u * 3.6, u * 1.15, u * 3.7);
    g.beginPath(); g.moveTo(tx - u * 0.15, by - u * 3.6); g.lineTo(tx + u * 0.575, by - u * 4.7); g.lineTo(tx + u * 1.3, by - u * 3.6); g.closePath(); g.fill();
    // janela do sino, com o sino aceso
    var sxn = tx + u * 0.575, syn = by - u * 2.9, pulso = (t % 3.2) / 3.2, aceso = 0.55 + 0.45 * Math.max(0, 1 - pulso * 3);
    g.fillStyle = '#1B1236'; g.beginPath(); g.moveTo(sxn - u * 0.34, syn + u * 0.5); g.lineTo(sxn - u * 0.34, syn - u * 0.1); g.arc(sxn, syn - u * 0.1, u * 0.34, Math.PI, 0); g.lineTo(sxn + u * 0.34, syn + u * 0.5); g.closePath(); g.fill();
    var gl = g.createRadialGradient(sxn, syn + u * 0.1, 0, sxn, syn + u * 0.1, u * 1.6);
    gl.addColorStop(0, 'rgba(184,146,255,' + (0.75 * aceso) + ')'); gl.addColorStop(1, 'rgba(184,146,255,0)');
    g.fillStyle = gl; g.fillRect(sxn - u * 1.6, syn - u * 1.5, u * 3.2, u * 3.2);
    g.fillStyle = 'rgba(214,196,255,' + aceso + ')'; g.beginPath(); g.moveTo(sxn - u * 0.2, syn + u * 0.32); g.quadraticCurveTo(sxn - u * 0.2, syn - u * 0.12, sxn, syn - u * 0.15); g.quadraticCurveTo(sxn + u * 0.2, syn - u * 0.12, sxn + u * 0.2, syn + u * 0.32); g.closePath(); g.fill();
    // ondas do sino
    for (k = 0; k < 3; k++) {
      var ph = (pulso + k / 3) % 1;
      g.strokeStyle = 'rgba(184,146,255,' + (0.5 * (1 - ph)) + ')'; g.lineWidth = 1.5;
      g.beginPath(); g.arc(sxn, syn + u * 0.1, u * (0.5 + ph * 4.2), Math.PI * 1.05, Math.PI * 1.95); g.stroke();
    }
    // porta com luz morna
    g.fillStyle = 'rgba(240,170,90,0.85)'; g.fillRect(bx + u * 0.95, by - u * 0.55, u * 0.38, u * 0.65);
    // trilha e caminhante com lanterna
    g.strokeStyle = 'rgba(120,100,170,0.5)'; g.lineWidth = 3; g.setLineDash([6, 7]); g.beginPath();
    for (i2 = 0; i2 <= 30; i2++) { var px = W * (0.06 + 0.5 * i2 / 30), py = morro(px) + 6 + 5 * Math.sin(i2 * 0.9); if (i2) g.lineTo(px, py); else g.moveTo(px, py); }
    g.stroke(); g.setLineDash([]);
    var passo = (t * 0.035) % 1, cxh = W * (0.06 + 0.5 * passo), cyh = morro(cxh) + 4, bal = Math.sin(t * 5) * 1.2;
    var lan = g.createRadialGradient(cxh + 7, cyh - 10, 0, cxh + 7, cyh - 10, 46);
    lan.addColorStop(0, 'rgba(240,180,100,0.55)'); lan.addColorStop(1, 'rgba(240,180,100,0)');
    g.fillStyle = lan; g.fillRect(cxh - 40, cyh - 56, 94, 92);
    g.fillStyle = '#05030B'; g.beginPath(); g.arc(cxh, cyh - 21 + bal * 0.3, 3.4, 0, 6.2832); g.fill();
    g.beginPath(); g.moveTo(cxh - 4.5, cyh - 17); g.lineTo(cxh + 4.5, cyh - 17); g.lineTo(cxh + 6, cyh - 3); g.lineTo(cxh - 6, cyh - 3); g.closePath(); g.fill();
    g.fillRect(cxh - 4 - bal, cyh - 3, 3, 7); g.fillRect(cxh + 1 + bal, cyh - 3, 3, 7);
    g.fillStyle = '#F6C777'; g.fillRect(cxh + 6, cyh - 12, 3, 4);
    // névoa no vale
    for (k = 0; k < 3; k++) {
      var fx = ((t * (9 + k * 4) + k * 310) % (W + 500)) - 250;
      var nv = g.createRadialGradient(fx, H * (0.9 - k * 0.04), 0, fx, H * (0.9 - k * 0.04), 240);
      nv.addColorStop(0, 'rgba(116,216,208,0.10)'); nv.addColorStop(1, 'rgba(116,216,208,0)');
      g.fillStyle = nv; g.fillRect(0, H * 0.6, W, H * 0.4);
    }
    // chuva fina
    g.strokeStyle = 'rgba(190,200,240,0.16)'; g.lineWidth = 1;
    for (i2 = 0; i2 < 46; i2++) { var rx = (ruido(i2, 9, 1) * W + t * 40) % W, ry = (ruido(i2, 8, 2) * H + t * 260 * (0.7 + ruido(i2, 7, 3))) % H; g.beginPath(); g.moveTo(rx, ry); g.lineTo(rx - 3, ry + 11); g.stroke(); }
    // o dado, em primeiro plano, girando devagar
    var sol = SOLIDOS.d20, R = mMul(mEixo([0.3, 1, 0.2], t * 0.55), mEixo([1, 0, 0.4], 0.5 + Math.sin(t * 0.4) * 0.25));
    var dx = W * 0.2, dy = H * 0.3 + Math.sin(t * 1.1) * 7, tam = Math.min(W, H) * 0.16;
    var gd = g.createRadialGradient(dx, dy, tam * 0.3, dx, dy, tam * 2.3);
    gd.addColorStop(0, 'rgba(230,190,106,0.30)'); gd.addColorStop(1, 'rgba(230,190,106,0)');
    g.fillStyle = gd; g.fillRect(dx - tam * 2.3, dy - tam * 2.3, tam * 4.6, tam * 4.6);
    var pts = sol.v.map(function (v) { var p = mVec(R, v), kk = 5 / (5 - p[2] / sol.raio); return [dx + p[0] / sol.raio * tam * kk, dy - p[1] / sol.raio * tam * kk]; });
    var luz = vnorm([-0.45, 0.65, 0.75]);
    sol.f.forEach(function (f, n) {
      var nn = vnorm(mVec(R, centroFace(sol, f)));
      if (nn[2] <= 0.02) return;
      var b = Math.max(0, nn[0] * luz[0] + nn[1] * luz[1] + nn[2] * luz[2]);
      g.beginPath(); f.forEach(function (ix, q) { if (q) g.lineTo(pts[ix][0], pts[ix][1]); else g.moveTo(pts[ix][0], pts[ix][1]); }); g.closePath();
      g.fillStyle = misturar([38, 26, 74], [196, 164, 255], 0.12 + 0.78 * b); g.fill();
      g.lineJoin = 'round'; g.lineWidth = 1.5; g.strokeStyle = 'rgba(230,190,106,' + (0.4 + 0.5 * b) + ')'; g.stroke();
      var c = [0, 0]; f.forEach(function (ix) { c[0] += pts[ix][0] / 3; c[1] += pts[ix][1] / 3; });
      var fpx = tam * 0.5 * (0.35 + 0.65 * nn[2]);
      if (fpx < 8) return;
      g.font = '700 ' + Math.round(fpx) + 'px "Alegreya", Georgia, serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillStyle = 'rgba(22,15,40,' + (0.5 + 0.45 * nn[2]) + ')'; g.fillText(String(n + 1), c[0], c[1]);
    });
    // bordas que somem no fundo da página
    g.globalCompositeOperation = 'destination-in';
    var masc = g.createRadialGradient(W * 0.5, H * 0.5, Math.min(W, H) * 0.3, W * 0.5, H * 0.5, Math.min(W, H) * 0.52);
    masc.addColorStop(0, 'rgba(0,0,0,1)'); masc.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = masc; g.fillRect(0, 0, W, H);
    g.globalCompositeOperation = 'source-over';
  }
  function animarCapa(cv) {
    if (capaQuadro) { cancelAnimationFrame(capaQuadro); capaQuadro = null; }
    pintarCapa(cv, 4200);
    if (semMovimento() || typeof requestAnimationFrame !== 'function') return;
    function quadro(agora) {
      if (!cv.isConnected || rotaDesenhada !== 'inicio') { capaQuadro = null; return; }
      pintarCapa(cv, agora + 4200);
      capaQuadro = requestAnimationFrame(quadro);
    }
    capaQuadro = requestAnimationFrame(quadro);
  }

  paginas.inicio = function (pg) {
    var capa = el('header', 'capa-grande'), txt = el('div', 'capa-texto'), arte = document.createElement('canvas');
    arte.className = 'capa-arte'; arte.setAttribute('role', 'img');
    arte.setAttribute('aria-label', 'Ilustração animada: uma capela no alto de um morro, sob a lua, com o sino aceso; alguém sobe a trilha com uma lanterna, e um dado de vinte lados gira em primeiro plano.');
    var h1 = el('h1');
    por(h1, document.createTextNode('Sua mesa de RPG, '), el('em', null, 'com um mestre que nunca falta.'));
    por(txt, el('p', 'sobretitulo', 'Crônica · sozinho ou em grupo'), h1,
      el('p', 'chamada', 'Crie um herói do seu jeito e escreva o que ele faz. O mestre narra, o motor rola os dados à vista de todos, e a história lembra de cada escolha.'));
    var f = el('div', 'fila');
    por(f, link('Começar a aventura', 'jogar', 'botao primario grande'), link('Criar personagem', 'herois', 'botao grande'));
    txt.appendChild(f);
    txt.appendChild(el('p', 'capa-nota', 'Regras de D&D 5ª edição (SRD 5.2) · ' + Object.keys(C.AVENTURAS).length + ' aventuras · ' + Object.keys(C.CLASSES).length + ' classes · ' + Object.keys(C.ESPECIES).length + ' espécies · até ' + C.MAX_HEROIS + ' heróis por mesa'));
    por(capa, txt, arte);
    pg.appendChild(capa);
    animarCapa(arte);

    var recentes = indiceMesas();
    if (recentes.length) {
      var sc = secao('Continuar de onde parou');
      var g = el('div', 'grade');
      recentes.slice(0, 2).forEach(function (m) {
        var c = el('article', 'caixa destaque');
        por(c, el('span', 'rotulo', (C.AVENTURAS[m.av] || {}).titulo || 'Aventura'), el('h3', null, m.nome), el('p', 'sub', m.herois + ' · ' + m.cena));
        var fl = el('div', 'fila');
        fl.appendChild(botao('Continuar', 'primario', function () { abrirMesaLocal(m.id); }));
        c.appendChild(fl); g.appendChild(c);
      });
      sc.appendChild(g); pg.appendChild(sc);
    }

    var passos = secao('Em três passos');
    var tp = el('div', 'tres');
    [['1', 'Crie seu herói', 'Espécie, classe, atributos, perícias, magias, aparência e história. Ou pegue um dos quatro heróis prontos.'],
      ['2', 'Escolha a aventura', 'Um treino de dez minutos para aprender, ou a subida ao morro onde um sino de pedra toca sozinho.'],
      ['3', 'Jogue como quiser', 'Sozinho, em grupo no mesmo aparelho ou, com a mesa compartilhada ligada, cada um do seu lugar e no seu horário.']
    ].forEach(function (x) { var d = el('div', 'passo'); por(d, el('span', 'passo-num', x[0]), el('h3', null, x[1]), el('p', null, x[2])); tp.appendChild(d); });
    passos.appendChild(tp); pg.appendChild(passos);

    var como = secao('O que tem na mesa');
    var t = el('div', 'grade tres-col');
    [['Um mestre que narra', 'Ele segue o roteiro da aventura e, quando a página permite, uma IA interpreta o que você escrever fora do previsto.'],
      ['Um motor que arbitra', 'Toda tentativa recebe um veredito e todo dado é rolado pelo sistema. A narração nunca decide um resultado sozinha.'],
      ['Dados que rolam de verdade', 'Um d20 em 3D entra girando e para no resultado, com a conta completa embaixo.'],
      ['O mapa da cena', 'Cada lugar tem um mapa em grade, com heróis, inimigos e outros personagens nos seus lugares.'],
      ['Combate com tática', 'Distâncias, linha de frente e de trás, magias, ataques furtivos e aliados que levantam quem caiu.'],
      ['Uma campanha que lembra', 'Cada fato vai para o diário e não volta atrás. O progresso é salvo a cada ação.']
    ].forEach(function (x) { var d = el('article', 'caixa recurso'); por(d, el('h3', null, x[0]), el('p', null, x[1])); t.appendChild(d); });
    como.appendChild(t); pg.appendChild(como);

    var av = secao('Aventuras');
    var ga = el('div', 'grade');
    Object.keys(C.AVENTURAS).forEach(function (id) { ga.appendChild(cartaoAventura(id, true)); });
    av.appendChild(ga); pg.appendChild(av);

    var es = secao('Nesta página, agora');
    var ul = el('ul', 'estado-lista');
    ul.appendChild(linhaEstado(true, 'Jogo completo neste aparelho, com 1 a ' + C.MAX_HEROIS + ' heróis na mesma mesa.'));
    if (!cap.pronto) ul.appendChild(linhaEstado(false, 'Verificando se o mestre por IA e as mesas compartilhadas estão disponíveis…'));
    else {
      ul.appendChild(linhaEstado(iaDisponivel(), iaDisponivel() ? 'Mestre por IA disponível: ele interpreta o que você escrever fora do roteiro.' + contaIA() : 'Mestre por IA indisponível aqui. O jogo funciona pelo roteiro e pelos botões.'));
      ul.appendChild(linhaEstado(onlineOk(), onlineOk() ? 'Mesas compartilhadas disponíveis: cada pessoa entra com o próprio personagem e joga quando puder.' : 'Mesas compartilhadas indisponíveis aqui. Para jogar em grupo, usem o mesmo aparelho.'));
    }
    if (!armazenaOk) ul.appendChild(linhaEstado(false, 'Este navegador não está guardando dados. Use “Copiar campanha”, na mesa, para não perder o progresso.'));
    es.appendChild(ul); pg.appendChild(es);

    var fim = el('section', 'chamada-final');
    por(fim, el('h2', null, 'O sino toca à meia-noite.'), el('p', null, 'Alguém precisa subir o morro para ver por quê.'), link('Jogar agora', 'jogar', 'botao primario grande'));
    pg.appendChild(fim);
  };

  paginas.aventuras = function (pg) {
    var s = secao('Aventuras', 'h1');
    s.appendChild(el('p', 'lead', 'Cada aventura é um roteiro pronto, com cenas, personagens, encontros e segredos. O mestre pode sair do roteiro, e todo desvio fica anotado no diário, com o motivo.'));
    var g = el('div', 'grade');
    Object.keys(C.AVENTURAS).forEach(function (id) { g.appendChild(cartaoAventura(id, true)); });
    s.appendChild(g);
    s.appendChild(el('p', 'dica', 'Os encontros se ajustam ao tamanho do grupo: mais heróis, mais inimigos. Novas aventuras entram nesta estante sem mudar o motor nem os personagens.'));
    pg.appendChild(s);
  };

  paginas.regras = function (pg) {
    var s = el('article', 'regras');
    s.appendChild(el('h1', null, 'Regras e como jogar'));
    function bloco(t, itens, paragrafo) {
      var b = el('section');
      b.appendChild(el('h2', null, t));
      if (paragrafo) b.appendChild(el('p', null, paragrafo));
      if (itens) { var ul = el('ul'); itens.forEach(function (i) { ul.appendChild(el('li', null, i)); }); b.appendChild(ul); }
      s.appendChild(b);
    }
    bloco('O básico', [
      'Toque numa sugestão ou escreva o que seu personagem faz: “falo com a Marga”, “examino a porta”, “ataco o goblin”.',
      'Perguntar não gasta nada: “posso arrombar a porta?”, “quem é Ivo?”. O mestre responde sem rolar dado e sem mudar a história.',
      'Quando o resultado é incerto, o mestre dá o veredito (perícia e dificuldade) e o motor rola um dado de 20 lados. Igualar ou passar a dificuldade (CD) é sucesso.',
      'Vantagem: rola dois d20 e fica com o maior. Desvantagem: fica com o menor.',
      'Um teste que falhou não se repete do mesmo jeito pelo mesmo herói. Outro herói pode tentar, ou o grupo procura outro caminho: sempre existe um.'
    ]);
    bloco('Personagem', [
      'Espécie: cada uma dá uma vantagem simples (um ponto de vida a mais por nível, sorte nos dados, uma perícia extra…).',
      'Classe: Guerreiro, Ladino, Clérigo ou Mago. Define pontos de vida, armas, magias e habilidades.',
      'Atributos: os valores 15, 14, 13, 12, 10 e 8, distribuídos como você quiser. O antecedente soma +2 e +1 (ou +1 em três).',
      'Perícias: o antecedente dá duas, a classe deixa escolher outras. O ladino dobra o bônus em duas delas.',
      'Magias: clérigos e magos escolhem quais levam. Magias de 1º círculo gastam espaços de magia; truques são à vontade.'
    ]);
    bloco('Combate', [
      'Cada inimigo está a uma de três distâncias: corpo a corpo, média distância ou longe.',
      'Cada herói fica na linha de frente ou na de trás. Quem está atrás atira e conjura em paz; os inimigos atacam quem está na frente. Sem ninguém na frente, eles alcançam todo mundo.',
      'No seu turno: um movimento (avançar, trocar de linha ou recuar), uma ação (atacar, conjurar, esquivar, desengajar, esconder-se, fugir) e, às vezes, uma ação bônus (poção, algumas magias e habilidades).',
      'Ataque: d20 + bônus contra a Classe de Armadura (CA) do alvo. Um 20 natural é crítico e dobra os dados de dano.',
      'Atacar à distância estando na frente, com um inimigo em corpo a corpo, dá desvantagem. Sair de perto de um inimigo provoca um ataque, a não ser que o herói desengaje antes.',
      'Com 0 PV o herói cai e faz testes contra a morte a cada turno. Um aliado pode curá-lo. No modo Tranquilo ninguém morre; no Clássico, três falhas matam.',
      'Se o grupo inteiro cair, quem resistir acorda num lugar seguro com 1 PV. Se ninguém resistir, dá para voltar ao último ponto seguro.'
    ]);
    bloco('Jogar em grupo', [
      'No mesmo aparelho: monte a mesa com até ' + C.MAX_HEROIS + ' heróis e passe a vez. Toque no herói, no alto da tela, para escolher quem age.',
      'Em mesa compartilhada (quando a página oferece): cada pessoa entra com o próprio personagem, pelo código da mesa, e joga quando puder. Ninguém precisa estar conectado ao mesmo tempo.',
      'Fora de combate, qualquer um age. Em combate, o motor segue a ordem de iniciativa. Para não travar a mesa, qualquer jogador pode agir pelo herói de quem está ausente.',
      'Ouro e poções são do grupo. O grupo anda junto: todos estão sempre na mesma cena.'
    ]);
    bloco('Mestre por IA', [
      'O roteiro da aventura vem primeiro: ele é o gabarito do que existe no mundo.',
      'Quando você escreve algo que o roteiro não prevê, a IA interpreta: responde perguntas, reconhece ações previstas ditas de outro jeito, ou dá o veredito de um improviso.',
      'A IA nunca rola dados nem muda o estado do jogo. Ela propõe; o motor confere a perícia e a dificuldade, rola e registra.',
      'Um improviso não dá itens, não derrota inimigos e não revela segredos. Para isso existem as ações da aventura.',
      (cap.origem === 'claude' ? 'Cada consulta usa a conta Claude de quem está jogando, e o aplicativo pede permissão na primeira vez. ' : '') + 'Dá para desligar o mestre por IA na aba Mesa.'
    ]);
    bloco('Descanso', [
      'Descanso curto (uma hora, em lugar seguro): gasta Dados de Vida para recuperar PV e devolve algumas habilidades.',
      'Descanso longo (uma noite, onde houver cama): recupera tudo.'
    ]);
    bloco('Simplificações desta mesa', [
      'Níveis 1 e 2, quatro classes, cinco espécies e quatro antecedentes. Sem talentos de origem.',
      'Combate por zonas e linhas, sem grade.',
      'Bênção e Escudo da Fé duram até o fim do combate, sem regra de concentração. Sono afeta até dois inimigos à mesma distância.',
      'Fichas de criaturas adaptadas do SRD, com pontos de vida ajustados ao tamanho do grupo. No modo Tranquilo, os inimigos causam metade do dano.',
      'O grupo não se divide: cenas separadas para cada jogador ficam para uma próxima versão.'
    ]);
    var lic = el('section');
    por(lic, el('h2', null, 'Licença'), el('p', null, 'Crônica ' + C.VERSAO + '. As regras vêm do System Reference Document 5.2.1, sob licença Creative Commons Attribution 4.0 International. As aventuras “O Pátio de Treino” e “O Sino de Pedra-Funda” são originais.'), el('p', 'atribuicao', C.ATRIBUICAO));
    s.appendChild(lic);
    pg.appendChild(s);
  };
