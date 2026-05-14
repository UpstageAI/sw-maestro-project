-- pets soft delete RPC.
--
-- 배경: pets_select_own_active 정책이 deleted_at IS NULL을 referenced column으로 포함.
-- PostgreSQL은 UPDATE가 SELECT policy의 referenced column을 변경하면 NEW row를 SELECT
-- policy USING으로 재검사 → deleted_at = now() 시 본 정책이 NEW를 거부 → 42501.
-- 직접 UPDATE는 클라이언트(BFF)에서 동작 불가하므로 SECURITY DEFINER RPC로 우회.
--
-- 보안: SECURITY DEFINER로 RLS bypass하지만, 함수 본문에서 명시적으로 (1) 펫 존재 +
-- 활성 여부 (2) 호출자가 owner인지 확인. PUBLIC EXECUTE는 REVOKE, authenticated만 허용.

create or replace function public.soft_delete_pet(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_owner uuid;
begin
  select owner_id into v_owner from public.pets
    where id = p_id and deleted_at is null;
  if v_owner is null then
    raise exception using errcode = 'P0002', message = 'pet not found';
  end if;
  if v_owner <> (select auth.uid()) then
    raise exception using errcode = '42501', message = 'not authorized';
  end if;
  update public.pets set deleted_at = now() where id = p_id;
end;
$$;

revoke all on function public.soft_delete_pet(uuid) from public;
grant execute on function public.soft_delete_pet(uuid) to authenticated;
