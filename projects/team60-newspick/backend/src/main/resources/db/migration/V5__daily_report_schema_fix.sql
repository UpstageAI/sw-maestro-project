-- daily_reports 스키마 정합성 수정
--
-- 기존 로컬 DB에는 V2가 summary 정규화로 이미 적용된 상태가 있을 수 있어
-- 리포트 스키마 보정은 새 버전에서 idempotent하게 처리한다.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'daily_reports'
          AND column_name = 'sub_articles'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'daily_reports'
          AND column_name = 'timeline'
    ) THEN
        ALTER TABLE daily_reports RENAME COLUMN sub_articles TO timeline;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'daily_reports'
          AND column_name = 'timeline'
    ) THEN
        ALTER TABLE daily_reports
            ADD COLUMN timeline jsonb NOT NULL DEFAULT '[]'::jsonb;
    END IF;
END $$;

DO $$
DECLARE
    briefing_type text;
    has_headline boolean;
BEGIN
    SELECT udt_name
    INTO briefing_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'daily_reports'
      AND column_name = 'briefing';

    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'daily_reports'
          AND column_name = 'headline'
    )
    INTO has_headline;

    IF briefing_type IS NULL THEN
        ALTER TABLE daily_reports
            ADD COLUMN briefing jsonb NOT NULL DEFAULT '{"headline":"","summary":""}'::jsonb;
    ELSIF briefing_type <> 'jsonb' THEN
        ALTER TABLE daily_reports ADD COLUMN briefing_json jsonb;

        IF has_headline THEN
            UPDATE daily_reports
            SET briefing_json = jsonb_build_object(
                'headline', COALESCE(headline #>> '{}', ''),
                'summary', COALESCE(briefing, '')
            );
        ELSE
            UPDATE daily_reports
            SET briefing_json = jsonb_build_object(
                'headline', '',
                'summary', COALESCE(briefing, '')
            );
        END IF;

        UPDATE daily_reports
        SET briefing_json = '{"headline":"","summary":""}'::jsonb
        WHERE briefing_json IS NULL;

        ALTER TABLE daily_reports ALTER COLUMN briefing_json SET NOT NULL;
        ALTER TABLE daily_reports DROP COLUMN briefing;
        ALTER TABLE daily_reports RENAME COLUMN briefing_json TO briefing;
    END IF;

    IF has_headline THEN
        ALTER TABLE daily_reports DROP COLUMN headline;
    END IF;
END $$;
