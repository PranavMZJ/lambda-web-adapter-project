# Design Document: lambda-web-adapter-migration-test

## Overview

This project demonstrates that **aws-lambda-web-adapter** enables a standard Flask web application to run on AWS Lambda without any application code changes. Two Lambda deployments are compared side-by-side:

- **Test 1 (no-adapter)**: The Flask app is deployed as-is. Lambda cannot find a handler function, so invocations fail with `Runtime.HandlerNotFound`.
- **Test 2 (with-adapter)**: The same zip package is deployed with the aws-lambda-web-adapter Lambda Layer attached. The adapter intercepts Lambda invocations, starts the Flask HTTP server, and proxies requests — all without touching application code.

A Python test runner sends identical HTTP requests to both API Gateway endpoints, records the results, and a report generator produces bilingual Markdown comparison reports (`report.md` in Japanese, `report_en.md` in English).

### Key Design Principle

The entire point of the project is to prove zero application code changes are needed. Therefore, the **same deployment zip** is used for both Lambda functions. The only difference between Test 1 and Test 2 is Terraform configuration (layer attachment and environment variables).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Local Development                                              │
│  Flask app (port 8000) ──► DynamoDB (AWS, ap-northeast-1)      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  AWS (ap-northeast-1)                                           │
│                                                                 │
│  API Gateway (HTTP API)                                         │
│    ├── /test1/{proxy+} ──► Lambda: no-adapter                  │
│    │                         (Flask zip, no layer)             │
│    │                         └──► DynamoDB table               │
│    │                                                            │
│    └── /test2/{proxy+} ──► Lambda: with-adapter                │
│                              (same Flask zip + LWA layer)      │
│                              └──► DynamoDB table               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Local Scripts                                                  │
│  test_runner.py ──► API Gateway endpoints ──► results.json     │
│  report_generator.py ──► results.json ──► report.md            │
│                                         └──► report_en.md      │
└─────────────────────────────────────────────────────────────────┘
```

### How aws-lambda-web-adapter Works

When the Lambda Layer is attached and `AWS_LAMBDA_EXEC_WRAPPER=/opt/bootstrap` is set:

1. Lambda's runtime calls `/opt/bootstrap` (the wrapper script from the layer) instead of the handler directly.
2. The wrapper starts the **Lambda Web Adapter** binary as a Lambda Extension.
3. The adapter starts the application using the function handler string as a shell command (e.g., `run.sh`).
4. The adapter performs a readiness check by polling `GET /` until the app responds.
5. On each Lambda invocation, the adapter translates the API Gateway event into an HTTP request, forwards it to `localhost:$PORT`, and translates the HTTP response back into a Lambda response.

Without the layer, Lambda tries to import the handler module and call `lambda_handler(event, context)`. Since the Flask app has no such function, Lambda returns `Runtime.HandlerNotFound`.

---

## Components and Interfaces

### 1. Flask Application (`app/`)

The Flask app is a self-contained HTTP server with no Lambda-specific code.

```
app/
├── app.py          # Flask application, routes, DynamoDB logic
├── run.sh          # Startup script (used as Lambda handler string)
└── requirements.txt
```

**`app.py` interface:**

| Route | Method | Request | Response |
|---|---|---|---|
| `/` | GET | — | `{"status": "ok"}`, HTTP 200 |
| `/items` | GET | — | `[{item}, ...]`, HTTP 200 |
| `/items` | POST | `{"name": str, ...}` | `{item}`, HTTP 201 |
| `/items/<id>` | GET | — | `{item}`, HTTP 200 or HTTP 404 |

The app reads `DYNAMODB_TABLE_NAME` from the environment. It uses `boto3` to interact with DynamoDB. No `lambda_handler` function is defined anywhere in the application code.

**`run.sh`** is the Lambda handler string. It starts gunicorn:

```bash
#!/bin/bash
PATH=$PATH:$LAMBDA_TASK_ROOT/bin \
    PYTHONPATH=$PYTHONPATH:/opt/python:$LAMBDA_RUNTIME_DIR \
    exec python -m gunicorn -b=:$PORT -w=1 app:app
```

This script is only executed when the adapter is present. In Test 1, the handler string `run.sh` causes `Runtime.HandlerNotFound` because Lambda tries to import it as a Python module.

### 2. Terraform Infrastructure (`terraform/`)

```
terraform/
├── main.tf             # Root module: calls all child modules
├── variables.tf        # Input variables (profile, region, tags)
├── outputs.tf          # API Gateway URLs, Lambda ARNs
├── terraform.tfvars    # Variable values (not committed)
└── modules/
    ├── dynamodb/       # DynamoDB table
    ├── iam/            # Lambda execution role (shared)
    ├── lambda-no-adapter/    # Test 1 Lambda + packaging
    ├── lambda-with-adapter/  # Test 2 Lambda + layer
    └── api-gateway/    # HTTP API + routes + integrations
```

**Module responsibilities:**

| Module | Resources |
|---|---|
| `dynamodb` | `aws_dynamodb_table` |
| `iam` | `aws_iam_role`, `aws_iam_role_policy_attachment` |
| `lambda-no-adapter` | `aws_lambda_function` (no layer), `aws_lambda_permission` |
| `lambda-with-adapter` | `aws_lambda_function` (with LWA layer), `aws_lambda_permission` |
| `api-gateway` | `aws_apigatewayv2_api`, routes, integrations, stage |

### 3. Test Runner (`scripts/test_runner.py`)

Reads endpoint URLs from a config file or environment variables, sends the same HTTP requests to both endpoints, and writes results to `results/results.json`.

**Input:** `config.json` or environment variables `TEST1_URL`, `TEST2_URL`

**Output:** `results/results.json`

```json
{
  "timestamp": "2025-01-01T00:00:00Z",
  "test1": {
    "base_url": "https://...",
    "results": [
      {
        "endpoint": "GET /",
        "status_code": null,
        "response_body": null,
        "error": "Runtime.HandlerNotFound: ..."
      }
    ]
  },
  "test2": {
    "base_url": "https://...",
    "results": [
      {
        "endpoint": "GET /",
        "status_code": 200,
        "response_body": {"status": "ok"},
        "error": null
      }
    ]
  }
}
```

### 4. Report Generator (`scripts/report_generator.py`)

Reads `results/results.json` and produces `report.md` (Japanese) and `report_en.md` (English).

**Input:** `results/results.json`

**Output:** `report.md`, `report_en.md`

Both reports contain: Overview, Test 1 results, Test 2 results, side-by-side comparison table, and conclusion.

### 5. Kiro Steering Files (`.kiro/steering/`)

```
.kiro/steering/
├── naming-tagging.md       # MZJ-IAM naming and tagging rules
└── bilingual-docs.md       # Bilingual documentation rules
```

**`naming-tagging.md`** captures the MZJ-IAM conventions so Kiro applies them automatically when generating Terraform or resource names.

**`bilingual-docs.md`** captures the rule that all project `.md` files have a Japanese default and an `_en.md` English counterpart; `.kiro/` spec files are English only.

### 6. Kiro Hooks (`.kiro/hooks/`)

```
.kiro/hooks/
├── sync-bilingual-docs.json   # Auto-sync _en.md when .md is edited
└── post-task-test.json        # Run test_runner.py after deploy tasks
```

**`sync-bilingual-docs.json`**: Triggers on `fileEdited` for `*.md` files (excluding `_en.md` and `.kiro/**`). Asks the agent to update the corresponding `_en.md` file to reflect the same content in English.

**`post-task-test.json`**: Triggers on `postTaskExecution`. Runs `scripts/test_runner.py` after deployment tasks complete.

---

## Data Models

### DynamoDB Item

Table name: `Pranav-lambda-web-adapter-migration-test-items`

| Attribute | Type | Description |
|---|---|---|
| `id` | String (PK) | UUID v4, generated on creation |
| `name` | String | Item name (required) |
| `created_at` | String | ISO 8601 timestamp |

Billing mode: PAY_PER_REQUEST (no capacity planning needed for a demo project).

### Test Result Record

```python
@dataclass
class TestResult:
    endpoint: str          # e.g. "GET /"
    status_code: int | None
    response_body: Any     # parsed JSON or raw string
    error: str | None      # error message if request failed
```

### Test Run Output

```python
@dataclass
class TestRun:
    base_url: str
    results: list[TestResult]

@dataclass
class TestOutput:
    timestamp: str         # ISO 8601
    test1: TestRun
    test2: TestRun
```

---

## Packaging Strategy

The same zip file is used for both Lambda functions. This is the core proof that no code changes are needed.

```
deployment.zip
├── app.py
├── run.sh          (chmod +x)
└── (dependencies installed into zip root via pip install -t .)
```

**Build process** (`scripts/build.sh`):

```bash
#!/bin/bash
set -e
BUILD_DIR=$(mktemp -d)
cp app/app.py app/run.sh app/requirements.txt "$BUILD_DIR/"
pip install -r app/requirements.txt -t "$BUILD_DIR/" --quiet
chmod +x "$BUILD_DIR/run.sh"
cd "$BUILD_DIR"
zip -r "$OLDPWD/deployment.zip" .
rm -rf "$BUILD_DIR"
echo "Built deployment.zip"
```

Terraform uses a `null_resource` with a `local-exec` provisioner (or a `data "archive_file"`) to build the zip before deploying. Both Lambda modules reference the same `deployment.zip` path.

**Lambda handler string:** `run.sh`

- **Test 1**: Lambda tries to import `run.sh` as a Python module → `Runtime.HandlerNotFound`
- **Test 2**: The adapter wrapper intercepts execution, runs `run.sh` as a shell script → gunicorn starts on `$PORT`

---

## Terraform Module Structure

### Root `main.tf`

```hcl
provider "aws" {
  region  = var.region          # "ap-northeast-1"
  profile = var.aws_profile     # "terraform"
}

locals {
  common_tags = {
    User    = "Pranav"
    Project = "lambda-web-adapter-migration-test"
  }
  name_prefix = "Pranav-lambda-web-adapter-migration-test"
}

module "dynamodb" {
  source      = "./modules/dynamodb"
  name_prefix = local.name_prefix
  tags        = local.common_tags
}

module "iam" {
  source             = "./modules/iam"
  name_prefix        = local.name_prefix
  tags               = local.common_tags
  permissions_boundary = "arn:aws:iam::681561127010:policy/MZJTeamBoundary"
}

module "lambda_no_adapter" {
  source         = "./modules/lambda-no-adapter"
  name_prefix    = local.name_prefix
  role_arn       = module.iam.lambda_role_arn
  dynamodb_table = module.dynamodb.table_name
  tags           = local.common_tags
}

module "lambda_with_adapter" {
  source         = "./modules/lambda-with-adapter"
  name_prefix    = local.name_prefix
  role_arn       = module.iam.lambda_role_arn
  dynamodb_table = module.dynamodb.table_name
  tags           = local.common_tags
}

module "api_gateway" {
  source                    = "./modules/api-gateway"
  name_prefix               = local.name_prefix
  lambda_no_adapter_arn     = module.lambda_no_adapter.function_arn
  lambda_with_adapter_arn   = module.lambda_with_adapter.function_arn
  tags                      = local.common_tags
}
```

### `modules/iam/`

Creates one shared Lambda execution role:

- Role name: `Pranav-lambda-web-adapter-migration-test-role`
- Trust policy: `lambda.amazonaws.com`
- Permissions boundary: `arn:aws:iam::681561127010:policy/MZJTeamBoundary`
- Attached policies: `AWSLambdaBasicExecutionRole`, inline policy for DynamoDB access

### `modules/lambda-no-adapter/`

```hcl
resource "aws_lambda_function" "no_adapter" {
  function_name = "${var.name_prefix}-no-adapter"
  filename      = "${path.root}/../deployment.zip"
  handler       = "run.sh"
  runtime       = "python3.12"
  role          = var.role_arn

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table
    }
  }

  tags = var.tags
}
```

No layers attached. Handler `run.sh` will cause `Runtime.HandlerNotFound`.

### `modules/lambda-with-adapter/`

```hcl
resource "aws_lambda_function" "with_adapter" {
  function_name = "${var.name_prefix}-with-adapter"
  filename      = "${path.root}/../deployment.zip"
  handler       = "run.sh"
  runtime       = "python3.12"
  role          = var.role_arn

  layers = [
    "arn:aws:lambda:ap-northeast-1:753240598075:layer:LambdaAdapterLayerX86:27"
  ]

  environment {
    variables = {
      DYNAMODB_TABLE_NAME      = var.dynamodb_table
      AWS_LAMBDA_EXEC_WRAPPER  = "/opt/bootstrap"
      PORT                     = "8000"
    }
  }

  tags = var.tags
}
```

### `modules/api-gateway/`

Creates an HTTP API with two route groups:

- `ANY /test1/{proxy+}` → Lambda integration → `no-adapter` function
- `ANY /test2/{proxy+}` → Lambda integration → `with-adapter` function

Uses `aws_apigatewayv2_api`, `aws_apigatewayv2_integration`, `aws_apigatewayv2_route`, and `aws_apigatewayv2_stage` (auto-deploy enabled).

---

## Project Directory Layout

```
lambda-web-adapter-migration-test/
├── app/
│   ├── app.py                  # Flask application (no Lambda code)
│   ├── run.sh                  # Startup script (Lambda handler string)
│   └── requirements.txt        # Flask, gunicorn, boto3
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── terraform.tfvars        # (gitignored)
│   └── modules/
│       ├── dynamodb/
│       ├── iam/
│       ├── lambda-no-adapter/
│       ├── lambda-with-adapter/
│       └── api-gateway/
├── scripts/
│   ├── build.sh                # Builds deployment.zip
│   ├── test_runner.py          # Sends requests, writes results.json
│   └── report_generator.py     # Reads results.json, writes reports
├── results/
│   └── results.json            # TestRunner output (gitignored)
├── deployment.zip              # Built artifact (gitignored)
├── config.json                 # API Gateway URLs (gitignored)
├── report.md                   # Japanese comparison report
├── report_en.md                # English comparison report
├── README.md                   # Japanese README
├── README_en.md                # English README
├── testing.md                  # Japanese testing guide
├── testing_en.md               # English testing guide
└── .kiro/
    └── specs/
        └── lambda-web-adapter-migration-test/
            ├── requirements.md
            ├── design.md
            └── tasks.md
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

This feature involves a mix of infrastructure (Terraform), application logic (Flask + DynamoDB), and data transformation (TestRunner, ReportGenerator). Property-based testing applies to the application logic and data transformation layers. Infrastructure checks use smoke tests and integration tests.

The property-based testing library used is **Hypothesis** (Python).

---

### Property 1: Item creation round-trip

*For any* valid item payload (non-empty name, arbitrary additional string fields), POSTing the item to `/items` and then GETting `/items/{id}` using the returned ID should return an item with the same field values as the original payload.

**Validates: Requirements 1.5**

---

### Property 2: Invalid payloads are rejected

*For any* HTTP request body that is not valid JSON, or is valid JSON but missing the required `name` field, or has `name` set to an empty/whitespace-only string, a `POST /items` request should return HTTP 400.

**Validates: Requirements 1.6**

---

### Property 3: Non-existent item returns 404

*For any* UUID that has not been inserted into the DynamoDB table, a `GET /items/{id}` request should return HTTP 404.

**Validates: Requirements 1.7**

---

### Property 4: TestRunner records all response fields

*For any* HTTP response (varying status code, body content, and presence/absence of error), the TestRunner's recording function should capture the status code, response body, and error message — none of these fields should be silently dropped.

**Validates: Requirements 2.7, 5.2**

---

### Property 5: TestRunner sends identical requests to both endpoints

*For any* configuration of test cases, the set of requests sent to the Test 1 endpoint and the set of requests sent to the Test 2 endpoint should be identical (same methods, paths, and bodies).

**Validates: Requirements 5.1**

---

### Property 6: Test results JSON round-trip

*For any* set of test results (varying numbers of test cases, status codes, response bodies, and errors), serializing the results to JSON and deserializing them should produce an equivalent data structure with no data loss.

**Validates: Requirements 5.4**

---

### Property 7: TestRunner continues on connection failure

*For any* connection failure type (timeout, connection refused, DNS resolution failure), the TestRunner should record the error for that test case and continue executing the remaining test cases without raising an unhandled exception.

**Validates: Requirements 5.5**

---

### Property 8: Report contains all required sections

*For any* valid `results.json` input (varying endpoint counts, status codes, and error messages), the ReportGenerator should produce both `report.md` and `report_en.md`, each containing all five required sections: Overview, Test 1 results, Test 2 results, comparison table, and conclusion.

**Validates: Requirements 6.1, 6.4**

---

### Property 9: Comparison table covers all tested endpoints

*For any* set of test results covering N distinct endpoints, the comparison table in the generated report should contain exactly N rows — one for each endpoint tested.

**Validates: Requirements 6.5**

---

### Property 10: Conclusion states code change status

*For any* test results input, the conclusion section of the generated report should contain exactly one of the two required statements: "No application code changes were required" or "Application code changes were required" — never both, never neither.

**Validates: Requirements 6.6**

---

### Property 11: All Terraform resources have required tags

*For any* Terraform resource block in the configuration, the `tags` attribute should include both `User = "Pranav"` and `Project = "lambda-web-adapter-migration-test"`.

**Validates: Requirements 4.2**

---

### Property 12: All IAM roles have MZJTeamBoundary

*For any* `aws_iam_role` resource block in the Terraform configuration, the `permissions_boundary` attribute should be set to `arn:aws:iam::681561127010:policy/MZJTeamBoundary`.

**Validates: Requirements 4.3**

---

**Property Reflection — Redundancy Check:**

- Properties 4 and 5 are distinct: Property 4 tests the recording function's completeness; Property 5 tests that both endpoints receive the same requests.
- Properties 8, 9, and 10 are distinct: Property 8 tests section presence; Property 9 tests table row count; Property 10 tests conclusion content.
- Properties 11 and 12 are distinct: Property 11 covers all resource types; Property 12 specifically covers IAM roles (a compliance-critical subset).
- No redundancy identified. All 12 properties provide unique validation value.

---

## Error Handling

### Flask Application

| Scenario | Handling |
|---|---|
| `POST /items` with missing/invalid JSON | Return HTTP 400 with `{"error": "Invalid request body"}` |
| `GET /items/<id>` for non-existent item | Return HTTP 404 with `{"error": "Item not found"}` |
| DynamoDB connection failure | Return HTTP 500 with `{"error": "Internal server error"}` (do not expose boto3 details) |
| Missing `DYNAMODB_TABLE_NAME` env var | Fail fast at startup with a clear error message |

### Test Runner

| Scenario | Handling |
|---|---|
| Connection refused / timeout | Record `error` field, set `status_code` and `response_body` to `null`, continue |
| HTTP error response (4xx, 5xx) | Record normally — these are expected results, not failures |
| JSON parse error on response body | Record raw response text in `response_body` |
| Config file missing | Exit with a clear error message before sending any requests |

### Report Generator

| Scenario | Handling |
|---|---|
| `results.json` not found | Exit with a clear error message |
| Malformed `results.json` | Exit with a clear error message indicating the parse error |
| Missing fields in results | Use `"N/A"` as the display value |

### Terraform

| Scenario | Handling |
|---|---|
| Missing permissions boundary | Terraform apply will fail at the AWS API level (MZJ-IAM policy enforcement) |
| Missing required tags | Terraform apply will fail at the AWS API level |
| `deployment.zip` not built | Terraform will fail with a file-not-found error; run `scripts/build.sh` first |

---

## Testing Strategy

### Unit Tests (`tests/unit/`)

Focus on specific examples and edge cases for the Flask application logic and script components.

- `test_app.py`: Test each Flask route with concrete examples using a mocked DynamoDB client (via `unittest.mock`).
  - `GET /` returns `{"status": "ok"}` with HTTP 200
  - `POST /items` with valid body returns HTTP 201 and the created item
  - `POST /items` with empty body returns HTTP 400
  - `GET /items/<id>` for existing item returns HTTP 200
  - `GET /items/<id>` for non-existent item returns HTTP 404
- `test_test_runner.py`: Test the recording and serialization logic with concrete examples.
- `test_report_generator.py`: Test report section generation with concrete examples.

### Property-Based Tests (`tests/property/`)

Use **Hypothesis** to verify universal properties across generated inputs. Each test runs a minimum of 100 iterations.

```python
# Example: Property 1 — Item creation round-trip
# Feature: lambda-web-adapter-migration-test, Property 1: Item creation round-trip
@given(st.fixed_dictionaries({"name": st.text(min_size=1)}))
@settings(max_examples=100)
def test_item_creation_round_trip(item_payload):
    ...
```

Properties covered:
- **Property 1**: Item creation round-trip (Hypothesis + mocked DynamoDB)
- **Property 2**: Invalid payloads rejected (Hypothesis generates invalid bodies)
- **Property 3**: Non-existent item returns 404 (Hypothesis generates random UUIDs)
- **Property 4**: TestRunner records all response fields (Hypothesis generates mock responses)
- **Property 5**: TestRunner sends identical requests to both endpoints
- **Property 6**: Test results JSON round-trip (Hypothesis generates result sets)
- **Property 7**: TestRunner continues on connection failure (Hypothesis generates failure types)
- **Property 8**: Report contains all required sections (Hypothesis generates result inputs)
- **Property 9**: Comparison table covers all tested endpoints
- **Property 10**: Conclusion states code change status
- **Property 11**: All Terraform resources have required tags (parse HCL, check tags)
- **Property 12**: All IAM roles have MZJTeamBoundary (parse HCL, check boundary)

### Integration Tests (`tests/integration/`)

Run against the actual deployed AWS infrastructure. These are not property-based tests — they use 1-3 representative examples.

- Verify Test 1 Lambda returns an error response (confirming `Runtime.HandlerNotFound` behavior)
- Verify Test 2 Lambda returns correct responses for all four endpoints
- Verify DynamoDB table exists and is accessible from both Lambda functions
- Verify API Gateway routes correctly to both Lambda functions

### Smoke Tests

Static checks that run without AWS credentials:

- Verify `app.py` has no `lambda_handler` function
- Verify `app.py` imports Flask and creates a Flask app instance
- Verify Terraform configuration has the correct provider region and profile
- Verify `deployment.zip` contains `app.py` and `run.sh`
- Verify `run.sh` is executable

### Bilingual Documentation Tests

- Verify `README.md` and `README_en.md` both exist and contain all required sections
- Verify `testing.md` and `testing_en.md` both exist and contain all required sections
- Verify `report.md` and `report_en.md` are both produced by the report generator

### Test Execution

```bash
# Unit + property tests (no AWS credentials needed)
pytest tests/unit/ tests/property/ -v

# Integration tests (requires deployed infrastructure)
pytest tests/integration/ -v

# All tests
pytest -v
```
