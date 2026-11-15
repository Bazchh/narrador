/* Crônica 2 — motor de regras. O mestre narra, o motor arbitra: todo dado sai daqui e fica registrado. */
  var VERSAO = '2.0.0';
  var ATRIBUICAO = 'This work includes material from the System Reference Document 5.2.1 (“SRD 5.2.1”) by Wizards of the Coast LLC, available at https://www.dndbeyond.com/srd. The SRD 5.2.1 is licensed under the Creative Commons Attribution 4.0 International License, available at https://creativecommons.org/licenses/by/4.0/legalcode.';
  var MAX_HEROIS = 4, LOG_MAX = 400, ROL_MAX = 200;

  /* ------------------------------------------------------------------ utilidades */
  function norm(s) {
    return String(s == null ? '' : s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9\/?#:_\s]/g, ' ').replace(/\s+/g, ' ').trim();
  }
  function mod(v) { return Math.floor((v - 10) / 2); }
  function sinal(n) { return (n >= 0 ? '+' : '−') + Math.abs(n); }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function texto(v, max) { return String(v == null ? '' : v).replace(/[\u0000-\u001f\u007f]+/g, ' ').replace(/\s+/g, ' ').trim().slice(0, max); }
  function hash(str) {
    var h = 2166136261 >>> 0;
    str = String(str);
    for (var i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
    return h >>> 0;
  }
  function prox(S) {
    var t = (S.rng = (S.rng + 0x6D2B79F5) >>> 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  function dado(S, lados) { return 1 + Math.floor(prox(S) * lados); }
  function sortear(S, lista) { return lista[Math.floor(prox(S) * lista.length)]; }
  function lista(nomes) {
    if (nomes.length <= 1) return nomes.join('');
    return nomes.slice(0, -1).join(', ') + ' e ' + nomes[nomes.length - 1];
  }

  function out(S, tipo, txt) {
    S.log.push({ n: ++S.nLog, t: tipo, x: txt });
    if (S.log.length > LOG_MAX) S.log.splice(0, S.log.length - LOG_MAX);
  }
  function registrar(S, r) {
    r.n = ++S.nRol; r.cena = S.cena;
    S.rolagens.push(r);
    if (S.rolagens.length > ROL_MAX) S.rolagens.splice(0, S.rolagens.length - ROL_MAX);
  }
  function aviso(S, t) { out(S, 'sistema', t); return false; }

  /* ------------------------------------------------------------------ dados do sistema */
  var ATR = { for: 'Força', des: 'Destreza', con: 'Constituição', int: 'Inteligência', sab: 'Sabedoria', car: 'Carisma' };
  var ATR_ORDEM = ['for', 'des', 'con', 'int', 'sab', 'car'];
  var CONJUNTO = [15, 14, 13, 12, 10, 8];
  var PERICIAS = {
    acrobacia: { nome: 'Acrobacia', atr: 'des' }, arcanismo: { nome: 'Arcanismo', atr: 'int' },
    atletismo: { nome: 'Atletismo', atr: 'for' }, atuacao: { nome: 'Atuação', atr: 'car' },
    enganacao: { nome: 'Enganação', atr: 'car' }, furtividade: { nome: 'Furtividade', atr: 'des' },
    historia: { nome: 'História', atr: 'int' }, intimidacao: { nome: 'Intimidação', atr: 'car' },
    intuicao: { nome: 'Intuição', atr: 'sab' }, investigacao: { nome: 'Investigação', atr: 'int' },
    animais: { nome: 'Lidar com Animais', atr: 'sab' }, medicina: { nome: 'Medicina', atr: 'sab' },
    natureza: { nome: 'Natureza', atr: 'int' }, percepcao: { nome: 'Percepção', atr: 'sab' },
    persuasao: { nome: 'Persuasão', atr: 'car' }, prestidigitacao: { nome: 'Prestidigitação', atr: 'des' },
    religiao: { nome: 'Religião', atr: 'int' }, sobrevivencia: { nome: 'Sobrevivência', atr: 'sab' }
  };
  var PERICIAS_ORDEM = Object.keys(PERICIAS);
  var TIPO_DANO = { cortante: 'cortante', perfurante: 'perfurante', concussao: 'de concussão', fogo: 'de fogo', frio: 'de frio', eletrico: 'elétrico', trovao: 'de trovão', radiante: 'radiante', necrotico: 'necrótico', forca: 'de força' };
  var CORES = ['verde', 'bronze', 'azul', 'vinho', 'cinza', 'roxo'];

  var ESPECIES = {
    humano: { nome: 'Humano', resumo: 'Versátil. Ganha uma perícia a mais, à sua escolha.', traco: 'Engenhoso: uma perícia extra.' },
    anao: { nome: 'Anão', resumo: 'Robusto. Ganha 1 ponto de vida a mais por nível.', traco: 'Robustez anã: +1 PV por nível.' },
    elfo: { nome: 'Elfo', resumo: 'Atento. Já começa treinado em Percepção.', traco: 'Sentidos aguçados: treinado em Percepção.' },
    halfling: { nome: 'Halfling', resumo: 'Sortudo. Quando tira 1 no d20, rola de novo.', traco: 'Sorte: um 1 natural no d20 é rolado de novo.' },
    orc: { nome: 'Orc', resumo: 'Implacável. Uma vez por descanso longo, em vez de cair a 0 PV, fica com 1.', traco: 'Resistência implacável: uma vez por descanso longo, fica com 1 PV em vez de cair.' }
  };

  var ARMAS = {
    espada_longa: { nome: 'Espada longa', atr: 'for', n: 1, l: 8, tipo: 'cortante', alcance: 'perto', maestria: 'drenar', re: 'espada|lamina' },
    espada_grande: { nome: 'Espada grande', atr: 'for', n: 2, l: 6, tipo: 'cortante', alcance: 'perto', maestria: 'raspar', re: 'espada|montante|lamina' },
    azagaia: { nome: 'Azagaia', atr: 'for', n: 1, l: 6, tipo: 'perfurante', alcance: 'arremesso', maestria: 'lentidao', re: 'azagaia|lanca|arremess' },
    arco_longo: { nome: 'Arco longo', atr: 'des', n: 1, l: 8, tipo: 'perfurante', alcance: 'dist', maestria: 'lentidao', re: 'arco|flecha|atir|dispar' },
    espada_curta: { nome: 'Espada curta', atr: 'acu', n: 1, l: 6, tipo: 'perfurante', alcance: 'perto', maestria: 'afligir', re: 'espada|lamina' },
    rapieira: { nome: 'Rapieira', atr: 'acu', n: 1, l: 8, tipo: 'perfurante', alcance: 'perto', maestria: 'afligir', re: 'rapieira|espada|lamina' },
    arco_curto: { nome: 'Arco curto', atr: 'des', n: 1, l: 6, tipo: 'perfurante', alcance: 'dist', maestria: 'afligir', re: 'arco|flecha|atir|dispar' },
    besta_leve: { nome: 'Besta leve', atr: 'des', n: 1, l: 8, tipo: 'perfurante', alcance: 'dist', maestria: 'lentidao', re: 'besta|virote|atir|dispar' },
    maca: { nome: 'Maça', atr: 'for', n: 1, l: 6, tipo: 'concussao', alcance: 'perto', re: 'maca|clava' },
    martelo: { nome: 'Martelo de guerra', atr: 'for', n: 1, l: 8, tipo: 'concussao', alcance: 'perto', re: 'martelo' },
    cajado: { nome: 'Cajado', atr: 'for', n: 1, l: 6, tipo: 'concussao', alcance: 'perto', re: 'cajado|bastao' }
  };
  var MAESTRIA = {
    drenar: 'ao acertar, o alvo tem desvantagem no próximo ataque',
    raspar: 'ao errar, ainda causa dano igual ao modificador de Força',
    lentidao: 'ao acertar, o alvo não avança no próximo turno',
    afligir: 'ao acertar, o próximo ataque contra o mesmo alvo tem vantagem'
  };

  var CLASSES = {
    guerreiro: {
      nome: 'Guerreiro', dv: 10, pvNivel: 6, conj: null, salv: ['for', 'con'],
      resumo: 'Armadura pesada e armas de guerra. Aguenta muito e bate firme. O mais fácil para começar.',
      prioridade: ['for', 'con', 'des', 'sab', 'car', 'int'],
      listaPericias: ['atletismo', 'percepcao', 'intimidacao', 'sobrevivencia', 'acrobacia', 'animais', 'historia', 'intuicao', 'persuasao'], nPericias: 2, nDobro: 0,
      kitTitulo: 'Estilo de luta',
      kits: {
        escudo: { nome: 'Espada e escudo', resumo: 'Estilo Defesa: a maior Classe de Armadura do jogo. Espada longa e azagaias.', armas: ['espada_longa', 'azagaia'] },
        grande: { nome: 'Espada grande', resumo: 'Estilo Armas Grandes: 2d6 de dano, e os dados nunca valem menos que 3. Sem escudo.', armas: ['espada_grande', 'azagaia'] },
        arco: { nome: 'Arco longo', resumo: 'Estilo Arquearia: +2 para acertar à distância. Combina com Destreza alta.', armas: ['arco_longo', 'espada_curta'], prioridade: ['des', 'con', 'for', 'sab', 'car', 'int'] }
      },
      tracos: ['Retomar o Fôlego: ação bônus, recupera 1d10 + nível PV. 2 usos.', 'Maestria em armas: cada arma tem um efeito especial ao acertar.'],
      tracos2: ['Surto de Ação: uma ação extra no turno, uma vez por descanso.']
    },
    ladino: {
      nome: 'Ladino', dv: 8, pvNivel: 5, conj: null, salv: ['des', 'int'],
      resumo: 'Rápido e furtivo, bom com fechaduras e conversa. Causa muito dano quando ataca com vantagem ou ao lado de um aliado.',
      prioridade: ['des', 'con', 'sab', 'car', 'int', 'for'],
      listaPericias: ['furtividade', 'prestidigitacao', 'percepcao', 'enganacao', 'acrobacia', 'investigacao', 'persuasao', 'intuicao', 'atletismo', 'intimidacao'], nPericias: 4, nDobro: 2, dobroPadrao: ['furtividade', 'prestidigitacao', 'percepcao', 'enganacao'],
      kitTitulo: 'Armas',
      kits: {
        rapieira: { nome: 'Rapieira e arco curto', resumo: 'Mais dano de perto (1d8). O arco deixa o próximo ataque com vantagem.', armas: ['rapieira', 'arco_curto'] },
        besta: { nome: 'Espada curta e besta leve', resumo: 'Mais dano de longe (1d8), e a besta impede o alvo de avançar.', armas: ['espada_curta', 'besta_leve'] }
      },
      tracos: ['Ataque Furtivo: +1d6 de dano, uma vez por turno, quando ataca com vantagem ou com um aliado junto do alvo.', 'Especialização: bônus dobrado em duas perícias.', 'Maestria em armas e ferramentas de ladrão.'],
      tracos2: ['Ação Ardilosa: Esconder-se, Desengajar ou Disparada como ação bônus.']
    },
    clerigo: {
      nome: 'Clérigo', dv: 8, pvNivel: 5, conj: 'sab', salv: ['sab', 'car'],
      resumo: 'Cura o grupo, usa armadura e escudo e é o terror dos mortos-vivos.',
      prioridade: ['sab', 'con', 'for', 'car', 'des', 'int'],
      listaPericias: ['persuasao', 'religiao', 'intuicao', 'medicina', 'historia'], nPericias: 2, nDobro: 0,
      kitTitulo: 'Ordem divina',
      kits: {
        protetor: { nome: 'Protetor', resumo: 'Cota de malha, escudo e martelo de guerra. CA 18 e 1d8 de dano.', armas: ['martelo'] },
        taumaturgo: { nome: 'Taumaturgo', resumo: 'Soma a Sabedoria em Arcanismo e Religião e ganha o truque Poupar os Moribundos. Armadura mais leve.', armas: ['maca'] }
      },
      truquesFixos: ['chama'], listaTruques: [], nTruques: 0,
      listaMagias: ['curar', 'palavra', 'raioguia', 'bencao', 'escudofe', 'infligir'], nMagias: 4,
      tracos: ['Conjuração divina: 2 espaços de magia de 1º círculo.'],
      tracos2: ['Canalizar Divindade (2 usos): Expulsar Mortos-Vivos ou Centelha Divina (cura 1d8 + Sabedoria).']
    },
    mago: {
      nome: 'Mago', dv: 6, pvNivel: 4, conj: 'int', salv: ['int', 'sab'],
      resumo: 'Magia poderosa à distância, mas frágil de perto. O mais difícil sozinho; brilha num grupo.',
      prioridade: ['int', 'con', 'des', 'sab', 'car', 'for'],
      listaPericias: ['arcanismo', 'investigacao', 'historia', 'intuicao', 'religiao', 'natureza', 'medicina'], nPericias: 2, nDobro: 0,
      kitTitulo: 'Equipamento',
      kits: { cajado: { nome: 'Cajado e grimório', resumo: 'O equipamento padrão do mago.', armas: ['cajado'] } },
      truquesFixos: [], listaTruques: ['fogo', 'gelo', 'choque'], nTruques: 2,
      listaMagias: ['misseis', 'maos', 'armadura', 'onda', 'orbe', 'sono'], nMagias: 4,
      tracos: ['Conjuração arcana: 2 espaços de magia de 1º círculo.', 'Recuperação Arcana: uma vez por dia, um descanso curto devolve 1 espaço de magia.'],
      tracos2: ['Erudito: bônus dobrado em Arcanismo (se for treinado).']
    }
  };

  var ANTECEDENTES = {
    acolito: { nome: 'Acólito', pericias: ['intuicao', 'religiao'], atr: ['int', 'sab', 'car'], resumo: 'Criado num templo. Entende de gente e de fé.' },
    criminoso: { nome: 'Criminoso', pericias: ['prestidigitacao', 'furtividade'], atr: ['des', 'con', 'int'], ferramentas: true, resumo: 'Viveu à margem da lei. Leva ferramentas de ladrão.' },
    sabio: { nome: 'Sábio', pericias: ['arcanismo', 'historia'], atr: ['con', 'int', 'sab'], resumo: 'Anos entre livros. Reconhece magia e coisas antigas.' },
    soldado: { nome: 'Soldado', pericias: ['atletismo', 'intimidacao'], atr: ['for', 'des', 'con'], resumo: 'Serviu em armas. Forte e difícil de encarar.' }
  };

  var MAGIAS = {
    chama: { nome: 'Chama Sagrada', truque: true, modo: 'salv', salv: 'des', n: 1, l: 8, tipo: 'radiante', acao: 'acao', re: 'chama', texto: 'Truque. O alvo faz uma salvaguarda de Destreza ou sofre 1d8 de dano radiante.' },
    poupar: { nome: 'Poupar os Moribundos', truque: true, modo: 'poupar', acao: 'acao', re: 'poupar|estabiliz', texto: 'Truque. Um aliado caído fica estável e para de fazer testes contra a morte.' },
    raioguia: { nome: 'Raio Guia', modo: 'ataque', n: 4, l: 6, tipo: 'radiante', acao: 'acao', guia: true, re: 'raio guia|guia', texto: 'Ataque mágico: 4d6 de dano radiante, e o próximo ataque contra o alvo tem vantagem.' },
    curar: { nome: 'Curar Ferimentos', modo: 'cura', n: 2, l: 8, acao: 'acao', fora: true, re: 'curar|cura ferimento|curo', texto: 'Um aliado (ou você) recupera 2d8 + Sabedoria PV.' },
    palavra: { nome: 'Palavra Curativa', modo: 'cura', n: 2, l: 4, acao: 'bonus', fora: true, re: 'palavra', texto: 'Ação bônus. Um aliado (ou você) recupera 2d4 + Sabedoria PV.' },
    bencao: { nome: 'Bênção', modo: 'bencao', acao: 'acao', re: 'bencao|abenco', texto: 'O grupo inteiro soma 1d4 nos ataques e salvaguardas até o fim do combate.' },
    escudofe: { nome: 'Escudo da Fé', modo: 'escudofe', acao: 'bonus', re: 'escudo da fe|escudo', texto: 'Ação bônus. Um aliado (ou você) ganha +2 na CA até o fim do combate.' },
    infligir: { nome: 'Infligir Ferimentos', modo: 'salv', toque: true, salv: 'con', n: 2, l: 10, tipo: 'necrotico', meio: true, acao: 'acao', re: 'infligir', texto: 'Toque, em corpo a corpo. Salvaguarda de Constituição: 2d10 de dano necrótico, ou metade se o alvo passar.' },
    fogo: { nome: 'Raio de Fogo', truque: true, modo: 'ataque', n: 1, l: 10, tipo: 'fogo', acao: 'acao', re: 'raio de fogo|fogo', texto: 'Truque. Ataque mágico à distância: 1d10 de dano de fogo.' },
    gelo: { nome: 'Raio de Gelo', truque: true, modo: 'ataque', n: 1, l: 8, tipo: 'frio', lento: true, acao: 'acao', re: 'gelo|frio', texto: 'Truque. Ataque mágico à distância: 1d8 de frio, e o alvo não avança no próximo turno.' },
    choque: { nome: 'Toque Chocante', truque: true, modo: 'ataque', toque: true, n: 1, l: 8, tipo: 'eletrico', choque: true, acao: 'acao', re: 'choque|chocante', texto: 'Truque. Em corpo a corpo, um ataque mágico: 1d8 elétrico, e o alvo não faz ataques de oportunidade até o próximo turno dele.' },
    misseis: { nome: 'Mísseis Mágicos', modo: 'auto', tipo: 'forca', acao: 'acao', re: 'missil|misseis', texto: 'Três dardos que acertam sempre: 1d4+1 de dano de força cada.' },
    maos: { nome: 'Mãos Flamejantes', modo: 'area', salv: 'des', n: 3, l: 6, tipo: 'fogo', acao: 'acao', re: 'maos|flamejante', texto: 'Todos os inimigos em corpo a corpo: 3d6 de fogo, metade se passarem na salvaguarda de Destreza. Exige estar na linha de frente.' },
    onda: { nome: 'Onda Trovejante', modo: 'area', salv: 'con', n: 2, l: 8, tipo: 'trovao', empurra: true, acao: 'acao', re: 'onda|trovejante|trovao', texto: 'Todos os inimigos em corpo a corpo: 2d8 de trovão (metade se passarem em Constituição). Quem falha é empurrado para a média distância.' },
    orbe: { nome: 'Orbe Cromático', modo: 'ataque', n: 3, l: 8, tipo: 'fogo', acao: 'acao', re: 'orbe|cromatico', texto: 'Ataque mágico à distância: 3d8 de dano de fogo.' },
    armadura: { nome: 'Armadura Arcana', modo: 'armadura', acao: 'acao', fora: true, re: 'armadura', texto: 'Sua CA passa a 13 + Destreza até o próximo descanso longo.' },
    sono: { nome: 'Sono', modo: 'sono', salv: 'sab', acao: 'acao', re: 'sono|dormir|adormec', texto: 'Até dois inimigos à mesma distância fazem salvaguarda de Sabedoria ou dormem por dois turnos (acordam se sofrerem dano). Mortos-vivos são imunes.' }
  };

  // Fichas adaptadas do SRD 5.2.1 (Goblin Minion, Skeleton, Zombie, Cultist), com PV ajustados ao tamanho do grupo.
  var MONSTROS = {
    goblin: { nome: 'Goblin', ca: 12, hp: 7, ini: 2, atq: { nome: 'adaga', bonus: 4, n: 1, l: 4, b: 2, tipo: 'perfurante' }, salv: { des: 2, con: 0, sab: -1 }, re: /goblin/ },
    esqueleto: { nome: 'Esqueleto', ca: 14, hp: 13, ini: 3, atq: { nome: 'espada curta', bonus: 5, n: 1, l: 6, b: 3, tipo: 'perfurante' }, salv: { des: 3, con: 2, sab: -1 }, mortoVivo: true, vuln: ['concussao'], re: /esqueleto|ossada|ossos/ },
    zumbi: { nome: 'Zumbi', ca: 8, hp: 15, ini: -2, atq: { nome: 'pancada', bonus: 3, n: 1, l: 8, b: 1, tipo: 'concussao' }, salv: { des: -2, con: 3, sab: 0 }, mortoVivo: true, lerdo: true, fortitude: true, re: /zumbi|guardiao|cadaver/ },
    ivo: { nome: 'Ivo', ca: 12, hp: 14, ini: 1, atq: { nome: 'foice ritual', bonus: 3, n: 1, l: 4, b: 2, tipo: 'cortante' }, salv: { des: 1, con: 1, sab: 2 }, parado: true, re: /ivo|sacristao|homem/ },
    plebeu: { nome: 'Morador', ca: 10, hp: 4, ini: 0, atq: { nome: 'porrete', bonus: 2, n: 1, l: 4, b: 0, tipo: 'concussao' }, salv: { des: 0, con: 0, sab: 0 }, re: /morador|aldea/ },
    cacador: { nome: 'Caçador', ca: 13, hp: 16, ini: 2, atq: { nome: 'faca de caça', bonus: 4, n: 1, l: 6, b: 2, tipo: 'perfurante' }, salv: { des: 2, con: 1, sab: 1 }, re: /cacador/ },
    lobo: { nome: 'Lobo', ca: 12, hp: 11, ini: 2, atq: { nome: 'mordida', bonus: 4, n: 2, l: 4, b: 2, tipo: 'perfurante' }, salv: { des: 2, con: 1, sab: 1 }, re: /lobo/ },
    bandido: { nome: 'Salteador', ca: 12, hp: 11, ini: 1, atq: { nome: 'cimitarra', bonus: 3, n: 1, l: 6, b: 1, tipo: 'cortante' }, salv: { des: 1, con: 1, sab: 0 }, re: /salteador|bandido|homem/ },
    chefe: { nome: 'Chefe', ca: 14, hp: 22, ini: 2, atq: { nome: 'espada curta', bonus: 4, n: 1, l: 8, b: 2, tipo: 'cortante' }, salv: { des: 2, con: 2, sab: 1 }, re: /garra|chefe|lider/ },
    boneco: { nome: 'Boneco de treino', ca: 11, hp: 9, ini: 0, atq: { nome: 'espada de madeira', bonus: 2, n: 1, l: 4, b: 0, tipo: 'concussao' }, salv: { des: 0, con: 1, sab: -2 }, re: /boneco|manequim|espantalho/ }
  };

  var ZONAS = ['perto', 'medio', 'longe'];
  var ZNOME = { perto: 'corpo a corpo', medio: 'média distância', longe: 'longe' };

  /* ------------------------------------------------------------------ personagem */
  function sugerirAtributos(classe, kit) {
    var cl = CLASSES[classe] || CLASSES.guerreiro;
    var pr = (cl.kits[kit] && cl.kits[kit].prioridade) || cl.prioridade, a = {};
    pr.forEach(function (k, i) { a[k] = CONJUNTO[i]; });
    return a;
  }
  function sugerirBonus(classe, kit, antecedente) {
    var cl = CLASSES[classe] || CLASSES.guerreiro, an = ANTECEDENTES[antecedente] || ANTECEDENTES.soldado;
    var pr = (cl.kits[kit] && cl.kits[kit].prioridade) || cl.prioridade;
    var ord = pr.filter(function (k) { return an.atr.indexOf(k) >= 0; });
    return { modo: '2+1', a: ord[0], b: ord[1] };
  }
  function atributosValidos(a) {
    if (!a || typeof a !== 'object') return false;
    var v = ATR_ORDEM.map(function (k) { return a[k]; }).slice().sort(function (x, y) { return y - x; });
    return v.length === 6 && v.every(function (x, i) { return x === CONJUNTO[i]; });
  }
  function escolher(pedidos, permitidos, n, fora) {
    var r = [];
    (Array.isArray(pedidos) ? pedidos : []).forEach(function (p) {
      if (r.length < n && permitidos.indexOf(p) >= 0 && r.indexOf(p) < 0 && fora.indexOf(p) < 0) r.push(p);
    });
    permitidos.forEach(function (p) { if (r.length < n && r.indexOf(p) < 0 && fora.indexOf(p) < 0) r.push(p); });
    return r;
  }
  // Monta um herói a partir de uma ficha de criação. Tudo o que vier inválido é trocado pelo sugerido.
  function criarPC(o) {
    o = o || {};
    var cid = CLASSES[o.classe] ? o.classe : 'guerreiro', cl = CLASSES[cid];
    var aid = ANTECEDENTES[o.antecedente] ? o.antecedente : 'soldado', an = ANTECEDENTES[aid];
    var eid = ESPECIES[o.especie] ? o.especie : 'humano';
    var kit = cl.kits[o.kit] ? o.kit : Object.keys(cl.kits)[0];
    var base = atributosValidos(o.atr) ? o.atr : sugerirAtributos(cid, kit), atr = {};
    ATR_ORDEM.forEach(function (k) { atr[k] = base[k]; });
    var b = o.bonus || {}, sug = sugerirBonus(cid, kit, aid);
    if (b.modo === '1+1+1') an.atr.forEach(function (k) { atr[k] += 1; });
    else {
      var ba = an.atr.indexOf(b.a) >= 0 ? b.a : sug.a, bb = an.atr.indexOf(b.b) >= 0 && b.b !== ba ? b.b : (sug.b !== ba ? sug.b : an.atr.filter(function (k) { return k !== ba; })[0]);
      atr[ba] += 2; atr[bb] += 1;
    }
    var per = an.pericias.slice();
    if (eid === 'elfo' && per.indexOf('percepcao') < 0) per.push('percepcao');
    escolher(o.pericias, cl.listaPericias, cl.nPericias, per).forEach(function (p) { per.push(p); });
    if (eid === 'humano') escolher([o.periciaExtra, 'percepcao', 'intuicao', 'furtividade'], PERICIAS_ORDEM, 1, per).forEach(function (p) { per.push(p); });
    var dobro = cl.nDobro ? escolher((Array.isArray(o.dobro) ? o.dobro : []).concat(cl.dobroPadrao || []), per, cl.nDobro, []) : [];
    var mags = [];
    if (cl.conj) {
      mags = cl.truquesFixos.slice();
      escolher(o.truques, cl.listaTruques, cl.nTruques, mags).forEach(function (m) { mags.push(m); });
      if (cid === 'clerigo' && kit === 'taumaturgo') mags.push('poupar');
      escolher(o.magias, cl.listaMagias, cl.nMagias, mags).forEach(function (m) { mags.push(m); });
    }
    var nome = texto(o.nome, 24) || 'Aventureiro';
    var pv = cl.dv + mod(atr.con) + (eid === 'anao' ? 1 : 0);
    return {
      id: '', dono: o.dono || null, nome: nome, especie: eid, classe: cid, antecedente: aid, kit: kit, nivel: 1, pb: 2, atr: atr,
      pvMax: pv, pv: pv, dvTotal: 1, dv: 1, pericias: per, dobro: dobro, salv: cl.salv.slice(),
      ferramentas: cid === 'ladino' || !!an.ferramentas, armas: cl.kits[kit].armas.slice(), magias: mags,
      espacosMax: cl.conj ? 2 : 0, espacos: cl.conj ? 2 : 0,
      folego: cid === 'guerreiro' ? 2 : 0, surto: 0, canalizar: 0, recArcana: cid === 'mago' ? 1 : 0,
      implacavel: eid === 'orc' ? 1 : 0, armaduraArcana: false,
      aparencia: texto(o.aparencia, 160), historia: texto(o.historia, 240), cor: CORES.indexOf(o.cor) >= 0 ? o.cor : CORES[0],
      caido: null, morto: false, linha: 'frente', fx: {}
    };
  }
  // Devolve a ficha de criação já corrigida, do jeito que o motor a entende (para a tela mostrar o que vale).
  function normalizarFicha(o) {
    var h = criarPC(o), cl = CLASSES[h.classe], an = ANTECEDENTES[h.antecedente];
    var base = atributosValidos(o && o.atr) ? o.atr : sugerirAtributos(h.classe, h.kit);
    var b = (o && o.bonus) || {}, sug = sugerirBonus(h.classe, h.kit, h.antecedente), bonus;
    if (b.modo === '1+1+1') bonus = { modo: '1+1+1' };
    else {
      var ba = an.atr.indexOf(b.a) >= 0 ? b.a : sug.a, bb = an.atr.indexOf(b.b) >= 0 && b.b !== ba ? b.b : (sug.b !== ba ? sug.b : an.atr.filter(function (k) { return k !== ba; })[0]);
      bonus = { modo: '2+1', a: ba, b: bb };
    }
    var fixas = an.pericias.slice();
    if (h.especie === 'elfo' && fixas.indexOf('percepcao') < 0) fixas.push('percepcao');
    var daClasse = h.pericias.filter(function (p) { return fixas.indexOf(p) < 0; }).slice(0, cl.nPericias);
    var extra = h.especie === 'humano' ? h.pericias[h.pericias.length - 1] : null;
    return {
      nome: h.nome, especie: h.especie, classe: h.classe, antecedente: h.antecedente, kit: h.kit,
      atr: clone(base), bonus: bonus, pericias: daClasse, periciaExtra: extra, dobro: h.dobro.slice(),
      truques: h.magias.filter(function (m) { return cl.conj && cl.listaTruques.indexOf(m) >= 0; }),
      magias: h.magias.filter(function (m) { return cl.conj && cl.listaMagias.indexOf(m) >= 0; }),
      aparencia: h.aparencia, historia: h.historia, cor: h.cor
    };
  }

  function consc(h) { return !h.morto && h.pv > 0; }
  function ativos(S) { return S.herois.filter(consc); }
  function vivosH(S) { return S.herois.filter(function (h) { return !h.morto; }); }
  function heroi(S, id) { for (var i = 0; i < S.herois.length; i++) if (S.herois[i].id === id) return S.herois[i]; return null; }
  function ca(h) {
    var des = mod(h.atr.des), v;
    if (h.classe === 'guerreiro') v = Math.max(16, 12 + des) + (h.kit === 'escudo' ? 3 : 0);
    else if (h.classe === 'clerigo') v = h.kit === 'protetor' ? 18 : 14 + Math.max(-5, Math.min(2, des)) + 2;
    else if (h.classe === 'ladino') v = 11 + des;
    else v = (h.armaduraArcana ? 13 : 10) + des;
    if (h.fx && h.fx.escudoFe) v += 2;
    return v;
  }
  function caTexto(h) {
    var t;
    if (h.classe === 'guerreiro') t = (12 + mod(h.atr.des) > 16 ? 'couro batido' : 'cota de malha') + (h.kit === 'escudo' ? ', escudo e estilo Defesa' : '');
    else if (h.classe === 'clerigo') t = h.kit === 'protetor' ? 'cota de malha e escudo' : 'brunea e escudo';
    else if (h.classe === 'ladino') t = 'armadura de couro';
    else t = h.armaduraArcana ? 'Armadura Arcana ativa' : 'sem armadura';
    return t + (h.fx && h.fx.escudoFe ? ', Escudo da Fé' : '');
  }
  function bonusPericia(h, p) {
    var b = mod(h.atr[PERICIAS[p].atr]);
    if (h.pericias.indexOf(p) >= 0) b += h.pb;
    if (h.dobro.indexOf(p) >= 0) b += h.pb;
    if (h.classe === 'clerigo' && h.kit === 'taumaturgo' && (p === 'arcanismo' || p === 'religiao')) b += Math.max(1, mod(h.atr.sab));
    return b;
  }
  function bonusSalv(h, a) { return mod(h.atr[a]) + (h.salv.indexOf(a) >= 0 ? h.pb : 0); }
  function conj(h) { return CLASSES[h.classe].conj; }
  function cdMagia(h) { return 8 + h.pb + mod(h.atr[conj(h)]); }
  function atqMagia(h) { return h.pb + mod(h.atr[conj(h)]); }
  function armas(h) { return h.armas.map(function (id) { var w = ARMAS[id]; return { id: id, nome: w.nome, atr: w.atr, n: w.n, l: w.l, tipo: w.tipo, alcance: w.alcance, maestria: w.maestria, re: w.re }; }); }
  function modArma(h, w) { return w.atr === 'acu' ? Math.max(mod(h.atr.for), mod(h.atr.des)) : mod(h.atr[w.atr]); }
  function bonusArma(h, w) { return modArma(h, w) + h.pb + (h.classe === 'guerreiro' && h.kit === 'arco' && w.alcance === 'dist' ? 2 : 0); }
  function temMaestria(h) { return h.classe === 'guerreiro' || h.classe === 'ladino'; }
  function magias(h) { return h.magias; }
  function temMagia(h, id) { return h.magias.indexOf(id) >= 0; }
  function escala(cd) {
    return cd <= 5 ? 'muito fácil' : cd <= 10 ? 'fácil' : cd <= 15 ? 'médio' : cd <= 20 ? 'difícil' : cd <= 25 ? 'muito difícil' : 'quase impossível';
  }
  function melhor(S, pericia) {
    var a = ativos(S), m = a[0];
    a.forEach(function (h) { if (bonusPericia(h, pericia) > bonusPericia(m, pericia)) m = h; });
    return m;
  }
  function grupo(S) { return ativos(S).length > 1; }

  /* ------------------------------------------------------------------ rolagens */
  // modo: 'vantagem' | 'desvantagem' | null ; h: herói que rola (para a Sorte de halfling)
  function d20(S, motivo, bonus, modo, alvo, rotAlvo, h) {
    var a = dado(S, 20), b = modo ? dado(S, 20) : null, nota = '';
    var k = modo === 'vantagem' ? Math.max(a, b) : modo === 'desvantagem' ? Math.min(a, b) : a;
    if (k === 1 && h && h.especie === 'halfling') { k = dado(S, 20); nota = ' · Sorte de halfling: o 1 vira ' + k; }
    var total = k + bonus;
    var r = { motivo: motivo, d20: k, dados: b === null ? [a] : [a, b], bonus: bonus, modo: modo || 'normal', total: total, alvo: alvo == null ? null : alvo, rotAlvo: rotAlvo || null };
    r.ok = alvo == null ? null : total >= alvo;
    registrar(S, r);
    r.texto = motivo + ': d20 ' + (b === null ? '(' + a + ')' : '(' + a + ' e ' + b + ', vale ' + (modo === 'vantagem' ? Math.max(a, b) : Math.min(a, b)) + ' por ' + modo + ')') + nota + ' ' + sinal(bonus) + ' = ' + total;
    r.resumo = r.texto;
    return r;
  }
  function fecharD20(S, r, okFinal, extra) {
    r.ok = okFinal;
    var t = r.texto + (r.alvo != null ? ' contra ' + r.rotAlvo + ' ' + r.alvo : '') + ' → ' + (extra || (okFinal ? 'sucesso' : 'falha'));
    r.resumo = t;
    out(S, 'dado', t);
  }
  function teste(S, motivo, bonus, modo, cd, h) {
    var r = d20(S, motivo, bonus, modo, cd, 'CD', h);
    fecharD20(S, r, r.total >= cd);
    return r;
  }
  // partes: [{n, l}] ; o: {crit, sufixo, min3}
  function rolarSoma(S, motivo, partes, bonus, o) {
    o = o || {};
    var faces = [], total = 0, expr = [];
    partes.forEach(function (p) {
      var n = o.crit ? p.n * 2 : p.n;
      expr.push(n + 'd' + p.l);
      for (var i = 0; i < n; i++) { var v = dado(S, p.l); if (o.min3 && v < 3) v = 3; faces.push(v); total += v; }
    });
    total = Math.max(0, total + bonus);
    var t = motivo + ': ' + expr.join(' + ') + ' (' + faces.join(', ') + ')' + (bonus ? ' ' + sinal(bonus) : '') + ' = ' + total + (o.sufixo ? ' ' + o.sufixo : '') + (o.crit ? ' · crítico' : '');
    registrar(S, { motivo: motivo, dados: faces, bonus: bonus, total: total, modo: 'soma', resumo: t });
    out(S, 'dado', t);
    return total;
  }
  function bencao(S, h) {
    if (!h.fx || !h.fx.bencao) return 0;
    return dado(S, 4);
  }

  /* ------------------------------------------------------------------ campanha viva */
  function AV(S) { return AVENTURAS[S.av]; }
  function fato(S, txt) {
    S.fatos.push({ n: ++S.nFato, cena: S.cena, dia: S.dia, x: txt });
    out(S, 'fato', txt);
  }
  function desvio(S, previsto, feito, motivo) {
    S.desvios.push({ cena: S.cena, previsto: previsto, feito: feito, motivo: motivo });
    out(S, 'fato', 'Desvio do roteiro: ' + feito + ' Motivo: ' + motivo);
  }
  function curar(h, q) {
    var antes = h.pv;
    h.pv = Math.min(h.pvMax, h.pv + q);
    if (h.pv > 0) h.caido = null;
    return h.pv - antes;
  }
  function pagar(S, q) { S.ouro = Math.max(0, S.ouro - q); }
  function checkpoint(S) {
    if (S.combate || S.fim) return;
    var c = clone(S); c.ckpt = null;
    S.ckpt = c; S.nCkpt = (S.nCkpt || 0) + 1;
  }
  function nivelarHeroi(h) {
    var cl = CLASSES[h.classe];
    if (h.nivel >= 2) return 0;
    var g = cl.pvNivel + mod(h.atr.con) + (h.especie === 'anao' ? 1 : 0);
    h.nivel = 2; h.pvMax += g; if (!h.morto) h.pv += g; h.dvTotal = 2; h.dv += 1;
    if (cl.conj) {
      h.espacosMax = 3; h.espacos += 1;
      var nova = cl.listaMagias.filter(function (m) { return h.magias.indexOf(m) < 0; })[0];
      if (nova) h.magias.push(nova);
    }
    if (h.classe === 'guerreiro') h.surto = 1;
    if (h.classe === 'clerigo') h.canalizar = 2;
    if (h.classe === 'mago' && h.pericias.indexOf('arcanismo') >= 0 && h.dobro.indexOf('arcanismo') < 0) h.dobro.push('arcanismo');
    return g;
  }
  function subirNivel(S, onde) {
    if (S.nivel >= 2) return;
    S.nivel = 2;
    var linhas = ['Marco da história: o grupo chega ao nível 2.'];
    S.herois.forEach(function (h) {
      var cl = CLASSES[h.classe], antes = h.magias.length, g = nivelarHeroi(h);
      if (!g) return;
      var l = h.nome + ': PV máximos ' + h.pvMax + ' (+' + g + ')';
      if (cl.conj) l += ', 3 espaços de magia' + (h.magias.length > antes ? ', nova magia ' + MAGIAS[h.magias[h.magias.length - 1]].nome : '');
      linhas.push(l + '. ' + cl.tracos2.join(' '));
    });
    out(S, 'sistema', linhas.join('\n'));
    fato(S, (S.herois.length > 1 ? 'O grupo alcançou' : S.herois[0].nome + ' alcançou') + ' o nível 2 ' + onde + '.');
  }

  /* ------------------------------------------------------------------ vereditos (toda tentativa tem um) */
  function anotarVeredito(S, a, v) {
    if (!S.vereditos[a.id]) S.vereditos[a.id] = { rot: a.rot, tipo: v.tipo, per: v.per || null, cd: v.cd || null };
  }
  function textoVeredito(v) {
    if (v.tipo === 'teste') {
      var p = PERICIAS[v.per];
      return 'teste de ' + p.nome + ' (' + ATR[p.atr] + '), CD ' + v.cd + ' · ' + escala(v.cd) + (v.grupo ? ' · teste em grupo: passa se pelo menos metade passar' : '') + (v.modo ? ' · com ' + v.modo + (v.porque ? ' (' + v.porque + ')' : '') : '');
    }
    if (v.tipo === 'impossivel') return 'impossível';
    return 'consegue de cara';
  }
  function testePericia(S, h, v) {
    if (v.grupo && grupo(S)) {
      var passou = 0, lista = ativos(S);
      lista.forEach(function (x) { if (teste(S, PERICIAS[v.per].nome + ' de ' + x.nome, bonusPericia(x, v.per), v.modo || null, v.cd, x).ok) passou++; });
      var ok = passou * 2 >= lista.length;
      out(S, 'dado', 'Teste em grupo: ' + passou + ' de ' + lista.length + ' passaram → ' + (ok ? 'sucesso' : 'falha'));
      return { ok: ok };
    }
    var r = teste(S, PERICIAS[v.per].nome + (S.herois.length > 1 ? ' de ' + h.nome : ''), bonusPericia(h, v.per), v.modo || null, v.cd, h);
    return { ok: r.ok, total: r.total };
  }
  function tentar(S, a, h) {
    var v = a.veredito ? a.veredito(S, h) : { tipo: 'decara' };
    anotarVeredito(S, a, v);
    if (v.tipo === 'impossivel') {
      out(S, 'veredito', 'Veredito: impossível.');
      out(S, 'narra', v.motivo || 'Isso não está ao alcance do seu personagem.');
      return;
    }
    if (v.tipo === 'decara') { a.fazer(S, { ok: true }, h); return; }
    var chave = a.id + '@' + (v.grupo ? 'grupo' : h.id);
    if (S.tentou[chave] && !a.repetivel) {
      out(S, 'narra', (S.herois.length > 1 && !v.grupo ? h.nome + ' já tentou isso e nada mudou desde então. Outro herói pode tentar, ou o grupo procura outro caminho.' : 'Você já tentou isso e nada mudou desde então. O veredito seria o mesmo; procure outro caminho.'));
      return;
    }
    out(S, 'veredito', 'Veredito: ' + textoVeredito(v) + '.');
    S.tentou[chave] = true;
    a.fazer(S, testePericia(S, h, v), h);
  }
