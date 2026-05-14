create table if not exists public.stories (
    id uuid primary key default extensions.gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    child_id uuid not null references public.children(id) on delete cascade,
    title text not null,
    body text not null,
    lesson text not null,
    image_url text,
    audio_url text,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists stories_user_id_idx on public.stories (user_id);
create index if not exists stories_child_id_idx on public.stories (child_id);

drop trigger if exists stories_set_updated_at on public.stories;
create trigger stories_set_updated_at
before update on public.stories
for each row
execute function public.update_updated_at_column();

alter table public.stories enable row level security;

revoke all on table public.stories from anon, authenticated;
