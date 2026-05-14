-- children 테이블
create table if not exists public.children (
    id uuid primary key default extensions.gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    name text not null,
    age integer not null check (age >= 0 and age <= 18),
    personality text not null default '',
    favorite_character text not null default '',
    favorite_toy text not null default '',
    family_relationship text not null default '',
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_children_user_id on public.children(user_id);

drop trigger if exists children_set_updated_at on public.children;
create trigger children_set_updated_at
before update on public.children
for each row
execute function public.update_updated_at_column();

alter table public.children enable row level security;

revoke all on table public.children from anon, authenticated;

-- experiences 테이블
create table if not exists public.experiences (
    id uuid primary key default extensions.gen_random_uuid(),
    child_id uuid not null references public.children(id) on delete cascade,
    content text not null,
    experienced_at date not null default current_date,
    created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_experiences_child_id on public.experiences(child_id);

alter table public.experiences enable row level security;

revoke all on table public.experiences from anon, authenticated;
