-- Campanha viva: um arquivo SQLite por campanha. Migração 0001.
-- Regra do arquivo: o diário só recebe inserção. Quem tentar alterar ou apagar
-- recebe erro do banco, não aviso do código.
pragma foreign_keys = on;
pragma journal_mode = wal;

create table campanha (
  id              text primary key,                 -- uuid
  nome            text not null,
  aventura_id     text not null,                    -- id na pasta de aventuras
  modulo_versao   integer not null,                 -- versão fixada (C01)
  semente         text not null,                    -- semente das rolagens (E01)
  classificacao   text not null check (classificacao in ('livre','14','16','adulto')),
  tom             text not null default 'serio',
  configuracao    text not null default '{}',       -- json: dado físico, progressão, regras opcionais, limite de custo (C10)
  criada_em       text not null default (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- Ficha versionada: cada subida de nível ou mudança de regra é uma versão nova (B01, B04).
create table personagem (
  id              text not null,
  versao          integer not null,
  campanha_id     text not null references campanha (id),
  nome            text not null,
  origem          text not null check (origem in ('criado','pre_gerado')),
  ficha           text not null,                    -- json validado pelo motor
  srd_versao      text not null,
  criado_em       text not null default (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  primary key (id, versao)
);

create table sessao (
  id              text primary key,
  campanha_id     text not null references campanha (id),
  numero          integer not null,
  aberta_em       text not null default (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  encerrada_em    text,
  motivo_fim      text check (motivo_fim in ('encerrada','interrompida','retomada')),
  unique (campanha_id, numero)
);

-- O diário: toda coisa que aconteceu, em ordem, só inserção (G01).
create table diario (
  seq             integer primary key autoincrement,
  campanha_id     text not null references campanha (id),
  sessao_id       text references sessao (id),
  tipo            text not null check (tipo in (
                    'fato','desvio','veredito','rolagem','consulta','verificacao',
                    'recusa','configuracao','sessao','resumo','revisao','custo','ocorrencia')),
  cena_id         text,                             -- item canônico da cena, se houver
  origem          text not null,                    -- caso de uso que gravou (C05, D04...)
  dados           text not null,                    -- json com o conteúdo do registro
  registrado_em   text not null default (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
create index diario_por_campanha on diario (campanha_id, seq);
create index diario_por_tipo     on diario (campanha_id, tipo, seq);

create trigger diario_sem_update before update on diario
begin select raise(abort, 'diario_somente_insercao'); end;
create trigger diario_sem_delete before delete on diario
begin select raise(abort, 'diario_somente_insercao'); end;

-- Rolagens: o diário de dados (E01). O contador é a posição no gerador da campanha.
create table rolagem (
  seq             integer primary key references diario (seq),
  campanha_id     text not null references campanha (id),
  contador        integer,                          -- nulo quando informada (dado físico)
  expressao       text not null,                    -- 1d20+3
  modo            text not null check (modo in ('normal','vantagem','desvantagem')),
  dados           text not null,                    -- json: cada dado
  modificadores   text not null,                    -- json: composição
  total           integer not null,
  motivo          text not null,
  informada       integer not null default 0 check (informada in (0,1)),
  unique (campanha_id, contador)
);
create trigger rolagem_sem_update before update on rolagem
begin select raise(abort, 'diario_somente_insercao'); end;
create trigger rolagem_sem_delete before delete on rolagem
begin select raise(abort, 'diario_somente_insercao'); end;

-- Fatos: o estado do mundo, com conhecimento do personagem e encadeamento (F01, F04).
create table fato (
  seq             integer primary key references diario (seq),
  campanha_id     text not null references campanha (id),
  tipo_fato       text not null check (tipo_fato in (
                    'estado_local','estado_personagem','posse','relacao','conhecimento','evento')),
  referencia      text,                             -- item canônico afetado
  conhecimento    text not null check (conhecimento in ('conhecido','oculto','acredita')),
  substitui_seq   integer references fato (seq),    -- estado anterior que este sucede; nunca apagado
  resumo          text not null
);
create trigger fato_sem_update before update on fato
begin select raise(abort, 'diario_somente_insercao'); end;
create trigger fato_sem_delete before delete on fato
begin select raise(abort, 'diario_somente_insercao'); end;

-- Desvios do canônico, com motivo e regra invocada (F02).
create table desvio (
  seq             integer primary key references diario (seq),
  campanha_id     text not null references campanha (id),
  item_canonico   text,                             -- o que o módulo dizia
  o_que_mudou     text not null,
  motivo          text,                             -- nulo = "sem motivo informado", elevado na revisão
  regra           text,                             -- RN-02, RN-03...
  revisado        integer not null default 0 check (revisado in (0,1,2))  -- 0 pendente, 1 aprovado, 2 ruim
);
-- revisado é a única coluna que muda, e só de 0 para 1 ou 2 (F06): o passado não muda, a marca sim.
create trigger desvio_so_marca before update on desvio
when new.seq <> old.seq or new.item_canonico is not old.item_canonico or new.o_que_mudou <> old.o_que_mudou
  or new.motivo is not old.motivo or new.regra is not old.regra or old.revisado <> 0
begin select raise(abort, 'desvio_so_marca_de_revisao'); end;
create trigger desvio_sem_delete before delete on desvio
begin select raise(abort, 'diario_somente_insercao'); end;

-- Vereditos, para a consistência (C04, C05, G04).
create table veredito (
  seq             integer primary key references diario (seq),
  campanha_id     text not null references campanha (id),
  situacao        text not null,                    -- descrição comparável
  tipo            text not null check (tipo in ('de_cara','impossivel','teste')),
  pericia         text,
  dificuldade     integer check (dificuldade is null or dificuldade between 5 and 30),
  pergunta        integer not null default 0 check (pergunta in (0,1)),  -- 1 = "e se eu fizer?" (C04)
  rolagem_seq     integer references rolagem (seq),
  divergiu_de     integer references veredito (seq),
  motivo_divergencia text
);
create trigger veredito_sem_update before update on veredito
begin select raise(abort, 'diario_somente_insercao'); end;
create trigger veredito_sem_delete before delete on veredito
begin select raise(abort, 'diario_somente_insercao'); end;

-- Instantâneo do estado para abertura rápida; o diário continua sendo a verdade (G01, C02).
create table instantaneo (
  campanha_id     text not null references campanha (id),
  ate_seq         integer not null,
  estado          text not null,                    -- json do estado consolidado
  gravado_em      text not null default (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  primary key (campanha_id, ate_seq)
);

-- Regras de mesa dadas na revisão (F06), aplicadas ao mestre dali em diante.
create table regra_de_mesa (
  id              integer primary key autoincrement,
  campanha_id     text not null references campanha (id),
  texto           text not null,
  origem_seq      integer references diario (seq),
  ativa           integer not null default 1 check (ativa in (0,1)),
  criada_em       text not null default (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
