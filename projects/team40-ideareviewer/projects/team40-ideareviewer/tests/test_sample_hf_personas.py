import unittest
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from scripts.sample_hf_personas import (
    DEFAULT_SHUFFLE_BUFFER_SIZE,
    age_group,
    collect_pool,
    enrich_row,
    has_digital_signal,
    is_quality_row,
    iter_dataset_server_rows,
    load_hf_rows,
    occupation_group,
    review_axes,
    select_with_quotas,
    summarize_rows,
)


def _row(
    uuid: str,
    *,
    age: int = 67,
    sex: str = "남자",
    occupation: str = "사무 종사자",
    province: str = "서울",
    family_type: str = "배우자와 거주",
    education_level: str = "대학교",
    persona: str | None = None,
) -> dict:
    base_text = (
        "스마트폰 앱과 유튜브를 가끔 사용하지만 새로운 결제 절차는 조심스럽게 확인합니다. "
        "가족과 함께 생활하며 가격 부담, 개인정보, 고객지원, 건강과 안전을 중요하게 봅니다. "
        "동네 생활권 안에서 시간을 아끼는 서비스를 선호하고 복잡한 가입 과정에는 쉽게 피로를 느낍니다."
    )
    return {
        "uuid": uuid,
        "persona": persona or f"{uuid} 님은 일상 속 불편을 구체적으로 말하는 사용자입니다. {base_text}",
        "cultural_background": base_text,
        "skills_and_expertise": base_text,
        "hobbies_and_interests": base_text,
        "career_goals_and_ambitions": base_text,
        "sex": sex,
        "age": age,
        "occupation": occupation,
        "province": province,
        "family_type": family_type,
        "education_level": education_level,
    }


class SampleHfPersonasTests(unittest.TestCase):
    def test_default_shuffle_buffer_is_small_enough_for_fast_streaming_startup(self) -> None:
        self.assertEqual(DEFAULT_SHUFFLE_BUFFER_SIZE, 100)

    def test_age_group_maps_review_panel_buckets(self) -> None:
        self.assertEqual(age_group(24), "20s")
        self.assertEqual(age_group(39), "30s")
        self.assertEqual(age_group(48), "40s")
        self.assertEqual(age_group(56), "50s")
        self.assertEqual(age_group(69), "60s")
        self.assertEqual(age_group(84), "70plus")
        self.assertIsNone(age_group(17))

    def test_quality_row_requires_core_metadata_and_rich_text(self) -> None:
        self.assertTrue(is_quality_row(_row("a")))
        self.assertFalse(is_quality_row(_row("b", persona="짧음")))

        missing = _row("c")
        missing["province"] = None
        self.assertFalse(is_quality_row(missing))

    def test_derived_tags_detect_digital_and_review_axes(self) -> None:
        row = _row("a", occupation="농업 숙련 종사자")

        self.assertEqual(occupation_group(row["occupation"]), "agriculture")
        self.assertTrue(has_digital_signal(row))
        self.assertEqual(
            review_axes(row),
            [
                "accessibility",
                "price_sensitivity",
                "trust_safety",
                "privacy_security",
                "time_saving",
                "family_care",
                "local_life",
                "health_safety",
                "complexity_resistance",
                "customer_support",
            ],
        )

    def test_enrich_row_adds_selection_metadata_without_losing_raw_fields(self) -> None:
        enriched = enrich_row(_row("a", age=72, occupation="요양 보호사", province="강원"))

        self.assertEqual(enriched["uuid"], "a")
        self.assertEqual(enriched["_selection"]["age_group"], "70plus")
        self.assertEqual(enriched["_selection"]["occupation_group"], "care_health")
        self.assertEqual(enriched["_selection"]["province"], "강원")

    def test_select_with_quotas_deduplicates_and_satisfies_both_quotas(self) -> None:
        rows = [
            enrich_row(_row("old-a", age=71, province="서울", occupation="사무 종사자")),
            enrich_row(_row("old-a", age=71, province="서울", occupation="사무 종사자")),
            enrich_row(_row("old-b", age=78, province="부산", occupation="농업 종사자")),
            enrich_row(_row("young-a", age=28, province="제주", occupation="범용 소프트웨어 프로그래머")),
        ]

        selected = select_with_quotas(
            rows,
            age_quotas={"70plus": 2, "20s": 1},
            occ_quotas={"office": 1, "agriculture": 1, "professional": 1},
        )

        self.assertEqual(sorted(row["uuid"] for row in selected), ["old-a", "old-b", "young-a"])
        self.assertEqual(len({row["uuid"] for row in selected}), 3)

    def test_select_with_quotas_spills_supply_shortfall_to_other_groups(self) -> None:
        rows = [
            enrich_row(_row(f"office-{i}", age=40 + i, occupation="사무 종사자")) for i in range(5)
        ] + [
            enrich_row(_row("agri-1", age=64, occupation="농업 종사자")),
        ]

        selected = select_with_quotas(
            rows,
            age_quotas={"40s": 2, "50s": 2, "60s": 2},
            occ_quotas={"office": 4, "agriculture": 2},
        )

        occ_counts: dict[str, int] = {}
        for row in selected:
            g = row["_selection"]["occupation_group"]
            occ_counts[g] = occ_counts.get(g, 0) + 1
        self.assertEqual(len(selected), 6)
        self.assertEqual(occ_counts.get("agriculture", 0), 1)
        self.assertEqual(occ_counts.get("office", 0), 5)

    def test_select_with_quotas_excludes_other_bucket_from_strict_quota(self) -> None:
        rows = [
            enrich_row(_row(f"office-{i}", age=40 + i, occupation="사무 종사자")) for i in range(3)
        ] + [
            enrich_row(_row(f"other-{i}", age=40 + i, occupation="외계어 미분류 직종"))
            for i in range(3)
        ]

        selected = select_with_quotas(
            rows,
            age_quotas={"40s": 3},
            occ_quotas={"office": 3},
        )

        self.assertEqual(len(selected), 3)
        self.assertTrue(all(row["_selection"]["occupation_group"] == "office" for row in selected))

    def test_collect_pool_respects_start_row_and_source_window_size(self) -> None:
        source_rows = [
            _row("skip-0", age=24),
            _row("take-1", age=34),
            _row("take-2", age=44),
            _row("skip-3", age=54),
        ]

        pool = collect_pool(
            source_rows,
            pool_size=10,
            start_row=1,
            source_window_size=2,
        )

        self.assertEqual([row["uuid"] for row in pool], ["take-1", "take-2"])

    def test_summarize_rows_counts_core_distributions(self) -> None:
        rows = [
            enrich_row(_row("a", age=27, sex="여자", province="서울", occupation="학생")),
            enrich_row(_row("b", age=67, sex="남자", province="충청남", occupation="농업 종사자")),
        ]

        summary = summarize_rows(rows)

        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["age_groups"], {"20s": 1, "60s": 1})
        self.assertEqual(summary["sex"], {"남자": 1, "여자": 1})
        self.assertEqual(summary["provinces"], {"서울": 1, "충청남": 1})
        self.assertEqual(summary["occupation_groups"], {"agriculture": 1, "student": 1})

    def test_load_hf_rows_uses_configurable_shuffle_buffer(self) -> None:
        class FakeDataset:
            def __init__(self) -> None:
                self.shuffle_call = None

            def shuffle(self, *, seed: int, buffer_size: int):
                self.shuffle_call = {"seed": seed, "buffer_size": buffer_size}
                return self

        fake_dataset = FakeDataset()
        calls = []

        def fake_loader(path: str, *, split: str, streaming: bool):
            calls.append({"path": path, "split": split, "streaming": streaming})
            return fake_dataset

        loaded = load_hf_rows(seed=7, shuffle_buffer_size=123, loader=fake_loader)

        self.assertIs(loaded, fake_dataset)
        self.assertEqual(calls[0]["path"], "nvidia/Nemotron-Personas-Korea")
        self.assertEqual(fake_dataset.shuffle_call, {"seed": 7, "buffer_size": 123})

    def test_iter_dataset_server_rows_fetches_offset_batches(self) -> None:
        calls = []
        sleeps = []

        class FakeResponse:
            def __init__(self, payload: bytes) -> None:
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _tb) -> None:
                return None

            def read(self) -> bytes:
                return self.payload

        def fake_opener(url: str, *, timeout: int):
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            offset = int(query["offset"][0])
            length = int(query["length"][0])
            calls.append({"offset": offset, "length": length, "timeout": timeout})
            rows = [
                {"row_idx": offset + index, "row": _row(f"row-{offset + index}")}
                for index in range(length)
            ]
            payload = {
                "features": [],
                "rows": rows,
                "num_rows_total": 1_000_000,
                "num_rows_per_page": 100,
                "partial": False,
            }
            import json

            return FakeResponse(json.dumps(payload).encode("utf-8"))

        rows = list(
            iter_dataset_server_rows(
                start_row=20_000,
                source_window_size=205,
                batch_size=100,
                opener=fake_opener,
                sleeper=sleeps.append,
                batch_delay_seconds=0,
            )
        )

        self.assertEqual(len(rows), 205)
        self.assertEqual(rows[0]["uuid"], "row-20000")
        self.assertEqual(rows[-1]["uuid"], "row-20204")
        self.assertEqual(
            calls,
            [
                {"offset": 20_000, "length": 100, "timeout": 60},
                {"offset": 20_100, "length": 100, "timeout": 60},
                {"offset": 20_200, "length": 5, "timeout": 60},
            ],
        )
        self.assertEqual(sleeps, [])

    def test_iter_dataset_server_rows_retries_rate_limit_errors(self) -> None:
        calls = []
        sleeps = []

        class FakeResponse:
            def __init__(self, payload: bytes) -> None:
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _tb) -> None:
                return None

            def read(self) -> bytes:
                return self.payload

        def fake_opener(url: str, *, timeout: int):
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            offset = int(query["offset"][0])
            length = int(query["length"][0])
            calls.append({"offset": offset, "length": length, "timeout": timeout})
            if len(calls) == 1:
                raise HTTPError(url, 429, "Too Many Requests", hdrs=None, fp=None)

            rows = [
                {"row_idx": offset + index, "row": _row(f"row-{offset + index}")}
                for index in range(length)
            ]
            payload = {"features": [], "rows": rows}
            import json

            return FakeResponse(json.dumps(payload).encode("utf-8"))

        rows = list(
            iter_dataset_server_rows(
                start_row=20_000,
                source_window_size=2,
                batch_size=2,
                opener=fake_opener,
                sleeper=sleeps.append,
                retry_base_delay_seconds=0.25,
                batch_delay_seconds=0,
            )
        )

        self.assertEqual([row["uuid"] for row in rows], ["row-20000", "row-20001"])
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [0.25])

    def test_occupation_group_classifies_field_labor_extensions(self) -> None:
        self.assertEqual(occupation_group("건물 청소원"), "field_labor")
        self.assertEqual(occupation_group("건물 경비원"), "field_labor")
        self.assertEqual(occupation_group("시설 경비원"), "field_labor")
        self.assertEqual(occupation_group("전기 용접원"), "field_labor")
        self.assertEqual(occupation_group("강구조물 건립원"), "field_labor")
        self.assertEqual(occupation_group("수동 포장원"), "field_labor")
        self.assertEqual(occupation_group("그 외 물품 이동 장비 조작원"), "field_labor")

    def test_occupation_group_classifies_service_sales_extensions(self) -> None:
        self.assertEqual(occupation_group("전화 상담원"), "service_sales")
        self.assertEqual(occupation_group("일반 비서"), "service_sales")

    def test_occupation_group_classifies_professional_extensions(self) -> None:
        self.assertEqual(occupation_group("범용 소프트웨어 프로그래머"), "professional")
        self.assertEqual(occupation_group("경영 컨설턴트"), "professional")
        self.assertEqual(occupation_group("상품 기획자"), "professional")
        self.assertEqual(occupation_group("정보 시스템 운영자"), "professional")

    def test_occupation_group_classifies_self_employed_extensions(self) -> None:
        self.assertEqual(occupation_group("소규모 상점 경영자"), "self_employed")
        self.assertEqual(occupation_group("기업 고위 임원"), "self_employed")

    def test_occupation_group_priority_keeps_industry_safety_in_professional(self) -> None:
        self.assertEqual(occupation_group("산업 안전원"), "professional")

    def test_occupation_group_priority_keeps_office_assistant_in_office(self) -> None:
        self.assertEqual(occupation_group("사무 보조원"), "office")

    def test_age_group_weights_sum_to_one_hundred_and_flatten_seniors(self) -> None:
        from scripts.sample_hf_personas import AGE_GROUP_WEIGHTS
        self.assertEqual(sum(AGE_GROUP_WEIGHTS.values()), 100)
        self.assertEqual(AGE_GROUP_WEIGHTS["20s"], 17)
        self.assertEqual(AGE_GROUP_WEIGHTS["30s"], 17)
        self.assertEqual(AGE_GROUP_WEIGHTS["40s"], 17)
        self.assertEqual(AGE_GROUP_WEIGHTS["50s"], 17)
        self.assertEqual(AGE_GROUP_WEIGHTS["60s"], 16)
        self.assertEqual(AGE_GROUP_WEIGHTS["70plus"], 16)

    def test_make_quotas_scales_arbitrary_weights_to_target_total(self) -> None:
        from scripts.sample_hf_personas import AGE_GROUP_WEIGHTS, make_quotas
        quotas = make_quotas(100, AGE_GROUP_WEIGHTS)
        self.assertEqual(quotas, {
            "20s": 17, "30s": 17, "40s": 17, "50s": 17, "60s": 16, "70plus": 16,
        })
        half = make_quotas(50, AGE_GROUP_WEIGHTS)
        self.assertEqual(sum(half.values()), 50)

    def test_build_summary_includes_age_and_occupation_quotas(self) -> None:
        from scripts.sample_hf_personas import build_summary
        summary = build_summary(
            seed=1,
            source="file",
            start_row=0,
            source_window_size=None,
            batch_size=0,
            pool_size=10,
            candidate_size=10,
            selected_size=10,
            pool=[],
            candidates=[],
            selected=[],
            max_source_rows=None,
        )
        self.assertIn("age_quotas", summary)
        self.assertIn("occupation_quotas", summary)
        self.assertEqual(sum(summary["age_quotas"]["selected"].values()), 10)
        self.assertEqual(sum(summary["occupation_quotas"]["selected"].values()), 10)

    def test_occupation_group_weights_define_balanced_distribution(self) -> None:
        from scripts.sample_hf_personas import OCCUPATION_GROUP_WEIGHTS, make_quotas
        self.assertEqual(sum(OCCUPATION_GROUP_WEIGHTS.values()), 100)
        self.assertEqual(OCCUPATION_GROUP_WEIGHTS["office"], 13)
        self.assertEqual(OCCUPATION_GROUP_WEIGHTS["service_sales"], 12)
        self.assertEqual(OCCUPATION_GROUP_WEIGHTS["field_labor"], 12)
        self.assertEqual(OCCUPATION_GROUP_WEIGHTS["professional"], 11)
        self.assertEqual(OCCUPATION_GROUP_WEIGHTS["retired_unemployed"], 10)
        self.assertEqual(OCCUPATION_GROUP_WEIGHTS["education"], 9)
        self.assertEqual(OCCUPATION_GROUP_WEIGHTS["care_health"], 8)
        self.assertEqual(OCCUPATION_GROUP_WEIGHTS["self_employed"], 8)
        self.assertEqual(OCCUPATION_GROUP_WEIGHTS["agriculture"], 6)
        self.assertEqual(OCCUPATION_GROUP_WEIGHTS["arts_media"], 6)
        self.assertEqual(OCCUPATION_GROUP_WEIGHTS["homemaker"], 5)
        quotas = make_quotas(100, OCCUPATION_GROUP_WEIGHTS)
        self.assertEqual(quotas["office"], 13)
        self.assertEqual(sum(quotas.values()), 100)


if __name__ == "__main__":
    unittest.main()
