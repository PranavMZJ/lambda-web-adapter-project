# Implementation Plan: lambda-web-adapter-migration-test

## Overview

This plan implements a side-by-side comparison of a Flask application deployed to AWS Lambda with and without aws-lambda-web-adapter. Tasks are ordered so each step builds on the previous: project scaffolding → Flask app → build script → Terraform infrastructure → test runner → report generator → unit tests → property tests → documentation → integration tests.

All code is Python. Infrastructure is Terraform (HCL). Property-based tests use Hypothesis.

## Tasks

- [x] 1. Project scaffolding and Kiro setup
  - [x] 1.1 Create project directory structure and initial files
    - Create the full directory tree: `app/`, `terraform/modules/{dynamodb,iam,lambda-no-adapter,lambda-with-adapter,api-gateway}/`, `scripts/`, `results/`, `tests/unit/`, `tests/property/`, `tests/integration/`
    - Create `.gitignore` with entries for `deployment.zip`, `results/results.json`, `config.json`, `terraform.tfvars`, `terraform/.terraform/`, `*.tfstate*`, `__pycache__/`, `.pytest_cache/`
    - Create `app/requirements.txt` with `flask`, `gunicorn`, `boto3`
    - Create `config.json` placeholder with empty `test1_url` and `test2_url` fields
    - _Requirements: 1.1, 1.2, 4.1_

  - [x] 1.2 Create Kiro steering file for naming and tagging conventions
    - Create `.kiro/steering/naming-tagging.md` capturing MZJ-IAM rules:
      - All resources must have `User=Pranav` and `Project=lambda-web-adapter-migration-test` tags
      - Resource names follow `Pranav-lambda-web-adapter-migration-test-<purpose>` pattern
      - S3 bucket names must be lowercase: `pranav-lambda-web-adapter-migration-test-<purpose>`
      - All IAM roles must have `arn:aws:iam::681561127010:policy/MZJTeamBoundary` as permissions boundary
    - _Requirements: 4.2, 4.3_

  - [x] 1.3 Create Kiro steering file for bilingual documentation
    - Create `.kiro/steering/bilingual-docs.md` capturing the rule:
      - All project `.md` files have a Japanese default and an `_en.md` English counterpart
      - `.kiro/` spec files are English only
    - _Requirements: 6.2, 6.3, 7.1, 7.3, 8.1, 8.5_

  - [x] 1.4 Create Kiro hooks for bilingual sync and post-task testing
    - Create `.kiro/hooks/sync-bilingual-docs.json`: triggers on `fileEdited` for `*.md` (excluding `_en.md` and `.kiro/**`), asks agent to update the corresponding `_en.md`
    - Create `.kiro/hooks/post-task-test.json`: triggers on `postTaskExecution`, runs `scripts/test_runner.py`
    - _Requirements: 6.7, 7.3, 8.5_

- [x] 2. Implement Flask application
  - [x] 2.1 Implement `app/app.py` — Flask application with all routes
    - Import Flask, boto3, uuid, datetime, os
    - Read `DYNAMODB_TABLE_NAME` from environment variable; fail fast at startup if missing
    - Implement `GET /` returning `{"status": "ok"}` with HTTP 200
    - Implement `GET /items` returning all items from DynamoDB as a JSON array with HTTP 200
    - Implement `POST /items` validating JSON body (require non-empty `name`), generating UUID, persisting to DynamoDB, returning HTTP 201
    - Implement `GET /items/<id>` returning the item or HTTP 404
    - Handle DynamoDB errors with HTTP 500 (no boto3 details exposed)
    - Ensure NO `lambda_handler` function exists anywhere in the file
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_

  - [x] 2.2 Create `app/run.sh` — gunicorn startup script
    - Create the shell script that starts gunicorn on `$PORT` (default 8000)
    - Set `PATH` and `PYTHONPATH` for Lambda runtime compatibility
    - Make the script executable (`chmod +x`)
    - _Requirements: 1.3, 3.4, 3.5_

- [x] 3. Create build script
  - [x] 3.1 Implement `scripts/build.sh` — builds deployment.zip
    - Create a temp directory, copy `app/app.py`, `app/run.sh`, `app/requirements.txt`
    - Run `pip install -r requirements.txt -t .` in the temp directory
    - Ensure `run.sh` has execute permission
    - Zip all contents into `deployment.zip` at the project root
    - Clean up the temp directory
    - Make the script executable
    - _Requirements: 2.1, 3.1_

- [x] 4. Checkpoint — Verify Flask app and build
  - Ensure the Flask app runs locally (`DYNAMODB_TABLE_NAME=test flask run -p 8000`) and `GET /` returns `{"status": "ok"}`
  - Ensure `scripts/build.sh` produces `deployment.zip` containing `app.py` and `run.sh`
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Terraform infrastructure modules
  - [x] 5.1 Create `terraform/variables.tf` and `terraform/terraform.tfvars`
    - Define variables: `region` (default `ap-northeast-1`), `aws_profile` (default `terraform`), `name_prefix`, `permissions_boundary_arn`, `user_tag`, `project_tag`
    - Create `terraform.tfvars` with concrete values for Pranav's environment
    - _Requirements: 4.1, 4.2_

  - [x] 5.2 Implement `terraform/modules/dynamodb/` — DynamoDB table module
    - Create `main.tf`, `variables.tf`, `outputs.tf`
    - Define `aws_dynamodb_table` with name `Pranav-lambda-web-adapter-migration-test-items`, hash key `id` (String), billing mode PAY_PER_REQUEST
    - Apply required tags via variable
    - Output `table_name` and `table_arn`
    - _Requirements: 4.5, 4.6_

  - [x] 5.3 Implement `terraform/modules/iam/` — Lambda execution role module
    - Create `main.tf`, `variables.tf`, `outputs.tf`
    - Define `aws_iam_role` with name `Pranav-lambda-web-adapter-migration-test-role`
    - Set trust policy for `lambda.amazonaws.com`
    - Set `permissions_boundary` to `arn:aws:iam::681561127010:policy/MZJTeamBoundary`
    - Attach `AWSLambdaBasicExecutionRole` managed policy
    - Create inline policy for DynamoDB access (GetItem, PutItem, Scan on the table)
    - Apply required tags
    - Output `lambda_role_arn`
    - _Requirements: 2.4, 2.5, 4.2, 4.3_

  - [x] 5.4 Implement `terraform/modules/lambda-no-adapter/` — Test 1 Lambda module
    - Create `main.tf`, `variables.tf`, `outputs.tf`
    - Define `aws_lambda_function` with name `Pranav-lambda-web-adapter-migration-test-no-adapter`
    - Set handler to `run.sh`, runtime to `python3.12`
    - Reference `deployment.zip` from project root
    - Set `DYNAMODB_TABLE_NAME` environment variable
    - No layers attached
    - Apply required tags
    - Output `function_arn` and `invoke_arn`
    - _Requirements: 2.1, 2.2, 2.3, 2.6_

  - [x] 5.5 Implement `terraform/modules/lambda-with-adapter/` — Test 2 Lambda module
    - Create `main.tf`, `variables.tf`, `outputs.tf`
    - Define `aws_lambda_function` with name `Pranav-lambda-web-adapter-migration-test-with-adapter`
    - Set handler to `run.sh`, runtime to `python3.12`
    - Reference same `deployment.zip` from project root
    - Attach LWA layer: `arn:aws:lambda:ap-northeast-1:753240598075:layer:LambdaAdapterLayerX86:27`
    - Set environment variables: `DYNAMODB_TABLE_NAME`, `AWS_LAMBDA_EXEC_WRAPPER=/opt/bootstrap`, `PORT=8000`
    - Apply required tags
    - Output `function_arn` and `invoke_arn`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 5.6 Implement `terraform/modules/api-gateway/` — HTTP API module
    - Create `main.tf`, `variables.tf`, `outputs.tf`
    - Define `aws_apigatewayv2_api` (HTTP API)
    - Create two Lambda integrations (no-adapter and with-adapter)
    - Create routes: `ANY /test1/{proxy+}` → no-adapter, `ANY /test2/{proxy+}` → with-adapter
    - Create `aws_apigatewayv2_stage` with auto-deploy enabled
    - Create `aws_lambda_permission` for both functions
    - Apply required tags
    - Output `api_endpoint`
    - _Requirements: 4.4_

  - [x] 5.7 Create `terraform/main.tf` — root module wiring all child modules
    - Configure AWS provider with `var.region` and `var.aws_profile`
    - Define `locals` for `common_tags` and `name_prefix`
    - Call all five child modules with correct variable passing
    - _Requirements: 4.1, 4.2_

  - [x] 5.8 Create `terraform/outputs.tf` — root outputs
    - Output API Gateway endpoint URL, both Lambda function ARNs, DynamoDB table name
    - _Requirements: 4.4_

- [x] 6. Checkpoint — Verify Terraform configuration
  - Run `terraform init` and `terraform validate` in the `terraform/` directory
  - Verify all modules are correctly wired
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement test runner script
  - [x] 7.1 Implement `scripts/test_runner.py`
    - Read endpoint URLs from `config.json` (keys: `test1_url`, `test2_url`) or environment variables `TEST1_URL`, `TEST2_URL`
    - Exit with clear error if config is missing
    - Define test cases: `GET /`, `GET /items`, `POST /items` (with valid JSON body), `GET /items/{id}`
    - Send identical requests to both Test 1 and Test 2 endpoints
    - For each request, record: endpoint, status_code, response_body, error
    - Handle connection failures (timeout, refused, DNS) gracefully — record error, continue to next test case
    - Handle non-JSON response bodies by recording raw text
    - Write results to `results/results.json` with timestamp, test1, and test2 sections
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 8. Implement report generator script
  - [x] 8.1 Implement `scripts/report_generator.py`
    - Read `results/results.json`; exit with clear error if missing or malformed
    - Generate `report.md` (Japanese) with sections: Overview, Test 1 results, Test 2 results, comparison table, conclusion
    - Generate `report_en.md` (English) with the same sections
    - Comparison table: one row per endpoint, columns for endpoint, Test 1 result, Test 2 result
    - Conclusion: state "No application code changes were required" or "Application code changes were required" based on Test 2 success
    - Use `"N/A"` for missing fields in results
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 9. Checkpoint — Verify scripts
  - Create a sample `results/results.json` and run `scripts/report_generator.py` to verify report output
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement unit tests
  - [x] 10.1 Implement `tests/unit/test_app.py` — Flask route unit tests
    - Use Flask test client with mocked DynamoDB (unittest.mock)
    - Test `GET /` returns 200 and `{"status": "ok"}`
    - Test `POST /items` with valid body returns 201 and created item
    - Test `POST /items` with empty body returns 400
    - Test `POST /items` with missing `name` returns 400
    - Test `GET /items/<id>` for existing item returns 200
    - Test `GET /items/<id>` for non-existent item returns 404
    - Test `GET /items` returns 200 with JSON array
    - _Requirements: 1.2, 1.4, 1.5, 1.6, 1.7_

  - [x] 10.2 Implement `tests/unit/test_test_runner.py` — TestRunner unit tests
    - Test recording logic with concrete mock HTTP responses
    - Test JSON serialization of results
    - Test error handling for connection failures
    - Test config file reading
    - _Requirements: 5.1, 5.2, 5.4, 5.5_

  - [x] 10.3 Implement `tests/unit/test_report_generator.py` — ReportGenerator unit tests
    - Test report generation with sample results.json
    - Test that both report.md and report_en.md are produced
    - Test all five sections are present in output
    - Test comparison table row count matches endpoint count
    - Test conclusion content
    - Test handling of missing fields (N/A fallback)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [ ] 11. Implement property-based tests
  - [ ]* 11.1 Write property test for item creation round-trip
    - **Property 1: Item creation round-trip**
    - Use Hypothesis to generate valid item payloads (non-empty name, arbitrary string fields)
    - POST to `/items`, GET by returned ID, verify field values match
    - Use mocked DynamoDB
    - **Validates: Requirements 1.5**

  - [ ]* 11.2 Write property test for invalid payload rejection
    - **Property 2: Invalid payloads are rejected**
    - Use Hypothesis to generate invalid bodies: non-JSON, missing `name`, empty/whitespace `name`
    - Verify `POST /items` returns HTTP 400
    - **Validates: Requirements 1.6**

  - [ ]* 11.3 Write property test for non-existent item 404
    - **Property 3: Non-existent item returns 404**
    - Use Hypothesis to generate random UUIDs not in the table
    - Verify `GET /items/{id}` returns HTTP 404
    - **Validates: Requirements 1.7**

  - [ ]* 11.4 Write property test for TestRunner response field recording
    - **Property 4: TestRunner records all response fields**
    - Use Hypothesis to generate mock HTTP responses with varying status codes, bodies, errors
    - Verify the recording function captures all fields without dropping any
    - **Validates: Requirements 2.7, 5.2**

  - [ ]* 11.5 Write property test for TestRunner identical requests
    - **Property 5: TestRunner sends identical requests to both endpoints**
    - Use Hypothesis to generate test case configurations
    - Verify the same set of requests (methods, paths, bodies) is sent to both endpoints
    - **Validates: Requirements 5.1**

  - [ ]* 11.6 Write property test for test results JSON round-trip
    - **Property 6: Test results JSON round-trip**
    - Use Hypothesis to generate result sets with varying test cases, status codes, bodies, errors
    - Serialize to JSON and deserialize, verify equivalence
    - **Validates: Requirements 5.4**

  - [ ]* 11.7 Write property test for TestRunner connection failure resilience
    - **Property 7: TestRunner continues on connection failure**
    - Use Hypothesis to generate connection failure types (timeout, refused, DNS)
    - Verify error is recorded and remaining test cases execute
    - **Validates: Requirements 5.5**

  - [ ]* 11.8 Write property test for report required sections
    - **Property 8: Report contains all required sections**
    - Use Hypothesis to generate valid results.json inputs
    - Verify both report.md and report_en.md contain all five sections
    - **Validates: Requirements 6.1, 6.4**

  - [ ]* 11.9 Write property test for comparison table completeness
    - **Property 9: Comparison table covers all tested endpoints**
    - Use Hypothesis to generate result sets with N endpoints
    - Verify comparison table has exactly N rows
    - **Validates: Requirements 6.5**

  - [ ]* 11.10 Write property test for conclusion statement
    - **Property 10: Conclusion states code change status**
    - Use Hypothesis to generate various test results
    - Verify conclusion contains exactly one of the two required statements
    - **Validates: Requirements 6.6**

  - [ ]* 11.11 Write property test for Terraform resource tags
    - **Property 11: All Terraform resources have required tags**
    - Parse all `.tf` files, find resource blocks with `tags` attributes
    - Verify each includes `User = "Pranav"` and `Project = "lambda-web-adapter-migration-test"`
    - **Validates: Requirements 4.2**

  - [ ]* 11.12 Write property test for IAM role permissions boundary
    - **Property 12: All IAM roles have MZJTeamBoundary**
    - Parse all `.tf` files, find `aws_iam_role` resource blocks
    - Verify `permissions_boundary` is set to `arn:aws:iam::681561127010:policy/MZJTeamBoundary`
    - **Validates: Requirements 4.3**

- [x] 12. Checkpoint — Run all unit and property tests
  - Run `pytest tests/unit/ tests/property/ -v`
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Create project documentation
  - [x] 13.1 Create `README.md` (Japanese) and `README_en.md` (English)
    - Include sections: Project overview, Prerequisites, Setup instructions, Deployment instructions (Test 1 and Test 2), Test execution instructions, Report generation instructions
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 13.2 Create `testing.md` (Japanese) and `testing_en.md` (English)
    - Include sections: Prerequisites check, Step 1 (local testing), Step 2 (deploy Test 1), Step 3 (run Test 1), Step 4 (deploy Test 2), Step 5 (run Test 2), Step 6 (run TestRunner), Step 7 (generate report), Troubleshooting
    - Include expected output examples for each step
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 14. Implement integration tests (optional — requires deployed infrastructure)
  - [ ]* 14.1 Implement `tests/integration/test_deployed.py`
    - Verify Test 1 Lambda returns error response (Runtime.HandlerNotFound)
    - Verify Test 2 Lambda returns correct responses for all four endpoints
    - Verify DynamoDB table exists and is accessible
    - Verify API Gateway routes correctly to both Lambda functions
    - Read endpoint URLs from `config.json` or environment variables
    - _Requirements: 2.7, 2.8, 3.7, 3.8, 3.9, 3.10, 3.11_

- [x] 15. Final checkpoint — Ensure all tests pass
  - Run `pytest tests/unit/ tests/property/ -v`
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate the 12 correctness properties from the design document using Hypothesis
- Unit tests validate specific examples and edge cases
- Integration tests (task 14) require deployed AWS infrastructure and are marked optional
- The build script (task 3) must be completed before Terraform tasks (task 5) since Terraform references `deployment.zip`
- All Python code uses Python 3.12 to match the Lambda runtime
