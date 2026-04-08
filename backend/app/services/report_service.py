"""
report_service.py — Business Logic: Report/Export.

TODO:
- generate_report(db) → Tổng hợp dữ liệu từ cafe_scores,
  tạo file Excel (.xlsx) bằng openpyxl.
  Columns: cafe_id, name, total_visits, avg_duration, dropoff_rate,
  behavior_score, has_enough_data.
- Trả về bytes hoặc file path để router stream về client.
- Header: Content-Disposition: attachment; filename="studycafe_report.xlsx"
- Ref: docs/api_design.md mục 5.6.
"""
