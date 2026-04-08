"""
mock_data.py — Sinh mock data để test pipeline.

TODO:
- import_mock_data(db, source) → Tạo sessions + GPS logs giả lập.
  Trả về số sessions và logs đã import.
- Mock data bao gồm:
  - Vài quán cafe mẫu với tọa độ Hà Nội/HCM.
  - 20-30 sessions với GPS logs phân bố hợp lý.
  - Một số session "đang học" (stable) và "rời sớm" (dropoff).
- Ref: docs/api_design.md mục 5.7.
"""
