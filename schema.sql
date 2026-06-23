create table if not exists troqueles (
  codigo_troquel text primary key,
  monodroga text not null,
  potencia text,
  forma_farmacologica text,
  laboratorio text,
  estado text check (estado in ('activa','baja')) default 'activa',
  pvp numeric not null default 0,
  fecha_vigencia_precio date not null
);

create table if not exists convenio_oyte (
  codigo_troquel text primary key references troqueles(codigo_troquel),
  categoria text not null default 'Oncología y Ttos. Especiales',
  fecha_alta_convenio date,
  fecha_baja_convenio date
);

create table if not exists liquidaciones (
  id_liquidacion text primary key,
  codigo_troquel text references troqueles(codigo_troquel),
  periodo text not null,
  afiliado_id text,
  cantidad_cajas integer default 0,
  pvp_remito numeric default 0,
  pvp_descuento numeric default 0
);

create table if not exists simulacion_resultados (
  id_simulacion uuid primary key default gen_random_uuid(),
  tipo_caso text check (tipo_caso in ('A','B','C','D')),
  codigo_troquel text,
  fecha_corrida timestamptz default now(),
  recomendacion boolean,
  motivo text,
  facturacion_actual_anual numeric default 0,
  facturacion_proyectada_anual numeric default 0,
  detalle_consumo jsonb default '{}'::jsonb
);

create index if not exists ix_troqueles_monodroga on troqueles(monodroga);
create index if not exists ix_liq_troquel_periodo on liquidaciones(codigo_troquel, periodo);
