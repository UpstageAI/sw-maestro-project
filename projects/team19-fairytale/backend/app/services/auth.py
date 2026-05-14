from __future__ import annotations

from collections.abc import Mapping

from psycopg import errors

from app.db.postgres import get_db_connection
from app.security import hash_password, verify_password


class UserAlreadyExistsError(ValueError):
    """Raised when a user tries to register with an existing email address."""


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def create_user(*, email: str, password: str) -> Mapping[str, object]:
    normalized_email = normalize_email(email)
    password_hash = hash_password(password)

    try:
        async with get_db_connection() as connection:
            async with connection.transaction():
                async with connection.cursor() as cursor:
                    await cursor.execute(
                        """
                        insert into public.users (email, password_hash)
                        values (%s, %s)
                        returning
                            id::text as id,
                            email,
                            is_active,
                            created_at,
                            updated_at
                        """,
                        (normalized_email, password_hash),
                    )
                    user = await cursor.fetchone()
    except errors.UniqueViolation as exc:
        raise UserAlreadyExistsError("A user with this email already exists.") from exc

    return user


async def authenticate_user(*, email: str, password: str) -> Mapping[str, object] | None:
    user = await get_user_by_email(email)
    if user is None or not verify_password(password, str(user["password_hash"])):
        return None
    return user


async def get_user_by_email(email: str) -> Mapping[str, object] | None:
    normalized_email = normalize_email(email)

    async with get_db_connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                select
                    id::text as id,
                    email,
                    password_hash,
                    is_active,
                    created_at,
                    updated_at
                from public.users
                where email = %s
                limit 1
                """,
                (normalized_email,),
            )
            return await cursor.fetchone()


async def get_user_by_id(user_id: str) -> Mapping[str, object] | None:
    async with get_db_connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                select
                    id::text as id,
                    email,
                    is_active,
                    created_at,
                    updated_at
                from public.users
                where id = %s::uuid
                limit 1
                """,
                (user_id,),
            )
            return await cursor.fetchone()
