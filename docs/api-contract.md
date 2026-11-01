# REST API Contract & Endpoint Specifications

**Project Name:** TestFlow — Integrated Electronics Testing, QA & Operations Management Platform  
**Document Version:** 1.0  
**API Protocol:** RESTful over HTTP/JSON  
**Base URL:** `/api/v1`  
**Interactive Docs:** Swagger UI at `/docs` | ReDoc at `/redoc`  

---

## 1. Global Conventions & Standards

* **Content-Type:** `application/json` (except file upload endpoints which consume `multipart/form-data`).
* **Authentication:** Stateless JWT bearer token supplied via `Authorization: Bearer <TOKEN>` header or HTTP-only secure cookie.
* **Standard Success Envelope:** Single entity responses return the object directly. Collections return `{ "items": [...], "total": int, "page": int, "size": int }`.
* **Standard Error Envelope:**
  ```json
  {
    "detail": {
      "code": "RESOURCE_NOT_FOUND",
      "message": "Batch item with serial 'TF-AX3000-0012' does not exist.",
      "timestamp": "2026-11-01T19:10:00Z"
    }
  }
  ```

---

## 2. API Endpoint Matrix by Domain

### 2.1 Authentication & HR Management

#### `POST /api/v1/auth/login`
* **Access:** Public
* **Payload:**
  ```json
  {
    "email": "technician1@testflow.local",
    "password": "SecurePassword123!"
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "user": {
      "id": 4,
      "emp_code": "EMP-204",
      "name": "Sarah Connor",
      "role": "TEST_TECHNICIAN",
      "department": "Testing Floor"
    }
  }
  ```

#### `GET /api/v1/auth/me`
* **Access:** Authenticated (Any role)
* **Response (200 OK):** Current logged-in user profile with permissions array.

#### `GET /api/v1/employees`
* **Access:** `SUPER_ADMIN`, `OPERATIONS_MGR`, `HR_OFFICER`
* **Query Params:** `department_id`, `role`, `status`, `page`, `size`
* **Response (200 OK):** Paginated list of employee records.

#### `POST /api/v1/attendance/punch`
* **Access:** Authenticated (Self check-in/out)
* **Payload:**
  ```json
  {
    "punch_type": "IN"
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "id": 182,
    "employee_id": 4,
    "date": "2026-11-01",
    "punch_in": "08:58:20",
    "status": "PRESENT"
  }
  ```

#### `POST /api/v1/attendance/upload-excel`
* **Access:** `SUPER_ADMIN`, `HR_OFFICER`
* **Content-Type:** `multipart/form-data`
* **Body:** `file: <biometric_export.xlsx>`
* **Response (200 OK):**
  ```json
  {
    "total_rows": 450,
    "imported_count": 448,
    "skipped_rows": 2,
    "errors": [
      { "row": 14, "reason": "Unknown EmpCode 'EMP-999'" }
    ]
  }
  ```

---

### 2.2 Client & Product Catalog

#### `GET /api/v1/clients`
* **Access:** Authenticated
* **Response (200 OK):** Array of active OEM client profiles.

#### `POST /api/v1/product-models`
* **Access:** `SUPER_ADMIN`, `OPERATIONS_MGR`
* **Payload:**
  ```json
  {
    "client_id": 2,
    "category": "ROUTER",
    "model_number": "RT-AX58U",
    "model_name": "Dual-Band Wi-Fi 6 Router",
    "specifications": {
      "wifi_standard": "Wi-Fi 6 (802.11ax)",
      "frequency_bands": ["2.4GHz", "5GHz"],
      "input_voltage": "12V DC, 1.5A"
    }
  }
  ```

---

### 2.3 Batches & Inventory

#### `POST /api/v1/batches`
* **Access:** `SUPER_ADMIN`, `STORE_KEEPER`, `OPERATIONS_MGR`
* **Payload:**
  ```json
  {
    "client_id": 2,
    "product_model_id": 5,
    "batch_number": "BAT-202611-RTR01",
    "inward_date": "2026-11-01",
    "challan_number": "CHAL-8921",
    "expected_qty": 200,
    "received_qty": 200,
    "storage_location": "Bay B-04"
  }
  ```

#### `POST /api/v1/batches/{batch_id}/serials/bulk-import`
* **Access:** `SUPER_ADMIN`, `STORE_KEEPER`
* **Payload:**
  ```json
  {
    "serial_numbers": [
      "SN-AX58U-00101",
      "SN-AX58U-00102",
      "SN-AX58U-00103"
    ]
  }
  ```
* **Response (201 Created):**
  ```json
  {
    "batch_id": 12,
    "registered_units": 3,
    "status": "RECEIVED"
  }
  ```

#### `POST /api/v1/batches/{batch_id}/serials/auto-generate`
* **Access:** `SUPER_ADMIN`, `STORE_KEEPER`
* **Payload:**
  ```json
  {
    "prefix": "TF-RTR",
    "count": 200
  }
  ```
* **Response (201 Created):** Generates `TF-RTR-0001` through `TF-RTR-0200` with QR codes.

---

### 2.4 Test Templates & Test Execution

#### `POST /api/v1/test-templates`
* **Access:** `SUPER_ADMIN`, `TEST_SUPERVISOR`
* **Payload:**
  ```json
  {
    "product_model_id": 5,
    "name": "Wi-Fi Router RF & Ping Baseline",
    "parameters": [
      {
        "parameter_name": "Power Consumption",
        "data_type": "NUMERIC_RANGE",
        "min_limit": 6.0,
        "max_limit": 12.0,
        "unit_of_measure": "W",
        "is_mandatory": true,
        "display_order": 1
      },
      {
        "parameter_name": "Ethernet Ping Latency",
        "data_type": "NUMERIC_RANGE",
        "min_limit": 0.1,
        "max_limit": 10.0,
        "unit_of_measure": "ms",
        "is_mandatory": true,
        "display_order": 2
      },
      {
        "parameter_name": "WPS LED Functional",
        "data_type": "BOOLEAN",
        "is_mandatory": true,
        "display_order": 3
      }
    ]
  }
  ```

#### `POST /api/v1/test-sessions/manual`
* **Access:** `SUPER_ADMIN`, `TEST_TECHNICIAN`
* **Payload:**
  ```json
  {
    "batch_item_id": 84,
    "template_id": 3,
    "results": [
      { "parameter_id": 10, "measured_value": "8.4" },
      { "parameter_id": 11, "measured_value": "2.1" },
      { "parameter_id": 12, "measured_value": "true" }
    ],
    "remarks": "All ports functional"
  }
  ```
* **Response (201 Created):**
  ```json
  {
    "session_id": 1052,
    "batch_item_id": 84,
    "overall_result": "PASS",
    "updated_item_status": "PASSED"
  }
  ```

#### `POST /api/v1/test-sessions/upload-csv`
* **Access:** `SUPER_ADMIN`, `TEST_TECHNICIAN`
* **Content-Type:** `multipart/form-data`
* **Body:**
  * `template_id: 3`
  * `file: <automated_bench_dump.csv>`
* **Response (200 OK):**
  ```json
  {
    "processed_serials": 50,
    "passed": 48,
    "failed": 2,
    "failed_items": [
      { "serial_number": "SN-AX58U-00142", "reason": "Power Consumption: 14.2W > Max 12.0W" }
    ]
  }
  ```

---

### 2.5 Quality Assurance & Defect Management

#### `POST /api/v1/qa/disposition`
* **Access:** `SUPER_ADMIN`, `QA_INSPECTOR`
* **Payload:**
  ```json
  {
    "batch_item_id": 84,
    "decision": "APPROVED",
    "remarks": "Spot-checked throughput and physical labels. Ready for dispatch."
  }
  ```
* **Response (200 OK):** Unit state transitioned to `QA_APPROVED`.

#### `POST /api/v1/defects`
* **Access:** `SUPER_ADMIN`, `TEST_TECHNICIAN`, `QA_INSPECTOR`
* **Payload:**
  ```json
  {
    "batch_item_id": 85,
    "defect_code": "DEF-RF-02",
    "severity": "MAJOR",
    "description": "5GHz receiver sensitivity down by 15dBm"
  }
  ```

---

### 2.6 Outbound Dispatch & Traceability

#### `POST /api/v1/dispatch-orders`
* **Access:** `SUPER_ADMIN`, `STORE_KEEPER`, `OPERATIONS_MGR`
* **Payload:**
  ```json
  {
    "client_id": 2,
    "dispatch_date": "2026-11-02",
    "carrier_name": "SafeExpress Cargo",
    "vehicle_number": "DL-1AA-1234",
    "unit_serial_numbers": [
      "SN-AX58U-00101",
      "SN-AX58U-00102"
    ]
  }
  ```
* **Validation Rule:** System rejects with `400 Bad Request` if any included serial is not in `QA_APPROVED` status.

#### `GET /api/v1/traceability/{serial_number}`
* **Access:** Authenticated
* **Response (200 OK):**
  ```json
  {
    "serial_number": "SN-AX58U-00101",
    "product": {
      "model_number": "RT-AX58U",
      "model_name": "Dual-Band Wi-Fi 6 Router",
      "client": "Telco Alpha Corp"
    },
    "inward": {
      "batch_number": "BAT-202611-RTR01",
      "inward_date": "2026-11-01",
      "challan_number": "CHAL-8921"
    },
    "testing_history": [
      {
        "session_id": 1052,
        "technician": "Sarah Connor (EMP-204)",
        "timestamp": "2026-11-01T14:22:10Z",
        "result": "PASS",
        "parameters": [
          { "parameter": "Power Consumption", "measured": "8.4 W", "result": "PASS" },
          { "parameter": "Ethernet Ping", "measured": "2.1 ms", "result": "PASS" }
        ]
      }
    ],
    "qa_signoff": {
      "inspector": "Marcus Wright (EMP-112)",
      "decision": "APPROVED",
      "timestamp": "2026-11-01T16:05:00Z"
    },
    "dispatch": {
      "challan_number": "DISP-202611-004",
      "dispatch_date": "2026-11-02",
      "carrier": "SafeExpress Cargo"
    }
  }
  ```

---

### 2.7 Dashboards & Analytics

#### `GET /api/v1/dashboard/metrics`
* **Access:** Authenticated
* **Response (200 OK):**
  ```json
  {
    "today_inward_count": 450,
    "today_tested_count": 380,
    "today_first_pass_yield": 94.7,
    "active_batches_in_progress": 4,
    "present_technicians_count": 8,
    "top_defects": [
      { "code": "DEF-RF-02", "label": "Low RF Power", "count": 12 },
      { "code": "DEF-PWR-01", "label": "No Power / LED Dead", "count": 5 }
    ]
  }
  ```

