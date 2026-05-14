


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE EXTENSION IF NOT EXISTS "pg_net" WITH SCHEMA "extensions";






CREATE SCHEMA IF NOT EXISTS "private";


ALTER SCHEMA "private" OWNER TO "postgres";


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE TYPE "public"."mood_tag" AS ENUM (
    '행복',
    '신남',
    '평온',
    '졸림',
    '심심',
    '슬픔',
    '까칠'
);


ALTER TYPE "public"."mood_tag" OWNER TO "postgres";


CREATE TYPE "public"."pet_gender" AS ENUM (
    'male',
    'female',
    'unknown'
);


ALTER TYPE "public"."pet_gender" OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "private"."handle_new_user"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
declare
  v_name text;
begin
  v_name := left(
    coalesce(
      nullif(trim(coalesce(new.raw_user_meta_data->>'name', '')), ''),
      nullif(split_part(new.email, '@', 1), ''),
      'user'
    ),
    24
  );
  insert into public.profiles (id, display_name) values (new.id, v_name);
  return new;
end;
$$;


ALTER FUNCTION "private"."handle_new_user"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "private"."set_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
begin
  new.updated_at := now();
  return new;
end;
$$;


ALTER FUNCTION "private"."set_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "private"."usage_quotas_insert_guard"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
begin
  if new.generations_count <> 1 then
    raise exception 'usage_quotas INSERT must have generations_count = 1, got %', new.generations_count;
  end if;
  return new;
end;
$$;


ALTER FUNCTION "private"."usage_quotas_insert_guard"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "private"."usage_quotas_update_guard"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
begin
  if new.generations_count <= old.generations_count then
    raise exception 'usage_quotas UPDATE must increment generations_count (% -> %)', old.generations_count, new.generations_count;
  end if;
  return new;
end;
$$;


ALTER FUNCTION "private"."usage_quotas_update_guard"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."diaries" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "owner_id" "uuid" NOT NULL,
    "pet_id" "uuid" NOT NULL,
    "source_generation_id" "uuid" NOT NULL,
    "diary_text" "text" NOT NULL,
    "short_caption" "text" NOT NULL,
    "mood_tag" "public"."mood_tag" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "diaries_diary_text_check" CHECK ((("length"("diary_text") >= 50) AND ("length"("diary_text") <= 1000))),
    CONSTRAINT "diaries_short_caption_check" CHECK ((("length"("short_caption") >= 1) AND ("length"("short_caption") <= 100)))
);


ALTER TABLE "public"."diaries" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."diary_generations" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "owner_id" "uuid" NOT NULL,
    "pet_id" "uuid" NOT NULL,
    "session_id" "uuid" NOT NULL,
    "seq" smallint NOT NULL,
    "photo_path" "text" NOT NULL,
    "keywords" "text" NOT NULL,
    "honorific_used" "text" NOT NULL,
    "species_used" "text" NOT NULL,
    "gender_used" "public"."pet_gender" NOT NULL,
    "regen_feedback" "text",
    "diary_text" "text" NOT NULL,
    "short_caption" "text" NOT NULL,
    "mood_tag" "public"."mood_tag" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "diary_generations_check" CHECK ((("seq" > 1) OR ("regen_feedback" IS NULL))),
    CONSTRAINT "diary_generations_diary_text_check" CHECK ((("length"("diary_text") >= 50) AND ("length"("diary_text") <= 1000))),
    CONSTRAINT "diary_generations_honorific_used_check" CHECK ((("length"(TRIM(BOTH FROM "honorific_used")) >= 1) AND ("length"(TRIM(BOTH FROM "honorific_used")) <= 20))),
    CONSTRAINT "diary_generations_keywords_check" CHECK ((("length"("keywords") >= 1) AND ("length"("keywords") <= 1000))),
    CONSTRAINT "diary_generations_regen_feedback_check" CHECK ((("regen_feedback" IS NULL) OR (("length"("regen_feedback") >= 1) AND ("length"("regen_feedback") <= 500)))),
    CONSTRAINT "diary_generations_seq_check" CHECK ((("seq" >= 1) AND ("seq" <= 4))),
    CONSTRAINT "diary_generations_short_caption_check" CHECK ((("length"("short_caption") >= 1) AND ("length"("short_caption") <= 100))),
    CONSTRAINT "diary_generations_species_used_check" CHECK ((("length"(TRIM(BOTH FROM "species_used")) >= 1) AND ("length"(TRIM(BOTH FROM "species_used")) <= 20)))
);


ALTER TABLE "public"."diary_generations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."pets" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "owner_id" "uuid" NOT NULL,
    "name" "text" NOT NULL,
    "species" "text" NOT NULL,
    "honorific" "text" NOT NULL,
    "gender" "public"."pet_gender" DEFAULT 'unknown'::"public"."pet_gender" NOT NULL,
    "deleted_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "pets_honorific_check" CHECK ((("length"(TRIM(BOTH FROM "honorific")) >= 1) AND ("length"(TRIM(BOTH FROM "honorific")) <= 20))),
    CONSTRAINT "pets_name_check" CHECK ((("length"(TRIM(BOTH FROM "name")) >= 1) AND ("length"(TRIM(BOTH FROM "name")) <= 20))),
    CONSTRAINT "pets_species_check" CHECK ((("length"(TRIM(BOTH FROM "species")) >= 1) AND ("length"(TRIM(BOTH FROM "species")) <= 20)))
);


ALTER TABLE "public"."pets" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."profiles" (
    "id" "uuid" NOT NULL,
    "display_name" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "profiles_display_name_check" CHECK ((("length"(TRIM(BOTH FROM "display_name")) >= 1) AND ("length"(TRIM(BOTH FROM "display_name")) <= 24)))
);


ALTER TABLE "public"."profiles" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."usage_quotas" (
    "owner_id" "uuid" NOT NULL,
    "quota_date" "date" DEFAULT (("now"() AT TIME ZONE 'Asia/Seoul'::"text"))::"date" NOT NULL,
    "generations_count" smallint NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "usage_quotas_generations_count_check" CHECK ((("generations_count" >= 0) AND ("generations_count" <= 5)))
);


ALTER TABLE "public"."usage_quotas" OWNER TO "postgres";


ALTER TABLE ONLY "public"."diaries"
    ADD CONSTRAINT "diaries_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."diaries"
    ADD CONSTRAINT "diaries_source_generation_id_key" UNIQUE ("source_generation_id");



ALTER TABLE ONLY "public"."diary_generations"
    ADD CONSTRAINT "diary_generations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."diary_generations"
    ADD CONSTRAINT "diary_generations_session_id_seq_key" UNIQUE ("session_id", "seq");



ALTER TABLE ONLY "public"."pets"
    ADD CONSTRAINT "pets_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."usage_quotas"
    ADD CONSTRAINT "usage_quotas_pkey" PRIMARY KEY ("owner_id", "quota_date");



CREATE OR REPLACE TRIGGER "pets_set_updated_at" BEFORE UPDATE ON "public"."pets" FOR EACH ROW EXECUTE FUNCTION "private"."set_updated_at"();



CREATE OR REPLACE TRIGGER "profiles_set_updated_at" BEFORE UPDATE ON "public"."profiles" FOR EACH ROW EXECUTE FUNCTION "private"."set_updated_at"();



CREATE OR REPLACE TRIGGER "usage_quotas_insert_guard" BEFORE INSERT ON "public"."usage_quotas" FOR EACH ROW EXECUTE FUNCTION "private"."usage_quotas_insert_guard"();



CREATE OR REPLACE TRIGGER "usage_quotas_set_updated_at" BEFORE UPDATE ON "public"."usage_quotas" FOR EACH ROW EXECUTE FUNCTION "private"."set_updated_at"();



CREATE OR REPLACE TRIGGER "usage_quotas_update_guard" BEFORE UPDATE ON "public"."usage_quotas" FOR EACH ROW EXECUTE FUNCTION "private"."usage_quotas_update_guard"();



ALTER TABLE ONLY "public"."diaries"
    ADD CONSTRAINT "diaries_owner_id_fkey" FOREIGN KEY ("owner_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."diaries"
    ADD CONSTRAINT "diaries_pet_id_fkey" FOREIGN KEY ("pet_id") REFERENCES "public"."pets"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."diaries"
    ADD CONSTRAINT "diaries_source_generation_id_fkey" FOREIGN KEY ("source_generation_id") REFERENCES "public"."diary_generations"("id");



ALTER TABLE ONLY "public"."diary_generations"
    ADD CONSTRAINT "diary_generations_owner_id_fkey" FOREIGN KEY ("owner_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."diary_generations"
    ADD CONSTRAINT "diary_generations_pet_id_fkey" FOREIGN KEY ("pet_id") REFERENCES "public"."pets"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."pets"
    ADD CONSTRAINT "pets_owner_id_fkey" FOREIGN KEY ("owner_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_id_fkey" FOREIGN KEY ("id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."usage_quotas"
    ADD CONSTRAINT "usage_quotas_owner_id_fkey" FOREIGN KEY ("owner_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE "public"."diaries" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "diaries_delete_own" ON "public"."diaries" FOR DELETE TO "authenticated" USING ((( SELECT "auth"."uid"() AS "uid") = "owner_id"));



CREATE POLICY "diaries_insert_own" ON "public"."diaries" FOR INSERT TO "authenticated" WITH CHECK ((( SELECT "auth"."uid"() AS "uid") = "owner_id"));



CREATE POLICY "diaries_select_own" ON "public"."diaries" FOR SELECT TO "authenticated" USING ((( SELECT "auth"."uid"() AS "uid") = "owner_id"));



ALTER TABLE "public"."diary_generations" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "diary_generations_delete_own" ON "public"."diary_generations" FOR DELETE TO "authenticated" USING ((( SELECT "auth"."uid"() AS "uid") = "owner_id"));



CREATE POLICY "diary_generations_insert_own" ON "public"."diary_generations" FOR INSERT TO "authenticated" WITH CHECK ((( SELECT "auth"."uid"() AS "uid") = "owner_id"));



CREATE POLICY "diary_generations_select_own" ON "public"."diary_generations" FOR SELECT TO "authenticated" USING ((( SELECT "auth"."uid"() AS "uid") = "owner_id"));



ALTER TABLE "public"."pets" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "pets_insert_own" ON "public"."pets" FOR INSERT TO "authenticated" WITH CHECK ((( SELECT "auth"."uid"() AS "uid") = "owner_id"));



CREATE POLICY "pets_select_own_active" ON "public"."pets" FOR SELECT TO "authenticated" USING (((( SELECT "auth"."uid"() AS "uid") = "owner_id") AND ("deleted_at" IS NULL)));



CREATE POLICY "pets_update_own" ON "public"."pets" FOR UPDATE TO "authenticated" USING ((( SELECT "auth"."uid"() AS "uid") = "owner_id")) WITH CHECK ((( SELECT "auth"."uid"() AS "uid") = "owner_id"));



ALTER TABLE "public"."profiles" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "profiles_select_own" ON "public"."profiles" FOR SELECT TO "authenticated" USING ((( SELECT "auth"."uid"() AS "uid") = "id"));



CREATE POLICY "profiles_update_own" ON "public"."profiles" FOR UPDATE TO "authenticated" USING ((( SELECT "auth"."uid"() AS "uid") = "id")) WITH CHECK ((( SELECT "auth"."uid"() AS "uid") = "id"));



ALTER TABLE "public"."usage_quotas" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "usage_quotas_insert_own" ON "public"."usage_quotas" FOR INSERT TO "authenticated" WITH CHECK ((( SELECT "auth"."uid"() AS "uid") = "owner_id"));



CREATE POLICY "usage_quotas_select_own" ON "public"."usage_quotas" FOR SELECT TO "authenticated" USING ((( SELECT "auth"."uid"() AS "uid") = "owner_id"));



CREATE POLICY "usage_quotas_update_own" ON "public"."usage_quotas" FOR UPDATE TO "authenticated" USING ((( SELECT "auth"."uid"() AS "uid") = "owner_id")) WITH CHECK ((( SELECT "auth"."uid"() AS "uid") = "owner_id"));





ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";





GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";














































































































































































GRANT ALL ON TABLE "public"."diaries" TO "anon";
GRANT ALL ON TABLE "public"."diaries" TO "authenticated";
GRANT ALL ON TABLE "public"."diaries" TO "service_role";



GRANT ALL ON TABLE "public"."diary_generations" TO "anon";
GRANT ALL ON TABLE "public"."diary_generations" TO "authenticated";
GRANT ALL ON TABLE "public"."diary_generations" TO "service_role";



GRANT ALL ON TABLE "public"."pets" TO "anon";
GRANT ALL ON TABLE "public"."pets" TO "authenticated";
GRANT ALL ON TABLE "public"."pets" TO "service_role";



GRANT ALL ON TABLE "public"."profiles" TO "anon";
GRANT ALL ON TABLE "public"."profiles" TO "authenticated";
GRANT ALL ON TABLE "public"."profiles" TO "service_role";



GRANT ALL ON TABLE "public"."usage_quotas" TO "anon";
GRANT ALL ON TABLE "public"."usage_quotas" TO "authenticated";
GRANT ALL ON TABLE "public"."usage_quotas" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";































CREATE TRIGGER on_auth_user_created AFTER INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION private.handle_new_user();


  create policy "pet_photos_delete_own"
  on "storage"."objects"
  as permissive
  for delete
  to authenticated
using (((bucket_id = 'pet-photos'::text) AND ((storage.foldername(name))[1] = (( SELECT auth.uid() AS uid))::text)));



  create policy "pet_photos_insert_own"
  on "storage"."objects"
  as permissive
  for insert
  to authenticated
with check (((bucket_id = 'pet-photos'::text) AND ((storage.foldername(name))[1] = (( SELECT auth.uid() AS uid))::text)));



  create policy "pet_photos_select_own"
  on "storage"."objects"
  as permissive
  for select
  to authenticated
using (((bucket_id = 'pet-photos'::text) AND ((storage.foldername(name))[1] = (( SELECT auth.uid() AS uid))::text)));



  create policy "pet_photos_update_own"
  on "storage"."objects"
  as permissive
  for update
  to authenticated
using (((bucket_id = 'pet-photos'::text) AND ((storage.foldername(name))[1] = (( SELECT auth.uid() AS uid))::text)))
with check (((bucket_id = 'pet-photos'::text) AND ((storage.foldername(name))[1] = (( SELECT auth.uid() AS uid))::text)));



-- pet-photos bucket (storage data; supabase db pull은 schema만 dump하므로 명시 추가)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('pet-photos', 'pet-photos', false, 10485760, ARRAY['image/jpeg', 'image/png'])
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;


-- anon에 부여된 default privileges 회수 (정책: authenticated만 GRANT, anon은 RLS 추가 가드)
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.profiles FROM anon;
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.pets FROM anon;
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.diaries FROM anon;
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.diary_generations FROM anon;
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.usage_quotas FROM anon;



