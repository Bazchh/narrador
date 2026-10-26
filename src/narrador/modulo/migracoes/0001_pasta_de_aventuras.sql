-- Pasta de aventuras: um arquivo SQLite por aventura importada, ao lado do arquivo original.
-- Regra do arquivo: versão publicada do módulo canônico é imutável; só nasce versão nova.
pragma foreign_keys = on;

create table aventura (
  id                   text primary key,
  titulo               text not null,
  origem_arquivo       text not null,               -- caminho local, nunca copiado para fora (RN-09)
  impressao_digital    text not null unique,        -- hash do conteúdo (A01)
  formato              text not null check (formato in ('pdf','markdown','texto')),
  edicao_informada     text check (edicao_informada in ('2014','2024')),
  texto_parcial        integer not null default 0 check (texto_parcial in (0,1)),
  uso_pessoal_declarado integer not null default 1,
  importada_em         text not null default (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

create table texto_pagina (
  aventura_id          text not null references aventura (id),
  pagina               integer not null,
  texto                text not null,
  primary key (aventura_id, pagina)
);

-- Autorização de envio ao serviço de linguagem, registrada por importação (DC-12, A02).
create table autorizacao_envio (
  id                   integer primary key autoincrement,
  aventura_id          text not null references aventura (id),
  concedida            integer not null check (concedida in (0,1)),
  trechos              integer not null,            -- quantos trechos foram mostrados
  registrada_em        text not null default (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- Versões do módulo canônico (A03, A06). publicada_em nulo = rascunho.
create table modulo_versao (
  aventura_id          text not null references aventura (id),
  versao               integer not null,
  origem               text not null check (origem in ('importado','gerado','gerado_revisado')),
  publicada_em         text,
  impressao_texto      text not null,               -- hash do texto de origem no momento
  primary key (aventura_id, versao)
);

create table item_canonico (
  id                   text not null,
  aventura_id          text not null,
  versao               integer not null,
  tipo                 text not null check (tipo in (
                         'cena','local','personagem','criatura','item','gancho','segredo')),
  nome                 text not null,
  dados                text not null,               -- json
  pagina_origem        integer,
  incerto              integer not null default 0 check (incerto in (0,1)),
  segredo              integer not null default 0 check (segredo in (0,1)),
  condicao_descoberta  text,                        -- obrigatória quando segredo = 1
  primary key (id, aventura_id, versao),
  foreign key (aventura_id, versao) references modulo_versao (aventura_id, versao),
  check (segredo = 0 or condicao_descoberta is not null)
);

create table ligacao (
  aventura_id          text not null,
  versao               integer not null,
  de_item              text not null,
  para_item            text not null,
  tipo                 text not null check (tipo in ('leva_a','contem','sabe_de','possui','gatilho')),
  caminho_critico      integer not null default 0 check (caminho_critico in (0,1)),
  primary key (aventura_id, versao, de_item, para_item, tipo),
  foreign key (aventura_id, versao) references modulo_versao (aventura_id, versao)
);

-- Mapeamento de criaturas e itens para o SRD (A04).
create table mapeamento_srd (
  aventura_id          text not null,
  versao               integer not null,
  item_id              text not null,
  srd_id               text,                        -- nulo com ficha própria ou pendente
  srd_versao           text not null,
  ficha_propria        text,                        -- json, fica no módulo do dono, fora do produto
  pendente             integer not null default 0 check (pendente in (0,1)),
  fora_da_escala       integer not null default 0 check (fora_da_escala in (0,1)),
  primary key (aventura_id, versao, item_id),
  foreign key (aventura_id, versao) references modulo_versao (aventura_id, versao),
  check (pendente = 1 or srd_id is not null or ficha_propria is not null)
);

-- Imutabilidade: nada de uma versão publicada muda; só nasce versão nova (A06).
create trigger item_publicado_sem_update before update on item_canonico
when exists (select 1 from modulo_versao v where v.aventura_id = old.aventura_id and v.versao = old.versao and v.publicada_em is not null)
begin select raise(abort, 'versao_publicada_imutavel'); end;
create trigger item_publicado_sem_delete before delete on item_canonico
when exists (select 1 from modulo_versao v where v.aventura_id = old.aventura_id and v.versao = old.versao and v.publicada_em is not null)
begin select raise(abort, 'versao_publicada_imutavel'); end;
create trigger item_publicado_sem_insert before insert on item_canonico
when exists (select 1 from modulo_versao v where v.aventura_id = new.aventura_id and v.versao = new.versao and v.publicada_em is not null)
begin select raise(abort, 'versao_publicada_imutavel'); end;
create trigger ligacao_publicada_sem_mudanca before insert on ligacao
when exists (select 1 from modulo_versao v where v.aventura_id = new.aventura_id and v.versao = new.versao and v.publicada_em is not null)
begin select raise(abort, 'versao_publicada_imutavel'); end;
create trigger versao_publicada_fixa before update on modulo_versao
when old.publicada_em is not null
begin select raise(abort, 'versao_publicada_imutavel'); end;
