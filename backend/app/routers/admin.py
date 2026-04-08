"""
admin.py — FastAPI Router: Admin/Internal endpoints.

TODO:
- POST /api/mock-data/import              → Nạp mock data để test pipeline.
                                             Gọi mock_data service.
- POST /api/admin/cafes/{cafe_id}/approve  → [Optional] Admin duyệt quán pending.
- Endpoints nội bộ, không expose cho end-user.
- Ref: docs/api_design.md mục 5.7, 5.10.
"""
