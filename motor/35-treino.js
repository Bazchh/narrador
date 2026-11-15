  /* ------------------------------------------------------------------ aventura: O Pátio de Treino */
  function treinoInimigos(n) {
    return { bonecos: varios(n >= 3 ? 2 : 1, 'b', 'boneco', 'Boneco de treino', n === 2 ? 14 : 9) };
  }
  var TREINO_GRUPOS = {
    bonecos: {
      zonas: {}, zonaPadrao: 'medio', alerta: 'bonecosAlerta', onde: 'no pátio de treino', fugaPara: 'patio', acordaEm: 'patio', semMorte: true,
      textoFuga: 'Dorval ergue a mão e os bonecos travam no lugar. “Recuar também é tática. Respire e volte quando quiser.”',
      textoQueda: function () { return 'Um balde de água fria. Dorval está de pé ao lado, sem pressa nenhuma. “No pátio, cair não custa nada. Lá fora, custa. Sente no banco, descanse e tente de novo.” Quem caiu está com 1 ponto de vida.'; },
      aoVencer: function (S) {
        S.f.venceu = true;
        out(S, 'narra', 'O último boneco desaba num monte de palha e ripas. Dorval bate palmas, duas vezes, devagar.\n\n“Serve. Você já sabe o que precisa: se mexer, bater e não morrer. O resto a estrada ensina.”');
        fato(S, (S.herois.length > 1 ? 'O grupo venceu' : 'Você venceu') + ' os bonecos de treino do mestre Dorval.');
      }
    }
  };
  var TREINO_CENAS = {
    patio: {
      nome: 'Pátio de Treino', lugar: 'Quartel da guarda de Pedra-Funda',
      desc: function (S) { return 'Pátio de terra batida entre muros altos. Um fosso raso, uma trave de equilíbrio, um portão de ferro fechado e, no meio, ' + (S.f.venceu ? 'os restos dos bonecos de treino.' : 'bonecos de palha e madeira com espadas de pau.') + ' O mestre de armas Dorval observa de braços cruzados.'; },
      presentes: function () { return ['Dorval, o mestre de armas']; },
      seguro: function () { return true; },
      longo: function (S) { return (S.herois.length > 1 ? 'O grupo se estica' : 'Você se estica') + ' no banco comprido do alojamento e dorme sem sonhar. Amanhece o dia ' + S.dia + ', com Dorval batendo uma colher num caldeirão.'; },
      entrar: function (S, o) {
        if (o.primeira) {
          out(S, 'narra', 'O pátio do quartel cheira a terra molhada e palha. No meio dele, bonecos de treino com espadas de madeira; mais adiante, um fosso raso, uma trave de equilíbrio e um portão de ferro.\n\nDorval, o mestre de armas, tem um braço só e olhos que não perdem nada. “Antes de subir qualquer morro atrás de qualquer sino, mostre o que sabe fazer. Aqui pode errar à vontade.”\n\nFale com Dorval, experimente o fosso e a trave, ou vá direto aos bonecos.');
          return;
        }
        if (!o.calado) out(S, 'narra', 'O pátio continua onde estava, e Dorval também.');
      },
      acoes: [
        {
          id: 'falar_dorval', rot: 'Falar com Dorval', re: /dorval|mestre|falar|falo|convers|pergunt/,
          fazer: function (S) {
            S.f.falou = true;
            out(S, 'narra', '“É simples”, diz Dorval. “Quando o que você tenta pode dar errado, alguém joga um dado de vinte lados e soma o seu treino. Passou do número da dificuldade, deu certo. O fosso e a trave são isso.”\n\nEle aponta os bonecos com o queixo. “Briga tem vez: cada um se mexe, faz uma coisa e passa adiante. De longe você atira, de perto você bate. Quem cai, cai. Vá lá.”');
          }
        },
        {
          id: 'saltar_fosso', rot: 'Saltar o fosso', re: /fosso|salt|pul/, repetivel: true,
          veredito: function () { return { tipo: 'teste', per: 'atletismo', cd: 10 }; },
          fazer: function (S, r) {
            if (r.ok) out(S, 'narra', 'Três passos de corrida e o chão some debaixo de você por um instante. Você cai do outro lado, de pé. Dorval não diz nada, que é o elogio dele.');
            else out(S, 'narra', 'Você calcula mal o último passo e desce no fosso até os joelhos, na lama. Não machuca nada além do orgulho. “De novo, quando quiser”, diz Dorval.');
          }
        },
        {
          id: 'trave', rot: 'Atravessar a trave de equilíbrio', re: /trave|equilibr|atravess/, repetivel: true,
          veredito: function () { return { tipo: 'teste', per: 'acrobacia', cd: 10 }; },
          fazer: function (S, r) {
            if (r.ok) out(S, 'narra', 'Um pé na frente do outro, braços abertos, olhos na ponta da trave e não no chão. Você chega ao fim sem balançar.');
            else out(S, 'narra', 'No meio da trave o corpo decide ir para um lado e os pés para o outro. Você desce pulando, sem cair de fato. “Olhe para onde quer chegar, não para onde tem medo de cair”, diz Dorval.');
          }
        },
        {
          id: 'portao', rot: 'Erguer o portão de ferro', re: /portao|erguer|levantar|ferro|grade/,
          veredito: function () { return { tipo: 'impossivel', motivo: 'Três homens e um guincho levantam esse portão. Sozinho, ninguém levanta: nem com sorte nos dados. Dorval ri pelo nariz. “Nem tudo se resolve tentando. Às vezes o mestre só diz que não dá.”' }; },
          fazer: function () {}
        },
        {
          id: 'lutar_bonecos', rot: 'Enfrentar os bonecos de treino', re: /boneco|lut|atac|ataq|comb|brig|enfrent/,
          se: function (S) { return !S.f.venceu; },
          fazer: function (S) {
            out(S, 'narra', 'Dorval dá um assobio curto. Os bonecos estremecem, erguem as espadas de pau e viram a cabeça de palha na sua direção. “Encantamento velho do quartel”, ele explica. “Batem fraco. Mas batem.”');
            iniciarCombate(S, 'bonecos', {});
          }
        },
        {
          id: 'descansar_banco', rot: 'Dormir no alojamento (descanso longo)', re: /dorm|alojamento|banco|descans|noite/,
          fazer: function (S) { descansoLongo(S); }
        },
        {
          id: 'concluir', rot: 'Encerrar o treino', re: /encerr|conclu|termin|acab|ir embora|pronto|chega/,
          se: function (S) { return S.f.venceu || S.f.falou; },
          fazer: function (S) {
            out(S, 'narra', (S.f.venceu ? 'Dorval aperta sua mão com a única que tem. ' : 'Dorval dá de ombros. “Os bonecos ficam para outro dia.” ') + '“Tem um sino de pedra tocando sozinho lá no alto do morro, e uma estalajadeira oferecendo ouro a quem fizer parar. Se quiser trabalho de verdade, procure Dona Marga, na Estalagem do Lampião.”');
            fato(S, 'O treino com o mestre Dorval terminou. Ele indicou Dona Marga, na Estalagem do Lampião.');
            S.fim = { tipo: 'vitoria' };
            out(S, 'titulo', 'Fim do treino');
            out(S, 'sistema', resumo(S));
          }
        }
      ],
      topicos: [
        { re: /dorval|mestre/, txt: function () { return 'Dorval é o mestre de armas do quartel: um braço só, trinta anos de guarda e pouca paciência para conversa.'; } },
        { re: /boneco/, txt: function (S) { return S.f.venceu ? 'Os bonecos viraram palha e ripas.' : 'Bonecos de palha e madeira, movidos por um encantamento antigo. Batem fraco, com espadas de pau, e não matam ninguém.'; } },
        { re: /sino|morro|marga|trabalho/, txt: function () { return 'Dorval ainda não falou disso. Talvez fale quando o treino acabar.'; } }
      ],
      saidas: function () { return []; }
    }
  };

  /* ------------------------------------------------------------------ estante de aventuras */
  var AVENTURAS = {
    treino: {
      id: 'treino', titulo: 'O Pátio de Treino', duracao: '5 a 10 minutos', nivel: 'Nível 1', tipo: 'Treino',
      resumo: 'Uma cena só, para aprender sem risco: testes de perícia, um combate contra bonecos encantados e descanso. Ninguém morre aqui.',
      inicio: 'patio', cenas: TREINO_CENAS, grupos: TREINO_GRUPOS, inimigos: treinoInimigos, ondeLongo: 'Use o alojamento do quartel.',
      notas: function () { return 'É um treino sem risco. Dorval é seco, prático e bem-humorado à sua maneira. Não existe nada fora do pátio nesta aventura.'; }
    },
    sino: {
      id: 'sino', titulo: 'O Sino de Pedra-Funda', duracao: '30 a 45 minutos', nivel: 'Níveis 1 e 2', tipo: 'Aventura',
      resumo: 'Há três noites, o sino de pedra da capela velha toca sozinho à meia-noite. O sacristão subiu para ver e não voltou. Cinco cenas, três encontros, um segredo e vários finais.',
      inicio: 'estalagem', cenas: SINO_CENAS, grupos: SINO_GRUPOS, inimigos: sinoInimigos, ondeLongo: 'Só na Estalagem do Lampião.', temSegredo: true,
      notas: function (S) {
        var n = ['Vila pequena e assustada de Pedra-Funda. Tom sóbrio, de conto de assombração, sem humor forçado.'];
        n.push('Dona Marga, a estalajadeira: prática, direta, cansada. Bento, o caçador: resmungão, sabe da trilha.');
        if (!S.f.segredo) n.push('O motivo de tudo isso ainda NÃO foi descoberto pelos heróis. Não explique por que o sino toca nem o que Ivo quer; quem perguntar recebe só o que a vila sabe.');
        else n.push('Os heróis já sabem: Ivo toca o sino para trazer de volta a filha morta, Lívia. Trate o assunto com delicadeza.');
        return n.join(' ');
      }
    }
  };
