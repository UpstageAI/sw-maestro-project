create extension if not exists pgcrypto with schema extensions;

create or replace function public.update_updated_at_column()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = timezone('utc', now());
    return new;
end;
$$;

create table if not exists public.users (
    id uuid primary key default extensions.gen_random_uuid(),
    email text not null unique check (email = lower(email)),
    password_hash text not null,
    is_active boolean not null default true,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists users_created_at_idx on public.users (created_at desc);

drop trigger if exists users_set_updated_at on public.users;
create trigger users_set_updated_at
before update on public.users
for each row
execute function public.update_updated_at_column();

alter table public.users enable row level security;

revoke all on table public.users from anon, authenticated;
