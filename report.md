# Lambda Web Adapter 移行テスト レポート

## 概要

本レポートは、Flask アプリケーションを AWS Lambda にデプロイした際の動作比較結果をまとめたものです。

- **テスト 1（アダプターなし）**: aws-lambda-web-adapter を使用せずにデプロイ
- **テスト 2（アダプターあり）**: aws-lambda-web-adapter を Lambda Layer として追加してデプロイ

- **実行日時**: 2026-04-23T08:07:14Z
- **テスト 1 エンドポイント**: https://flw5pq61li.execute-api.ap-northeast-1.amazonaws.com/test1
- **テスト 2 エンドポイント**: https://flw5pq61li.execute-api.ap-northeast-1.amazonaws.com/test2

## テスト 1 結果（アダプターなし）

| エンドポイント | ステータスコード | エラー |
|---|---|---|
| GET / | 500 | Internal Server Error |
| GET /items | 500 | Internal Server Error |
| POST /items | 500 | Internal Server Error |
| GET /items/00000000-0000-0000-0000-000000000000 | 500 | Internal Server Error |

## テスト 2 結果（アダプターあり）

| エンドポイント | ステータスコード | レスポンスボディ | エラー |
|---|---|---|---|
| GET / | 200 | {"status": "ok"} | なし |
| GET /items | 200 | [{"created_at": "2026-04-23T08:05:38.763725+00:00", "id": "4dcf8e38-5f40-4e70-9dce-995b0a3abf39", "name": "test-item"}] | なし |
| POST /items | 201 | {"created_at": "2026-04-23T08:07:14.049834+00:00", "id": "53930e32-5465-40a8-9404-2d49b69918e2", "name": "test-item"} | なし |
| GET /items/00000000-0000-0000-0000-000000000000 | 404 | {"error": "Item not found"} | なし |

## 比較表

| エンドポイント | テスト 1 結果 | テスト 2 結果 |
|---|---|---|
| GET / | 500 / Internal Server Error | 200 |
| GET /items | 500 / Internal Server Error | 200 |
| POST /items | 500 / Internal Server Error | 201 |
| GET /items/00000000-0000-0000-0000-000000000000 | 500 / Internal Server Error | 404 |

## 結論

テスト 2 の全エンドポイントが正常に応答しました。**アプリケーションコードの変更は不要でした。**
