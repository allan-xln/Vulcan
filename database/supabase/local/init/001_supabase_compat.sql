do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;

  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;

  if not exists (select 1 from pg_roles where rolname = 'service_role') then
    create role service_role nologin bypassrls;
  end if;
end
$$;

create schema if not exists auth;

create extension if not exists pgcrypto;
create extension if not exists citext;

create table if not exists auth.users (
  id uuid primary key,
  instance_id uuid,
  aud text default 'authenticated',
  role text default 'authenticated',
  email citext unique,
  encrypted_password text,
  email_confirmed_at timestamptz,
  invited_at timestamptz,
  confirmation_token text default '',
  confirmation_sent_at timestamptz,
  recovery_token text default '',
  recovery_sent_at timestamptz,
  email_change_token_new text default '',
  email_change text default '',
  email_change_sent_at timestamptz,
  last_sign_in_at timestamptz,
  raw_app_meta_data jsonb not null default '{}'::jsonb,
  raw_user_meta_data jsonb not null default '{}'::jsonb,
  is_super_admin boolean,
  phone text,
  phone_confirmed_at timestamptz,
  phone_change text default '',
  phone_change_token text default '',
  phone_change_sent_at timestamptz,
  confirmed_at timestamptz,
  email_change_token_current text default '',
  email_change_confirm_status smallint default 0,
  banned_until timestamptz,
  reauthentication_token text default '',
  reauthentication_sent_at timestamptz,
  is_sso_user boolean not null default false,
  deleted_at timestamptz,
  is_anonymous boolean not null default false,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table auth.users add column if not exists instance_id uuid;
alter table auth.users add column if not exists aud text default 'authenticated';
alter table auth.users add column if not exists role text default 'authenticated';
alter table auth.users add column if not exists encrypted_password text;
alter table auth.users add column if not exists email_confirmed_at timestamptz;
alter table auth.users add column if not exists invited_at timestamptz;
alter table auth.users add column if not exists confirmation_token text default '';
alter table auth.users add column if not exists confirmation_sent_at timestamptz;
alter table auth.users add column if not exists recovery_token text default '';
alter table auth.users add column if not exists recovery_sent_at timestamptz;
alter table auth.users add column if not exists email_change_token_new text default '';
alter table auth.users add column if not exists email_change text default '';
alter table auth.users add column if not exists email_change_sent_at timestamptz;
alter table auth.users add column if not exists last_sign_in_at timestamptz;
alter table auth.users add column if not exists raw_app_meta_data jsonb not null default '{}'::jsonb;
alter table auth.users add column if not exists is_super_admin boolean;
alter table auth.users add column if not exists phone text;
alter table auth.users add column if not exists phone_confirmed_at timestamptz;
alter table auth.users add column if not exists phone_change text default '';
alter table auth.users add column if not exists phone_change_token text default '';
alter table auth.users add column if not exists phone_change_sent_at timestamptz;
alter table auth.users add column if not exists confirmed_at timestamptz;
alter table auth.users add column if not exists email_change_token_current text default '';
alter table auth.users add column if not exists email_change_confirm_status smallint default 0;
alter table auth.users add column if not exists banned_until timestamptz;
alter table auth.users add column if not exists reauthentication_token text default '';
alter table auth.users add column if not exists reauthentication_sent_at timestamptz;
alter table auth.users add column if not exists is_sso_user boolean not null default false;
alter table auth.users add column if not exists deleted_at timestamptz;
alter table auth.users add column if not exists is_anonymous boolean not null default false;

create index if not exists users_instance_id_email_idx on auth.users (instance_id, lower(email::text));
create index if not exists users_email_partial_key on auth.users (email) where email is not null;

create schema if not exists storage;

create table if not exists storage.buckets (
  id text primary key,
  name text not null unique,
  owner uuid,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  public boolean not null default false,
  avif_autodetection boolean not null default false,
  file_size_limit bigint,
  allowed_mime_types text[]
);

create table if not exists storage.objects (
  id uuid primary key default gen_random_uuid(),
  bucket_id text references storage.buckets(id) on delete cascade,
  name text,
  owner uuid,
  metadata jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  last_accessed_at timestamptz,
  path_tokens text[] generated always as (string_to_array(name, '/')) stored
);

create or replace function storage.foldername(name text)
returns text[]
language sql
immutable
as $$
  select string_to_array(trim(both '/' from coalesce(name, '')), '/')
$$;

create or replace function auth.uid()
returns uuid
language sql
stable
as $$
  select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;

create or replace function auth.role()
returns text
language sql
stable
as $$
  select coalesce(nullif(current_setting('request.jwt.claim.role', true), ''), 'anon')
$$;

grant usage on schema auth to postgres, anon, authenticated, service_role;
grant usage on schema storage to postgres, anon, authenticated, service_role;
grant select, insert, update, delete on auth.users to postgres, service_role;
grant select on auth.users to authenticated;
grant select, insert, update, delete on storage.buckets, storage.objects to postgres, service_role;
grant select on storage.buckets to anon, authenticated;
