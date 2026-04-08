"""
report.py — FastAPI Router: Report/Export endpoint.

TODO:
- GET /api/report/export → Xuất báo cáo tổng hợp dạng file Excel (.xlsx).
                            Gọi report_service.generate_report().
                            Trả về StreamingResponse với Content-Disposition header.
- Ref: docs/api_design.md mục 5.6.
"""
