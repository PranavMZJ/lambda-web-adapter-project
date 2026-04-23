# テストガイド

本ドキュメントは、lambda-web-adapter-migration-test プロジェクトのテスト手順をステップバイステップで説明します。

## 前提条件の確認

テストを開始する前に、以下の前提条件を確認してください。

### AWS 認証情報

```bash
aws sts get-caller-identity --profile terraform
```

期待される出力：

```json
{
    "UserId": "AIDXXXXXXXXXXXXXXXXX",
    "Account": "681561127010",
    "Arn": "arn:aws:iam::681561127010:user/Pranav"
}
```

### Terraform

```bash
terraform --version
```

期待される出力（例）：

```
Terraform v1.x.x
```

### Python 依存パッケージ

```bash
python3 --version
pip install flask gunicorn boto3 pytest hypothesis
```

Python 3.9 以上であることを確認してください。

---

## ステップ 1: ローカルテスト

Flask アプリをローカルで起動し、基本的な動作を確認します。

### アプリの起動

```bash
DYNAMODB_TABLE_NAME=test flask run -p 8000
```

> **注意**: ローカル環境では DynamoDB に接続できないため、`GET /` のヘルスチェックのみテスト可能です。

### ヘルスチェックの確認

別のターミナルで以下を実行します：

```bash
curl http://localhost:8000/
```

期待される出力：

```json
{"status": "ok"}
```

この応答が返れば、Flask アプリが正常に動作しています。

---

## ステップ 2: デプロイメントパッケージのビルド

Lambda にデプロイするための `deployment.zip` をビルドします。

```bash
bash scripts/build.sh
```

期待される出力：

```
Built deployment.zip
```

### 確認

```bash
ls -la deployment.zip
```

`deployment.zip` ファイルが存在することを確認してください。

---

## ステップ 3: インフラのデプロイ

Terraform を使用して AWS リソースをデプロイします。

```bash
cd terraform
terraform init
terraform apply
```

`terraform apply` の確認プロンプトで `yes` を入力します。

期待される出力（末尾）：

```
Apply complete! Resources: X added, 0 changed, 0 destroyed.

Outputs:

api_endpoint = "https://<api-id>.execute-api.ap-northeast-1.amazonaws.com"
dynamodb_table_name = "Pranav-lambda-web-adapter-migration-test-items"
lambda_no_adapter_arn = "arn:aws:lambda:ap-northeast-1:681561127010:function:Pranav-lambda-web-adapter-migration-test-no-adapter"
lambda_with_adapter_arn = "arn:aws:lambda:ap-northeast-1:681561127010:function:Pranav-lambda-web-adapter-migration-test-with-adapter"
```

```bash
cd ..
```

---

## ステップ 4: config.json の更新

Terraform の出力から API Gateway URL を取得し、`config.json` を更新します。

```bash
cd terraform
terraform output api_endpoint
cd ..
```

`config.json` を以下のように編集します：

```json
{
  "test1_url": "https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/test1",
  "test2_url": "https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/test2"
}
```

`<api-id>` を実際の API Gateway ID に置き換えてください。

---

## ステップ 5: テスト 1 の手動実行（アダプターなし）

テスト 1 のエンドポイントに手動でリクエストを送信します。**エラーが返ることが期待される動作です。**

### ヘルスチェック

```bash
curl https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/test1/
```

期待される出力：

```json
{"message":"Internal Server Error"}
```

### アイテム一覧取得

```bash
curl https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/test1/items
```

期待される出力：

```json
{"message":"Internal Server Error"}
```

### アイテム作成

```bash
curl -X POST https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/test1/items \
  -H "Content-Type: application/json" \
  -d '{"name": "test-item"}'
```

期待される出力：

```json
{"message":"Internal Server Error"}
```

> **重要**: テスト 1 では全てのリクエストがエラーを返します。これは `Runtime.HandlerNotFound` エラーによるもので、Flask アプリが aws-lambda-web-adapter なしでは Lambda 上で動作できないことを確認する**期待される動作**です。

---

## ステップ 6: テスト 2 の手動実行（アダプターあり）

テスト 2 のエンドポイントに手動でリクエストを送信します。**正常な応答が返ることが期待されます。**

### ヘルスチェック

```bash
curl https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/test2/
```

期待される出力：

```json
{"status": "ok"}
```

### アイテム一覧取得

```bash
curl https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/test2/items
```

期待される出力：

```json
[]
```

### アイテム作成

```bash
curl -X POST https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/test2/items \
  -H "Content-Type: application/json" \
  -d '{"name": "test-item"}'
```

期待される出力（例）：

```json
{
  "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "name": "test-item",
  "created_at": "2025-01-01T00:00:00+00:00"
}
```

### 作成したアイテムの取得

上記で返された `id` を使用します：

```bash
curl https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/test2/items/<id>
```

期待される出力：

```json
{
  "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "name": "test-item",
  "created_at": "2025-01-01T00:00:00+00:00"
}
```

---

## ステップ 7: 自動テストランナーの実行

```bash
python3 scripts/test_runner.py
```

期待される出力：

```
Running tests against Test 1: https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/test1
Running tests against Test 2: https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/test2
Results written to results/results.json

--- TEST1 (https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/test1) ---
  GET /: status=500  Internal Server Error
  GET /items: status=500  Internal Server Error
  POST /items: status=500  Internal Server Error
  GET /items/00000000-0000-0000-0000-000000000000: status=500  Internal Server Error

--- TEST2 (https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/test2) ---
  GET /: status=200
  GET /items: status=200
  POST /items: status=201
  GET /items/00000000-0000-0000-0000-000000000000: status=404
```

---

## ステップ 8: レポートの生成

```bash
python3 scripts/report_generator.py
```

期待される出力：

```
Report written to report.md
Report written to report_en.md
Done.
```

---

## ステップ 9: レポートの確認

生成されたレポートを確認します：

```bash
cat report.md
cat report_en.md
```

各レポートには以下のセクションが含まれます：

1. **概要** — テストの目的、環境、実行日時
2. **テスト 1 結果** — アダプターなしの各エンドポイントのステータスコードとエラー
3. **テスト 2 結果** — アダプターありの各エンドポイントのステータスコードとレスポンス
4. **比較表** — テスト 1 とテスト 2 の結果を並べた比較表
5. **結論** — アプリケーションコードの変更が必要だったかどうか

---

## トラブルシューティング

### "Runtime.HandlerNotFound" エラー（テスト 1）

**これは期待される動作です。** テスト 1 は aws-lambda-web-adapter なしでデプロイされているため、Lambda は `run.sh` を Python モジュールとしてインポートしようとし、`lambda_handler` 関数が見つからずにエラーを返します。このエラーは、アダプターなしではアプリが Lambda 上で動作できないことを証明しています。

### Permission denied / MZJTeamBoundary エラー

IAM ロールに正しいパーミッションバウンダリが設定されているか確認してください：

- パーミッションバウンダリ ARN: `arn:aws:iam::681561127010:policy/MZJTeamBoundary`
- `terraform/modules/iam/main.tf` の `permissions_boundary` 設定を確認してください

```bash
cd terraform
terraform plan
```

を実行して、IAM ロールの設定を確認できます。

### DynamoDB アクセス拒否エラー

Lambda 実行ロールに DynamoDB へのアクセス権限があるか確認してください：

- `terraform/modules/iam/main.tf` のインラインポリシーに `dynamodb:GetItem`、`dynamodb:PutItem`、`dynamodb:Scan` が含まれていることを確認してください
- テーブル名が `Pranav-lambda-web-adapter-migration-test-items` であることを確認してください

### config.json が空

`terraform output` を実行して API Gateway URL を取得し、`config.json` を更新してください：

```bash
cd terraform
terraform output api_endpoint
cd ..
```

出力された URL を使用して `config.json` の `test1_url` と `test2_url` を設定します。

### deployment.zip が見つからない

ビルドスクリプトを実行してください：

```bash
bash scripts/build.sh
```

`deployment.zip` がプロジェクトルートに生成されたことを確認してから、`terraform apply` を再実行してください。

### テスト 2 でタイムアウトが発生する

Lambda 関数のコールドスタートにより、初回リクエストに時間がかかる場合があります。数秒待ってから再度リクエストを送信してください。

### results.json が見つからない

テストランナーを先に実行してください：

```bash
python3 scripts/test_runner.py
```

`results/results.json` が生成されたことを確認してから、レポートジェネレーターを実行してください。
