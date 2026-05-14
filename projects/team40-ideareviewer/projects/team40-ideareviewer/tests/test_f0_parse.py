import unittest

from nodes.f0_parse import _repair_brief
from schemas import ServicePlanInput


_RAW_DIRECT_TRADE = (
    "농촌 생산자와 도시 소비자를 직접 연결하는 농산물 직거래 앱입니다. "
    "생산자는 스마트폰으로 수확한 농산물 사진과 가격을 올리고, "
    "소비자는 원하는 농산물을 주문하면 산지에서 직접 배송받습니다. "
    "중간 유통 마진 없이 생산자는 더 많이 받고, 소비자는 더 싸게 살 수 있습니다. "
    "동네 시장 상인도 소량 등록이 가능합니다."
)


class ParseRepairTests(unittest.TestCase):
    def test_repair_brief_fills_missing_target_and_features_from_raw_text(self) -> None:
        parsed = ServicePlanInput(
            raw_text=_RAW_DIRECT_TRADE,
            title="농-소 직거래 플랫폼 앱",
            description="농산물 직거래 서비스",
            target=None,
            key_features=[],
            concerns=None,
        )

        repaired = _repair_brief(parsed, _RAW_DIRECT_TRADE)

        self.assertIn("생산자", repaired.target or "")
        self.assertIn("소비자", repaired.target or "")
        self.assertTrue(any("사진" in feature and "가격" in feature for feature in repaired.key_features))
        self.assertTrue(any("배송" in feature for feature in repaired.key_features))
        self.assertTrue(any("소량 등록" in feature for feature in repaired.key_features))

    def test_repair_brief_extracts_generic_targets_and_features(self) -> None:
        raw = (
            "고령 환자와 보호자를 위한 병원 예약 서비스입니다. "
            "환자는 병원 예약 시간을 확인하고, 복약 알림을 받고, 보호자에게 일정을 공유합니다."
        )
        parsed = ServicePlanInput(
            raw_text=raw,
            title="병원 예약 서비스",
            description=None,
            target=None,
            key_features=[],
            concerns=None,
        )

        repaired = _repair_brief(parsed, raw)

        self.assertIn("고령 환자", repaired.target or "")
        self.assertIn("보호자", repaired.target or "")
        self.assertTrue(any("예약" in feature for feature in repaired.key_features))
        self.assertTrue(any("복약" in feature and "알림" in feature for feature in repaired.key_features))
        self.assertTrue(any("공유" in feature for feature in repaired.key_features))


if __name__ == "__main__":
    unittest.main()
