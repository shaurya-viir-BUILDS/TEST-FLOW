import io
from datetime import date
import openpyxl


def test_excel_attendance_upload_success(client, hr_headers):
    # Dynamically build a sample biometric export workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "BiometricPunchLog"

    # Write headers with aliases
    ws.append(["Staff ID", "Punch Date", "In Time", "Out Time", "Status"])

    # Row 1: Valid Employee EMP-TEST-01
    ws.append(["EMP-TEST-01", "2026-11-01", "08:55:00", "17:30:00", "Present"])
    # Row 2: Valid Employee EMP-TEST-02
    ws.append(["EMP-TEST-02", "2026-11-01", "09:02:15", "18:00:00", "Present"])
    # Row 3: Unknown Employee
    ws.append(["EMP-GHOST-99", "2026-11-01", "09:10:00", "17:00:00", "Present"])

    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    response = client.post(
        "/api/v1/attendance/upload-excel",
        headers=hr_headers,
        files={"file": ("biometric_november.xlsx", file_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 3
    assert data["imported_count"] == 2
    assert data["skipped_rows"] == 1
    assert len(data["errors"]) == 1
    assert "EMP-GHOST-99" in data["errors"][0]["emp_code"]
    assert "not found in database" in data["errors"][0]["reason"]


def test_excel_upload_rejected_for_technician(client, tech_headers):
    wb = openpyxl.Workbook()
    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    response = client.post(
        "/api/v1/attendance/upload-excel",
        headers=tech_headers,
        files={"file": ("biometric.xlsx", file_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert response.status_code == 403

