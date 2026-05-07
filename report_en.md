# Lambda Web Adapter Migration Test Report

## Overview

This report summarizes the comparison results of deploying a Flask application to AWS Lambda.

- **Test 1 (No Adapter)**: Deployed without aws-lambda-web-adapter
- **Test 2 (With Adapter)**: Deployed with aws-lambda-web-adapter as a Lambda Layer

- **Execution Time**: 2026-04-23T08:07:14Z
- **Test 1 Endpoint**: https://flw5pq61li.execute-api.ap-northeast-1.amazonaws.com/test1
- **Test 2 Endpoint**: https://flw5pq61li.execute-api.ap-northeast-1.amazonaws.com/test2

## Test 1 Results (No Adapter)

| Endpoint | Status Code | Error |
|---|---|---|
| GET / | 500 | Internal Server Error |
| GET /items | 500 | Internal Server Error |
| POST /items | 500 | Internal Server Error |
| GET /items/00000000-0000-0000-0000-000000000000 | 500 | Internal Server Error |

## Test 2 Results (With Adapter)

| Endpoint | Status Code | Response Body | Error |
|---|---|---|---|
| GET / | 200 | {"status": "ok"} | None |
| GET /items | 200 | [{"created_at": "2026-04-23T08:05:38.763725+00:00", "id": "4dcf8e38-5f40-4e70-9dce-995b0a3abf39", "name": "test-item"}] | None |
| POST /items | 201 | {"created_at": "2026-04-23T08:07:14.049834+00:00", "id": "53930e32-5465-40a8-9404-2d49b69918e2", "name": "test-item"} | None |
| GET /items/00000000-0000-0000-0000-000000000000 | 404 | {"error": "Item not found"} | None |

## Comparison Table

| Endpoint | Test 1 Result | Test 2 Result |
|---|---|---|
| GET / | 500 / Internal Server Error | 200 |
| GET /items | 500 / Internal Server Error | 200 |
| POST /items | 500 / Internal Server Error | 201 |
| GET /items/00000000-0000-0000-0000-000000000000 | 500 / Internal Server Error | 404 |

## Conclusion

All Test 2 endpoints responded successfully. **No application code changes were required.**
