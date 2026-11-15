  /* ---------------- mapa da cena: desenhado por código, com todos em seus lugares ---------------- */
  var COLS = 12, LINS = 8;
  var CENARIO = {
    'sino:estalagem': { tema: 'taverna', npcs: function (S) { return S.f.ivo ? [{ n: 'Marga', x: 6.5, y: 3.6 }, { n: 'Bento', x: 8, y: 5 }] : [{ n: 'Marga', x: 9.6, y: 1.35 }, { n: 'Bento', x: 10.2, y: 5.6 }]; } },
    'sino:trilha': { tema: 'trilha', grupo: 'goblins', mostra: function (S) { return (!S.f.goblins || (S.f.goblins === 'evitados' && !S.f.ivo)) && (S.f.viuGoblins || S.f.goblinsAlerta || !!S.combate); } },
    'sino:capela': { tema: 'capela' },
    'sino:cripta': { tema: 'cripta', grupo: 'cripta', mostra: function (S) { return !S.f.ivo; } },
    'sino:camara': { tema: 'camara', grupo: 'camara', neutro: true, mostra: function (S) { return !S.f.ivo; }, npcs: function (S) { return S.f.ivo && S.f.ivo !== 'morto' ? [{ n: 'Ivo', x: 9.2, y: 4.6 }] : []; } },
    'treino:patio': { tema: 'patio', grupo: 'bonecos', neutro: true, mostra: function (S) { return !S.f.venceu; }, npcs: function () { return [{ n: 'Dorval', x: 10.4, y: 1.4 }]; } }
  };
  var TEMAS = {
    taverna: ['#3B2A3A', '#453143', '#2A1D2B'], trilha: ['#1B3338', '#20393C', '#15282D'], capela: ['#37324F', '#3F3959', '#272340'],
    cripta: ['#262140', '#2D2749', '#1A1630'], camara: ['#2B2648', '#322C52', '#120E20'], patio: ['#47393F', '#4F4046', '#33282E']
  };
  function ruido(x, y, s) { var v = Math.sin(x * 127.1 + y * 311.7 + s * 74.7) * 43758.5453; return v - Math.floor(v); }
  function corCss(nome) { return getComputedStyle(document.documentElement).getPropertyValue(nome).trim() || '#B892FF'; }
  function espalhar(n) { return [[4], [3.1, 4.9], [2.5, 4, 5.5], [1.9, 3.3, 4.7, 6.1], [1.6, 2.8, 4, 5.2, 6.4]][Math.max(0, Math.min(4, n - 1))]; }

  function desenharMapa() {
    var cv = $('mapa');
    if (!cv || !M) return;
    document.body.classList.toggle('sem-mapa', prefs.mapa === false);
    $('btn-mapa').textContent = prefs.mapa === false ? 'Mostrar mapa' : 'Esconder';
    var S = M.S, info = C.infoCena(S), cfg = CENARIO[S.av + ':' + S.cena] || info.mapa || { tema: 'cripta' };
    var briga = !!(S.combate && S.combate.grupo === '_briga'), grp = briga ? '_briga' : cfg.grupo;
    $('mapa-titulo').textContent = 'Mapa · ' + info.nome + (S.combate ? ' · rodada ' + S.combate.rodada : '');
    if (prefs.mapa === false) { limpar($('mapa-legenda')); return; }
    var larg = cv.clientWidth || 430, alt = Math.round(larg * 2 / 3), dpr = Math.min(2, window.devicePixelRatio || 1);
    if (cv.width !== Math.round(larg * dpr) || cv.height !== Math.round(alt * dpr)) { cv.width = Math.round(larg * dpr); cv.height = Math.round(alt * dpr); }
    var g = cv.getContext('2d');
    if (!g) return;
    var u = cv.width / COLS;
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.clearRect(0, 0, cv.width, cv.height);
    function ret(x, y, w, h, cor) { g.fillStyle = cor; g.fillRect(x * u, y * u, w * u, h * u); }
    function circ(x, y, r, cor) { g.fillStyle = cor; g.beginPath(); g.arc(x * u, y * u, r * u, 0, Math.PI * 2); g.fill(); }
    function elip(x, y, rx, ry, cor) { g.fillStyle = cor; g.beginPath(); g.ellipse(x * u, y * u, rx * u, ry * u, 0, 0, Math.PI * 2); g.fill(); }
    function brilho(x, y, r, cor) { var gr = g.createRadialGradient(x * u, y * u, 0, x * u, y * u, r * u); gr.addColorStop(0, cor); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect((x - r) * u, (y - r) * u, 2 * r * u, 2 * r * u); }
    var T = TEMAS[cfg.tema] || TEMAS.cripta, x, y;

    /* chão */
    for (y = 0; y < LINS; y++) for (x = 0; x < COLS; x++) ret(x, y, 1.02, 1.02, ruido(x, y, 1) > 0.5 ? T[0] : T[1]);
    if (cfg.tema === 'taverna') {
      g.strokeStyle = T[2]; g.lineWidth = Math.max(1, u * 0.03);
      for (y = 0.5; y < LINS; y += 0.5) { g.beginPath(); g.moveTo(0, y * u); g.lineTo(COLS * u, y * u); g.stroke(); }
      ret(0, 0, COLS, 0.35, '#1E1420'); ret(8.2, 2, 3.6, 0.55, '#6B4A3A'); ret(8.2, 2.5, 3.6, 0.1, '#3D2A22');
      [[9, 0.55], [9.9, 0.55], [10.8, 0.55]].forEach(function (b) { ret(b[0], b[1], 0.5, 0.5, '#5A3F33'); circ(b[0] + 0.25, b[1] + 0.25, 0.14, '#2A1D2B'); });
      [[3.6, 1.9], [6, 6.2], [2.6, 6.1]].forEach(function (m) { circ(m[0], m[1], 0.62, '#5A3F33'); circ(m[0], m[1], 0.5, '#6B4A3A'); circ(m[0] + 0.15, m[1] - 0.1, 0.09, '#E6BE6A'); });
      ret(11.3, 4.9, 0.7, 1.6, '#1E1420'); brilho(11.4, 5.7, 2.6, 'rgba(240,150,80,0.45)'); circ(11.55, 5.7, 0.22, '#F2A45C');
      ret(0, 3.4, 0.22, 1.2, '#8A6A4A');
    } else if (cfg.tema === 'trilha') {
      ret(0, 0, COLS, 0.9, '#0F1B22'); g.strokeStyle = '#2E4A4A'; g.lineWidth = u * 0.06; g.beginPath(); g.moveTo(0, 0.9 * u); g.lineTo(COLS * u, 0.9 * u); g.stroke();
      g.strokeStyle = '#4A3F52'; g.lineWidth = u * 1.5; g.lineCap = 'round'; g.beginPath(); g.moveTo(-0.5 * u, 4.6 * u); g.bezierCurveTo(3 * u, 3.4 * u, 6 * u, 5.4 * u, 8.5 * u, 3.9 * u); g.bezierCurveTo(10 * u, 3 * u, 11 * u, 2.4 * u, 12.6 * u, 1.9 * u); g.stroke();
      [[7.4, 2.1, 0.8, 0.55], [9.5, 4.9, 0.9, 0.6], [10.6, 3.7, 0.6, 0.45], [8.3, 6.1, 0.7, 0.5]].forEach(function (p) { elip(p[0], p[1] + 0.1, p[2], p[3], '#141B24'); elip(p[0], p[1], p[2], p[3], '#5C6076'); elip(p[0] - 0.15, p[1] - 0.12, p[2] * 0.5, p[3] * 0.4, '#777C92'); });
      [[1, 7.2], [2.4, 7.6], [5.2, 7.4], [11.3, 7.1], [0.8, 1.8]].forEach(function (a) { circ(a[0], a[1], 0.75, '#12262A'); circ(a[0] - 0.1, a[1] - 0.1, 0.5, '#1D3A3A'); });
      for (x = 0; x < 26; x++) { g.strokeStyle = 'rgba(160,190,230,0.16)'; g.lineWidth = 1; var rx = ruido(x, 3, 9) * COLS * u, ry = ruido(x, 7, 5) * LINS * u; g.beginPath(); g.moveTo(rx, ry); g.lineTo(rx - u * 0.1, ry + u * 0.3); g.stroke(); }
    } else if (cfg.tema === 'capela') {
      ret(0, 0, COLS, 0.3, '#17132A'); ret(0, 7.7, COLS, 0.3, '#17132A');
      brilho(4.2, 3.4, 3.4, 'rgba(150,190,255,0.20)');
      for (y = 1.4; y < 7; y += 1.1) { ret(2.2, y, 1.9, 0.28, '#2A2540'); ret(5, y, 1.9, 0.28, '#2A2540'); }
      ret(9, 3.1, 1.1, 1.8, '#5A5478'); ret(9.1, 3.2, 0.9, 1.6, '#6B6590');
      ret(11.2, 3.3, 0.8, 1.4, S.f.criptaAberta ? '#06040C' : '#4A3528'); g.strokeStyle = '#8C8AA8'; g.lineWidth = u * 0.05; g.strokeRect(11.2 * u, 3.3 * u, 0.8 * u, 1.4 * u);
      ret(8.2, 0, 1.2, 0.35, '#4A3528'); ret(0.4, 0.4, 1.3, 1.3, '#17132A'); g.strokeStyle = '#6B6590'; g.strokeRect(0.4 * u, 0.4 * u, 1.3 * u, 1.3 * u);
      for (x = 0; x < 14; x++) circ(ruido(x, 1, 2) * COLS, 0.5 + ruido(x, 2, 4) * 7, 0.08, '#56506E');
    } else if (cfg.tema === 'cripta') {
      ret(0, 0, COLS, 0.9, '#120F22'); ret(0, 7.1, COLS, 0.9, '#120F22');
      for (x = 1.2; x < 11; x += 1.6) { ret(x, 0.15, 0.9, 0.7, '#07050F'); ret(x, 7.15, 0.9, 0.7, '#07050F'); circ(x + 0.45, 0.6, 0.12, '#8F8AA6'); circ(x + 0.45, 7.5, 0.12, '#8F8AA6'); }
      for (y = 3; y < 5; y += 0.28) ret(0, y, 0.8, 0.14, '#3A345A');
      ret(11.3, 3.3, 0.7, 1.4, '#06040C'); brilho(11.6, 4, 1.8, 'rgba(184,146,255,0.18)');
    } else if (cfg.tema === 'camara') {
      ret(0, 0, COLS, LINS, T[2]);
      circ(6.2, 4, 4.3, '#3A345A'); circ(6.2, 4, 4.1, T[0]);
      for (x = 0; x < 30; x++) { var an = ruido(x, 1, 1) * 6.283, rr = ruido(x, 2, 2) * 3.9; ret(6.2 + Math.cos(an) * rr, 4 + Math.sin(an) * rr * 0.92, 0.5, 0.5, 'rgba(255,255,255,0.03)'); }
      brilho(7.2, 5.6, 2.2, 'rgba(240,170,90,0.28)'); circ(7.2, 5.6, 0.1, '#F2A45C');
      g.strokeStyle = '#6B4A3A'; g.lineWidth = u * 0.12; g.beginPath(); g.moveTo(9.6 * u, 1.1 * u); g.lineTo(11.4 * u, 2.9 * u); g.moveTo(11.4 * u, 1.1 * u); g.lineTo(9.6 * u, 2.9 * u); g.stroke();
      if (S.f.sino === 'quebrado') { [[10.1, 1.8], [10.8, 2.3], [10.9, 1.6]].forEach(function (p) { elip(p[0], p[1], 0.35, 0.22, '#8C8AA0'); }); }
      else {
        if (!S.f.ivo && !S.f.sinoAbafado) brilho(10.5, 2, 1.9, 'rgba(184,146,255,0.35)');
        circ(10.5, 2, 0.82, '#5F5C74'); circ(10.5, 2, 0.66, '#8C8AA0'); circ(10.5, 2, 0.4, '#5F5C74');
        if (S.f.sino !== 'levado') circ(10.5, 2, 0.14, '#C9C6DA');
      }
      ret(10.2, 5.9, 1.2, 0.3, '#4A3528'); elip(10.8, 5.7, 0.26, 0.2, '#B8B2CC');
    } else if (cfg.tema === 'patio') {
      ret(0, 0, COLS, 0.3, '#1E171C'); ret(0, 7.7, COLS, 0.3, '#1E171C');
      ret(4.6, 1, 0.9, 3, '#150F16'); ret(4.7, 1.1, 0.7, 2.8, '#241A26');
      ret(2.8, 6.15, 4.4, 0.16, '#8A6A4A'); ret(2.8, 6.1, 0.16, 0.5, '#5A3F33'); ret(7.04, 6.1, 0.16, 0.5, '#5A3F33');
      for (y = 4.8; y < 7.2; y += 0.3) ret(11.55, y, 0.3, 0.12, '#8C8AA0');
      ret(11.5, 4.7, 0.1, 2.6, '#5F5C74'); ret(11.85, 4.7, 0.1, 2.6, '#5F5C74');
      ret(1, 0.5, 2.2, 0.35, '#5A3F33'); [1.3, 1.9, 2.5].forEach(function (rx2) { ret(rx2, 0.3, 0.08, 0.9, '#C9C6DA'); });
    }

    /* grade e clima */
    g.strokeStyle = 'rgba(236,231,247,0.07)'; g.lineWidth = 1;
    for (x = 1; x < COLS; x++) { g.beginPath(); g.moveTo(Math.round(x * u) + 0.5, 0); g.lineTo(Math.round(x * u) + 0.5, cv.height); g.stroke(); }
    for (y = 1; y < LINS; y++) { g.beginPath(); g.moveTo(0, Math.round(y * u) + 0.5); g.lineTo(cv.width, Math.round(y * u) + 0.5); g.stroke(); }
    var vg = g.createRadialGradient(cv.width / 2, cv.height / 2, cv.height * 0.3, cv.width / 2, cv.height / 2, cv.width * 0.72);
    vg.addColorStop(0, 'rgba(15,11,27,0)'); vg.addColorStop(1, 'rgba(15,11,27,0.72)');
    g.fillStyle = vg; g.fillRect(0, 0, cv.width, cv.height);

    /* faixas de distância, em combate */
    var cTinta = corCss('--tinta'), cOuro = corCss('--bronze'), cPerigo = corCss('--perigo'), cBom = corCss('--bom'), cLua = corCss('--lua');
    function rotulo(txt, cx, cy, cor, tam) {
      g.font = '700 ' + Math.round(u * (tam || 0.24)) + 'px "Alegreya Sans", "Segoe UI", sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.lineWidth = Math.max(2, u * 0.09); g.strokeStyle = 'rgba(10,7,18,0.85)'; g.strokeText(txt, cx * u, cy * u);
      g.fillStyle = cor; g.fillText(txt, cx * u, cy * u);
    }
    if (S.combate) {
      [[5.6, 'corpo a corpo'], [8, 'média'], [10.4, 'longe']].forEach(function (z) { g.fillStyle = 'rgba(242,139,147,0.06)'; g.fillRect((z[0] - 0.75) * u, 0.55 * u, 1.5 * u, (LINS - 1.1) * u); rotulo(z[1], z[0], 0.3, 'rgba(236,231,247,0.7)', 0.22); });
      if (S.herois.length > 1) { rotulo('frente', 4.3, 7.72, 'rgba(236,231,247,0.7)', 0.22); rotulo('atrás', 2.3, 7.72, 'rgba(236,231,247,0.7)', 0.22); }
    }

    /* fichas */
    function ficha(o) {
      var r = 0.42, px = o.x * u, py = o.y * u;
      g.globalAlpha = o.apagado ? 0.45 : 1;
      elip(o.x, o.y + 0.3, 0.34, 0.12, 'rgba(0,0,0,0.45)');
      if (o.vez) { g.strokeStyle = cOuro; g.lineWidth = u * 0.07; g.setLineDash([u * 0.14, u * 0.1]); g.beginPath(); g.arc(px, py, (r + 0.16) * u, 0, Math.PI * 2); g.stroke(); g.setLineDash([]); }
      circ(o.x, o.y, r + 0.06, '#0A0712'); circ(o.x, o.y, r, o.cor);
      if (o.frac != null) {
        g.lineWidth = u * 0.08; g.strokeStyle = 'rgba(10,7,18,0.9)'; g.beginPath(); g.arc(px, py, (r + 0.02) * u, 0, Math.PI * 2); g.stroke();
        g.strokeStyle = o.frac > 0.5 ? cBom : o.frac > 0.25 ? cOuro : cPerigo;
        g.beginPath(); g.arc(px, py, (r + 0.02) * u, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.max(0.02, Math.min(1, o.frac))); g.stroke();
      }
      g.font = '700 ' + Math.round(u * 0.42) + 'px "Alegreya", Georgia, serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillStyle = '#120C22'; g.fillText(o.letra, px, py + u * 0.02);
      g.globalAlpha = 1;
      rotulo(o.nome, o.x, o.y + 0.72, o.apagado ? 'rgba(236,231,247,0.55)' : cTinta, 0.3);
    }
    var vezId = S.combate ? C.vez(S) : null, ativo = S.fim ? null : heroiAtivoId();
    var linhas = { frente: [], tras: [] };
    S.herois.forEach(function (h) { linhas[S.combate && h.linha === 'tras' ? 'tras' : 'frente'].push(h); });
    if (!S.combate) { linhas = { frente: [], tras: [] }; S.herois.forEach(function (h, i) { linhas[i % 2 ? 'tras' : 'frente'].push(h); }); }
    ['frente', 'tras'].forEach(function (ln) {
      var ys = espalhar(linhas[ln].length);
      linhas[ln].forEach(function (h, i) {
        ficha({ x: S.combate ? (ln === 'frente' ? 4.3 : 2.3) : (ln === 'frente' ? 3.4 : 2.1), y: S.combate ? ys[i] : ys[i] + (ln === 'tras' ? 0.5 : 0), cor: corCss('--h-' + h.cor), letra: h.nome.charAt(0).toUpperCase(), nome: h.nome.split(' ')[0].slice(0, 9), frac: h.pvMax ? h.pv / h.pvMax : 0, vez: h.id === (vezId || ativo), apagado: h.morto || h.pv <= 0 });
      });
    });
    var temInimigos = false, temOutros = false;
    if (grp && S.inimigos[grp] && (briga || !cfg.mostra || cfg.mostra(S))) {
      var vivosE = S.inimigos[grp].filter(function (e) { return e.vivo; }), emLuta = S.combate && S.combate.grupo === grp, porZona = { perto: [], medio: [], longe: [] };
      vivosE.forEach(function (e) { porZona[emLuta ? e.zona : (e.tipo === 'ivo' ? 'longe' : 'medio')].push(e); });
      Object.keys(porZona).forEach(function (z) {
        var ys = espalhar(porZona[z].length);
        porZona[z].forEach(function (e, i) {
          var hostil = emLuta || !cfg.neutro, num = (e.nome.match(/\d+$/) || [''])[0];
          if (hostil) temInimigos = true; else temOutros = true;
          ficha({ x: z === 'perto' ? 5.6 : z === 'medio' ? 8 : 10.4, y: ys[i], cor: hostil ? cPerigo : cLua, letra: e.nome.charAt(0) + num, nome: e.nome.slice(0, 11), frac: e.hp / e.hpMax, apagado: e.dorme > 0 || e.expulso > 0 });
        });
      });
    }
    (cfg.npcs ? cfg.npcs(S) : []).filter(function (n) { return !(briga && S.inimigos._briga.some(function (e) { return e.vivo && e.nome.indexOf(n.n) >= 0; })); }).forEach(function (n) { temOutros = true; ficha({ x: n.x, y: n.y, cor: cLua, letra: n.n.charAt(0), nome: n.n, frac: null }); });

    var leg = $('mapa-legenda');
    limpar(leg);
    function item(cor, txt) { var s = el('span'), i = el('i'); i.style.background = cor; por(s, i, document.createTextNode(txt)); leg.appendChild(s); }
    item(corCss('--acento'), S.herois.length > 1 ? 'heróis' : 'seu herói');
    if (temInimigos) item(cPerigo, 'inimigos');
    if (temOutros) item(cLua, 'outros personagens');
    leg.appendChild(el('span', null, S.combate ? 'O anel em volta mostra os pontos de vida. Tracejado: de quem é a vez.' : 'O anel em volta de cada ficha mostra os pontos de vida.'));
  }

  /* ---------------- dados animados: um poliedro 3D que rola, quica e para no resultado ---------------- */
  var filaDados = [], dadoTimer = null, dadoQuadro = null, dadoAtivo = false;
  var FI = (1 + Math.sqrt(5)) / 2;
  var SOLIDOS = {
    d20: {
      v: [[-1, FI, 0], [1, FI, 0], [-1, -FI, 0], [1, -FI, 0], [0, -1, FI], [0, 1, FI], [0, -1, -FI], [0, 1, -FI], [FI, 0, -1], [FI, 0, 1], [-FI, 0, -1], [-FI, 0, 1]],
      f: [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]],
      raio: 1.9, letra: 0.5
    },
    d6: {
      v: [[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1], [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]],
      f: [[4, 5, 6, 7], [1, 0, 3, 2], [5, 1, 2, 6], [0, 4, 7, 3], [7, 6, 2, 3], [0, 1, 5, 4]],
      raio: 1.74, letra: 1.05
    }
  };
  function semMovimento() { try { return window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; } }
  function vnorm(a) { var l = Math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; }
  function vcruz(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
  function mEixo(e, ang) {
    e = vnorm(e);
    var c = Math.cos(ang), s2 = Math.sin(ang), t = 1 - c, x = e[0], y = e[1], z = e[2];
    return [[t * x * x + c, t * x * y - s2 * z, t * x * z + s2 * y], [t * x * y + s2 * z, t * y * y + c, t * y * z - s2 * x], [t * x * z - s2 * y, t * y * z + s2 * x, t * z * z + c]];
  }
  function mMul(a, b) {
    var r = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], i2, j, k;
    for (i2 = 0; i2 < 3; i2++) for (j = 0; j < 3; j++) for (k = 0; k < 3; k++) r[i2][j] += a[i2][k] * b[k][j];
    return r;
  }
  function mVec(m, v) { return [m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2], m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2], m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2]]; }
  function centroFace(sol, f) {
    var c = [0, 0, 0];
    f.forEach(function (ix) { c[0] += sol.v[ix][0]; c[1] += sol.v[ix][1]; c[2] += sol.v[ix][2]; });
    return [c[0] / f.length, c[1] / f.length, c[2] / f.length];
  }
  // Rotação que deixa a face 0 de frente para quem olha.
  function mFinal(sol) {
    var n = vnorm(centroFace(sol, sol.f[0])), eixo = vcruz(n, [0, 0, 1]), ang = Math.acos(Math.max(-1, Math.min(1, n[2])));
    if (Math.abs(eixo[0]) + Math.abs(eixo[1]) + Math.abs(eixo[2]) < 1e-6) return mEixo([1, 0, 0], n[2] > 0 ? 0 : Math.PI);
    return mEixo(eixo, ang);
  }
  function misturar(a, b, t) { return 'rgb(' + Math.round(a[0] + (b[0] - a[0]) * t) + ',' + Math.round(a[1] + (b[1] - a[1]) * t) + ',' + Math.round(a[2] + (b[2] - a[2]) * t) + ')'; }

  // Desenha um quadro. t vai de 0 (entrando) a 1 (parado); cena guarda o sorteio daquela rolagem.
  function pintarDado(cena, t) {
    var cv = $('dado-cv');
    if (!cv) return;
    var larg = cv.clientWidth || 220, alt = cv.clientHeight || 170, dpr = Math.min(2, window.devicePixelRatio || 1);
    if (cv.width !== Math.round(larg * dpr)) { cv.width = Math.round(larg * dpr); cv.height = Math.round(alt * dpr); }
    var g = cv.getContext('2d');
    if (!g) return;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, larg, alt);
    var sol = cena.sol, e = 1 - Math.pow(1 - t, 3), resto = 1 - e;
    var R = mMul(mEixo([0, 0, 1], cena.giroZ * resto), mMul(mEixo(cena.eixo, cena.voltas * resto), cena.final));
    var tam = alt * 0.3 * (0.72 + 0.28 * e);
    var chao = alt * 0.6, quique = Math.abs(Math.sin(t * Math.PI * 3)) * Math.pow(1 - t, 1.6) * alt * 0.42;
    var cx = larg * 0.5 + cena.lado * larg * 0.62 * Math.pow(resto, 1.3), cy = chao - quique;
    // sombra no chão
    g.fillStyle = 'rgba(0,0,0,' + (0.45 - 0.25 * (quique / (alt * 0.42 || 1))) + ')';
    g.beginPath(); g.ellipse(cx, chao + tam * 0.98, tam * (0.95 - 0.3 * quique / (alt * 0.42 || 1)), tam * 0.2, 0, 0, Math.PI * 2); g.fill();
    // brilho do resultado, quando para
    if (t >= 1 && cena.cor) {
      var gr = g.createRadialGradient(cx, cy, tam * 0.4, cx, cy, tam * 2.1);
      gr.addColorStop(0, cena.cor.replace('1)', '0.55)')); gr.addColorStop(1, cena.cor.replace('1)', '0)'));
      g.fillStyle = gr; g.fillRect(0, 0, larg, alt);
    }
    var pts = sol.v.map(function (v) { var p = mVec(R, v), k = 5 / (5 - p[2] / sol.raio); return [cx + p[0] / sol.raio * tam * k, cy - p[1] / sol.raio * tam * k, p[2]]; });
    var luz = vnorm([-0.45, 0.65, 0.75]), escuro = [38, 26, 74], claro = [196, 164, 255];
    sol.f.forEach(function (f, i2) {
      var n = vnorm(mVec(R, centroFace(sol, f)));
      if (n[2] <= 0.02) return;
      var brilho = Math.max(0, n[0] * luz[0] + n[1] * luz[1] + n[2] * luz[2]);
      g.beginPath();
      f.forEach(function (ix, k) { if (k) g.lineTo(pts[ix][0], pts[ix][1]); else g.moveTo(pts[ix][0], pts[ix][1]); });
      g.closePath();
      g.fillStyle = misturar(escuro, claro, 0.12 + 0.78 * brilho);
      g.fill();
      g.lineJoin = 'round'; g.lineWidth = 1.4; g.strokeStyle = 'rgba(230,190,106,' + (0.35 + 0.5 * brilho) + ')';
      g.stroke();
      var c = [0, 0];
      f.forEach(function (ix) { c[0] += pts[ix][0] / f.length; c[1] += pts[ix][1] / f.length; });
      var px = tam * sol.letra * (0.35 + 0.65 * n[2]);
      if (px < 7) return;
      g.font = '700 ' + Math.round(px) + 'px "Alegreya", Georgia, serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillStyle = i2 === 0 && t >= 1 ? '#FFF6DC' : 'rgba(22,15,40,' + (0.55 + 0.4 * n[2]) + ')';
      if (i2 === 0 && t >= 1) { g.shadowColor = 'rgba(0,0,0,0.6)'; g.shadowBlur = 6; }
      g.fillText(String(cena.numeros[i2]), c[0], c[1] + px * 0.04);
      g.shadowBlur = 0;
    });
  }

  function fecharDados() {
    filaDados = []; dadoAtivo = false;
    if (dadoTimer) { clearTimeout(dadoTimer); dadoTimer = null; }
    if (dadoQuadro) { cancelAnimationFrame(dadoQuadro); dadoQuadro = null; }
    var b = $('dados'); if (b) b.hidden = true;
  }
  function mostrarRolagens(inicial) {
    if (!M) return;
    var S = M.S;
    if (inicial || M.rolVisto == null || S.nRol < M.rolVisto) { M.rolVisto = S.nRol; return; }
    var nomes = S.herois.map(function (h) { return 'Iniciativa de ' + h.nome; });
    var novos = S.rolagens.filter(function (r) { return r.n > M.rolVisto && (String(r.motivo).indexOf('Iniciativa de ') !== 0 || nomes.indexOf(r.motivo) >= 0); });
    M.rolVisto = S.nRol;
    if (prefs.dados === false || !novos.length) return;
    if (novos.length > 6) novos = novos.slice(0, 2).concat(novos.slice(-4));
    filaDados = filaDados.concat(novos).slice(-8);
    if (!dadoAtivo) proximoDado();
  }
  function proximoDado() {
    if (dadoTimer) { clearTimeout(dadoTimer); dadoTimer = null; }
    if (dadoQuadro) { cancelAnimationFrame(dadoQuadro); dadoQuadro = null; }
    var box = $('dados');
    if (!filaDados.length) { dadoAtivo = false; dadoTimer = setTimeout(fecharDados, 2000); return; }
    dadoAtivo = true;
    var r = filaDados.shift(), soma = r.modo === 'soma', sol = soma ? SOLIDOS.d6 : SOLIDOS.d20;
    var valor = soma ? r.total : r.d20, outros = [], k;
    for (k = 1; k <= (soma ? 6 : 20); k++) if (k !== valor) outros.push(k);
    outros.sort(function () { return Math.random() - 0.5; });
    var crit = !soma && r.d20 === 20, pif = !soma && r.d20 === 1;
    var cena = {
      sol: sol, final: mFinal(sol), numeros: [valor].concat(outros), lado: Math.random() < 0.5 ? -1 : 1,
      eixo: [Math.random() - 0.5, Math.random() - 0.5, Math.random() * 0.6 + 0.2], voltas: (5 + Math.random() * 3) * Math.PI, giroZ: (Math.random() - 0.5) * 5,
      cor: soma ? null : crit ? 'rgba(230,190,106,1)' : r.ok === true ? 'rgba(126,221,176,1)' : r.ok === false ? 'rgba(242,139,147,1)' : null
    };
    box.hidden = false;
    box.className = 'dados';
    $('dado-motivo').textContent = String(r.motivo || '').slice(0, 70);
    $('dado-conta').textContent = '';
    $('dado-veredito').textContent = '';
    $('dado-fila').textContent = filaDados.length ? 'mais ' + filaDados.length + (filaDados.length > 1 ? ' rolagens' : ' rolagem') + ' · toque para pular' : 'toque para fechar';
    function parar() {
      dadoQuadro = null;
      pintarDado(cena, 1);
      box.className = 'dados parado' + (soma ? '' : crit ? ' critico' : r.ok === true ? ' ok' : r.ok === false ? ' falha' : '');
      $('dado-conta').textContent = soma ? (r.dados.length > 1 ? r.dados.join(' + ') : String(r.dados[0])) + (r.bonus ? ' ' + C.sinal(r.bonus) : '') + ' = ' + r.total
        : (r.dados.length > 1 ? 'dados ' + r.dados.join(' e ') + ' · ' : '') + r.d20 + ' ' + C.sinal(r.bonus) + ' = ' + r.total + (r.alvo != null ? ' contra ' + r.rotAlvo + ' ' + r.alvo : '');
      $('dado-veredito').textContent = soma ? '' : crit ? '20 natural!' : pif && r.ok === false ? '1 natural' : r.ok === true ? 'Sucesso' : r.ok === false ? 'Falha' : '';
      dadoTimer = setTimeout(proximoDado, filaDados.length ? 950 : 0);
    }
    if (semMovimento() || typeof requestAnimationFrame !== 'function') { parar(); return; }
    var inicio = null, dur = soma ? 800 : 1150;
    function quadro(agora) {
      if (inicio === null) inicio = agora;
      var t = Math.min(1, (agora - inicio) / dur);
      if (t >= 1) { parar(); return; }
      pintarDado(cena, t);
      dadoQuadro = requestAnimationFrame(quadro);
    }
    pintarDado(cena, 0);
    dadoQuadro = requestAnimationFrame(quadro);
  }
