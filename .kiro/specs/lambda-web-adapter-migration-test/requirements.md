# Requirements Document

## Introduction

This document defines the requirements for the `lambda-web-adapter-migration-test` feature.

The goal of this project is to demonstrate that **aws-lambda-web-adapter** allows a standard Flask web application to run on AWS Lambda **without any application code changes**. The project runs two tests and compares the results:

- **Test 1 (No Adapter)**: Deploy the Flask app to Lambda without aws-lambda-web-adapter and observe the resulting errors (e.g., missing `lambda_handler`, HTTP server startup failure).
- **Test 2 (With Adapter)**: Deploy the same Flask app to Lambda with aws-lambda-web-adapter as a Lambda Extension and verify that all endpoints work correctly without any code changes.

The comparison results are output as Markdown reports in both Japanese (`report.md`) and English (`report_en.md`).

Infrastructure is managed with Terraform (profile: `terraform`, region: `ap-northeast-1`) and follows MZJ-IAM naming and tagging conventions.

---

## Glossary

- **System**: The overall project system
- **LocalApp**: The Flask web application that runs locally and is deployed to Lambda without modification
- **LambdaDeployer**: The component responsible for deploying to Lambda (Terraform)
- **TestRunner**: The Python script that executes test requests against both Lambda endpoints and records results
- **ReportGenerator**: The component that reads test results and produces the comparison Markdown report
- **aws-lambda-web-adapter**: An AWS-provided Lambda Extension that allows HTTP server-based web apps to run as Lambda functions without code changes
- **API_Gateway**: AWS API Gateway (HTTP API) acting as the frontend for both Lambda functions
- **DynamoDB**: AWS DynamoDB used as the application data store
- **MZJTeamBoundary**: The IAM Permissions Boundary defined by the MZJ team; required on all IAM roles created by members. ARN: `arn:aws:iam::681561127010:policy/MZJTeamBoundary`
- **IAM_Username**: The IAM username of the member (`Pranav`); used in resource naming and tagging
- **Project_Tag**: The project identifier tag applied to all resources (value: `lambda-web-adapter-migration-test`)

---

## Requirements

### Requirement 1: Local Flask Application

**User Story:** As a developer, I want a standard Flask web application that runs locally without any Lambda-specific code, so that I have a clean baseline that represents a typical on-premises Python web app before migration.

#### Acceptance Criteria

1. THE LocalApp SHALL be implemented using Flask as the web framework
2. THE LocalApp SHALL provide the following HTTP endpoints:
   - `GET /` — health check, returns `{"status": "ok"}` with HTTP 200
   - `GET /items` — retrieves all items from DynamoDB, returns HTTP 200 with a JSON array
   - `POST /items` — creates a new item in DynamoDB, returns HTTP 201 with the created item
   - `GET /items/{id}` — retrieves a specific item from DynamoDB by ID, returns HTTP 200 with the item
3. WHEN the local startup command is executed, THE LocalApp SHALL listen for HTTP requests on port 8000
4. WHEN a `GET /` request is received, THE LocalApp SHALL return HTTP 200 and `{"status": "ok"}`
5. WHEN a `POST /items` request is received with a valid JSON body, THE LocalApp SHALL persist the item to DynamoDB and return HTTP 201
6. IF a `POST /items` request is received with an invalid or missing JSON body, THEN THE LocalApp SHALL return HTTP 400 with a descriptive error message
7. IF a `GET /items/{id}` request is received for a non-existent item, THEN THE LocalApp SHALL return HTTP 404
8. THE LocalApp SHALL contain no Lambda-specific handler functions (e.g., no `lambda_handler`, no `handler` export)
9. THE LocalApp SHALL read the DynamoDB table name from the environment variable `DYNAMODB_TABLE_NAME`

---

### Requirement 2: Test 1 — Deploy WITHOUT aws-lambda-web-adapter

**User Story:** As a developer, I want to deploy the LocalApp to Lambda without aws-lambda-web-adapter, so that I can observe and document the errors that occur when a standard web app is deployed to Lambda as-is.

#### Acceptance Criteria

1. THE LambdaDeployer SHALL package the LocalApp for Lambda deployment without modifying any application source code
2. THE LambdaDeployer SHALL deploy the Lambda function to the `ap-northeast-1` region using Terraform with the `terraform` AWS profile
3. THE LambdaDeployer SHALL name the Lambda function `Pranav-lambda-web-adapter-migration-test-no-adapter`
4. THE LambdaDeployer SHALL create a Lambda execution IAM role named `Pranav-lambda-web-adapter-migration-test-role`
5. THE LambdaDeployer SHALL attach `arn:aws:iam::681561127010:policy/MZJTeamBoundary` as the Permissions Boundary on the Lambda execution role
6. THE LambdaDeployer SHALL tag the Lambda function with `User=Pranav` and `Project=lambda-web-adapter-migration-test`
7. WHEN the Test 1 Lambda function is invoked via API_Gateway, THE TestRunner SHALL record the HTTP status code, response body, and any error messages returned
8. THE TestRunner SHALL record that Test 1 produces errors such as "handler not found", "Runtime.HandlerNotFound", or HTTP server startup failure, confirming the app cannot run on Lambda without the adapter

---

### Requirement 3: Test 2 — Deploy WITH aws-lambda-web-adapter

**User Story:** As a developer, I want to deploy the same LocalApp to Lambda with aws-lambda-web-adapter added as a Lambda Extension, so that I can verify all endpoints work correctly without making any changes to the application code.

#### Acceptance Criteria

1. THE LambdaDeployer SHALL deploy the same LocalApp source code used in Test 1 without any application code modifications
2. THE LambdaDeployer SHALL attach aws-lambda-web-adapter as a Lambda Layer (Lambda Extension) to the function
3. THE LambdaDeployer SHALL name the Lambda function `Pranav-lambda-web-adapter-migration-test-with-adapter`
4. THE LambdaDeployer SHALL set the Lambda environment variable `AWS_LAMBDA_EXEC_WRAPPER` to `/opt/bootstrap`
5. THE LambdaDeployer SHALL set the Lambda environment variable `PORT` to `8000`
6. THE LambdaDeployer SHALL tag the Lambda function with `User=Pranav` and `Project=lambda-web-adapter-migration-test`
7. WHEN the Test 2 Lambda function is invoked via API_Gateway at `GET /`, THE TestRunner SHALL receive HTTP 200 and `{"status": "ok"}`
8. WHEN the Test 2 Lambda function is invoked via API_Gateway at `GET /items`, THE TestRunner SHALL receive HTTP 200 and a JSON array of items
9. WHEN the Test 2 Lambda function is invoked via API_Gateway at `POST /items` with a valid JSON body, THE TestRunner SHALL receive HTTP 201
10. WHEN the Test 2 Lambda function is invoked via API_Gateway at `GET /items/{id}`, THE TestRunner SHALL receive HTTP 200 and the corresponding item
11. THE TestRunner SHALL record that no application code changes were required to make Test 2 work

---

### Requirement 4: Terraform Infrastructure

**User Story:** As a developer, I want all AWS resources managed by Terraform following MZJ-IAM conventions, so that the environment is reproducible and compliant with team policies.

#### Acceptance Criteria

1. THE LambdaDeployer SHALL manage all AWS resources using Terraform with the `terraform` AWS profile and the `ap-northeast-1` region
2. THE LambdaDeployer SHALL apply the tags `User=Pranav` and `Project=lambda-web-adapter-migration-test` to every AWS resource created
3. THE LambdaDeployer SHALL attach `arn:aws:iam::681561127010:policy/MZJTeamBoundary` as the Permissions Boundary on every IAM role created
4. THE LambdaDeployer SHALL create an API_Gateway (HTTP API) that exposes endpoints for both the Test 1 and Test 2 Lambda functions
5. THE LambdaDeployer SHALL create a DynamoDB table named `Pranav-lambda-web-adapter-migration-test-items`
6. THE LambdaDeployer SHALL tag the DynamoDB table with `User=Pranav` and `Project=lambda-web-adapter-migration-test`
7. THE LambdaDeployer SHALL name all S3 buckets in lowercase following the pattern `pranav-lambda-web-adapter-migration-test-<purpose>`
8. WHEN `terraform destroy` is executed, THE LambdaDeployer SHALL remove all resources created by the Terraform configuration

---

### Requirement 5: Test Runner Script

**User Story:** As a developer, I want a Python script that automatically sends identical requests to both Lambda endpoints and records the results, so that I can produce an objective, reproducible comparison.

#### Acceptance Criteria

1. THE TestRunner SHALL send the same set of HTTP requests to both the Test 1 endpoint (no adapter) and the Test 2 endpoint (with adapter)
2. THE TestRunner SHALL record the HTTP status code, response body, and error message (if any) for each request
3. THE TestRunner SHALL read the API_Gateway endpoint URLs from a configuration file or environment variables
4. WHEN all test requests have completed, THE TestRunner SHALL save the results to a JSON file
5. IF a connection to an API_Gateway endpoint fails, THEN THE TestRunner SHALL record the error and continue to the next test case without stopping execution

---

### Requirement 6: Comparison Report

**User Story:** As a developer, I want a Markdown comparison report in both Japanese and English that clearly shows the Test 1 and Test 2 results side by side, so that I can share the findings with others.

#### Acceptance Criteria

1. THE ReportGenerator SHALL read the TestRunner output JSON and generate a comparison report
2. THE ReportGenerator SHALL output the Japanese report as `report.md`
3. THE ReportGenerator SHALL output the English report as `report_en.md`
4. THE ReportGenerator SHALL include the following sections in both reports:
   - Overview (purpose, environment, execution date/time)
   - Test 1 results (status code and error content per endpoint)
   - Test 2 results (status code and response content per endpoint)
   - Side-by-side comparison table (Test 1 vs Test 2 per endpoint)
   - Conclusion (whether application code changes were required)
5. THE ReportGenerator SHALL display Test 1 and Test 2 results for each endpoint in a side-by-side comparison table
6. THE ReportGenerator SHALL explicitly state in the conclusion section either "No application code changes were required" or "Application code changes were required"
7. WHEN `report.md` is updated, THE ReportGenerator SHALL also update `report_en.md` to reflect the same content in English

---

### Requirement 7: Documentation

**User Story:** As a developer, I want project documentation in both Japanese and English covering prerequisites, setup, deployment, testing, and report generation, so that anyone can follow the project end-to-end.

#### Acceptance Criteria

1. THE System SHALL provide `README.md` (Japanese) and `README_en.md` (English)
2. THE System SHALL include the following sections in both README files:
   - Project overview and purpose
   - Prerequisites (AWS CLI, Terraform, Python version, AWS credentials setup)
   - Setup instructions
   - Deployment instructions (Test 1 and Test 2)
   - Test execution instructions
   - Report generation instructions
3. WHEN `README.md` is updated, THE System SHALL also update `README_en.md` to reflect the same content in English

---

### Requirement 8: Testing Guide

**User Story:** As a developer, I want a dedicated step-by-step testing guide in both Japanese and English that walks me through the entire project workflow from local testing to report generation, so that I can run the project correctly and understand what each result means.

#### Acceptance Criteria

1. THE System SHALL provide `testing.md` (Japanese) and `testing_en.md` (English)
2. THE System SHALL include the following sections in both testing guide files:
   - Prerequisites check (AWS credentials, Terraform, Python dependencies)
   - Step 1: Local testing — how to run the Flask app locally and verify each endpoint
   - Step 2: Deploy Test 1 — how to run `terraform apply` for the no-adapter deployment
   - Step 3: Run Test 1 — how to invoke the Test 1 Lambda endpoints and what errors to expect
   - Step 4: Deploy Test 2 — how to run `terraform apply` for the with-adapter deployment
   - Step 5: Run Test 2 — how to invoke the Test 2 Lambda endpoints and what success responses to expect
   - Step 6: Run the TestRunner script — how to execute the automated test runner
   - Step 7: Generate the report — how to run the ReportGenerator and where to find the output files
3. THE System SHALL include expected output examples for each step so the user can verify their results are correct
4. THE System SHALL include a troubleshooting section that explains common errors and how to resolve them (e.g., missing `lambda_handler` error in Test 1, permission denied errors, DynamoDB connection failures)
5. WHEN `testing.md` is updated, THE System SHALL also update `testing_en.md` to reflect the same content in English
