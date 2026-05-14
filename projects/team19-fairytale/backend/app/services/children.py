from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from app.db.postgres import get_db_connection


async def create_child(
    *,
    user_id: str,
    name: str,
    age: int,
    personality: str,
    favorite_character: str,
    favorite_toy: str = "",
    family_relationship: str = "",
) -> Mapping[str, object]:
    async with get_db_connection() as connection:
        async with connection.transaction():
            async with connection.cursor() as cursor:
                await cursor.execute(
                    """
                    insert into public.children
                        (user_id, name, age, personality, favorite_character,
                         favorite_toy, family_relationship)
                    values (%s::uuid, %s, %s, %s, %s, %s, %s)
                    returning
                        id::text as id,
                        user_id::text as user_id,
                        name,
                        age,
                        personality,
                        favorite_character,
                        favorite_toy,
                        family_relationship,
                        created_at,
                        updated_at
                    """,
                    (user_id, name, age, personality, favorite_character,
                     favorite_toy, family_relationship),
                )
                return await cursor.fetchone()


async def get_children_by_user(user_id: str) -> list[Mapping[str, object]]:
    async with get_db_connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                select
                    id::text as id,
                    user_id::text as user_id,
                    name,
                    age,
                    personality,
                    favorite_character,
                    favorite_toy,
                    family_relationship,
                    created_at,
                    updated_at
                from public.children
                where user_id = %s::uuid
                order by created_at
                """,
                (user_id,),
            )
            return await cursor.fetchall()


async def get_child_by_id(child_id: str) -> Mapping[str, object] | None:
    async with get_db_connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                select
                    id::text as id,
                    user_id::text as user_id,
                    name,
                    age,
                    personality,
                    favorite_character,
                    favorite_toy,
                    family_relationship,
                    created_at,
                    updated_at
                from public.children
                where id = %s::uuid
                limit 1
                """,
                (child_id,),
            )
            return await cursor.fetchone()


async def get_child_for_user(child_id: str, user_id: str) -> Mapping[str, object] | None:
    """Return a child row owned by the given user, or None."""
    async with get_db_connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                select
                    id::text as id,
                    user_id::text as user_id,
                    name,
                    age,
                    personality,
                    favorite_character,
                    favorite_toy,
                    family_relationship,
                    created_at,
                    updated_at
                from public.children
                where id = %s::uuid
                  and user_id = %s::uuid
                limit 1
                """,
                (child_id, user_id),
            )
            return await cursor.fetchone()


async def update_child(child_id: str, **fields: object) -> Mapping[str, object]:
    set_clauses = []
    params: list[object] = []
    for key, value in fields.items():
        set_clauses.append(f"{key} = %s")
        params.append(value)
    set_clauses.append("updated_at = now()")
    params.append(child_id)

    async with get_db_connection() as connection:
        async with connection.transaction():
            async with connection.cursor() as cursor:
                await cursor.execute(
                    f"""
                    update public.children
                    set {", ".join(set_clauses)}
                    where id = %s::uuid
                    returning
                        id::text as id,
                        user_id::text as user_id,
                        name,
                        age,
                        personality,
                        favorite_character,
                        created_at,
                        updated_at
                    """,
                    params,
                )
                return await cursor.fetchone()


async def delete_child(child_id: str) -> None:
    async with get_db_connection() as connection:
        async with connection.transaction():
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "delete from public.children where id = %s::uuid",
                    (child_id,),
                )


async def create_experience(
    *,
    child_id: str,
    content: str,
    experienced_at: date | None = None,
) -> Mapping[str, object]:
    async with get_db_connection() as connection:
        async with connection.transaction():
            async with connection.cursor() as cursor:
                if experienced_at is not None:
                    await cursor.execute(
                        """
                        insert into public.experiences
                            (child_id, content, experienced_at)
                        values (%s::uuid, %s, %s)
                        returning
                            id::text as id,
                            child_id::text as child_id,
                            content,
                            experienced_at,
                            created_at
                        """,
                        (child_id, content, experienced_at),
                    )
                else:
                    await cursor.execute(
                        """
                        insert into public.experiences
                            (child_id, content)
                        values (%s::uuid, %s)
                        returning
                            id::text as id,
                            child_id::text as child_id,
                            content,
                            experienced_at,
                            created_at
                        """,
                        (child_id, content),
                    )
                return await cursor.fetchone()


async def get_experiences_by_child(child_id: str) -> list[Mapping[str, object]]:
    async with get_db_connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                select
                    id::text as id,
                    child_id::text as child_id,
                    content,
                    experienced_at,
                    created_at
                from public.experiences
                where child_id = %s::uuid
                order by experienced_at desc, created_at desc
                """,
                (child_id,),
            )
            return await cursor.fetchall()
