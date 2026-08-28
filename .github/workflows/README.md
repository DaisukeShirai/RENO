# GitHub Actions一覧

フロントエンドはGitHub Actionsから直接公開せず、Amplify Hostingのリポジトリ連携で公開します。リポジトリ直下の `amplify.yml` にビルド設定があります。

| 表示名 | ファイル | いつ使うか | 実行内容 |
|---|---|---|---|
| `CI: Test and optionally deploy backend` | `main-deploy.yml` | 通常のpush・Pull Request | LocalStack、SAM、React、Playwrightのテスト。AWSデプロイは手動入力時のみ |
| `PROD: Deploy backend to AWS (SAM)` | `deploy-backend.yml` | AWSバックエンドを更新するとき | `reno-mvp` のLambda、API Gateway、DynamoDB、S3、Cognitoをデプロイ |
| `REUSABLE: LocalStack smoke tests` | `localstack-test.yml` | 単独では使わない | 他のWorkflowから呼び出す共通テスト |

## 使い分け

- 画面を公開・更新する：Amplify Hostingの対象ブランチへpushする
- バックエンドを変更する：`PROD: Deploy backend to AWS (SAM)` を手動実行する
- テストを確認する：`CI: Test and optionally deploy backend` の結果を確認する
- `REUSABLE: LocalStack smoke tests` は直接実行しない

## Amplify Hostingの設定

1. Amplify HostingでこのGitHubリポジトリの `main` ブランチを接続する。
2. アプリの環境変数に `RENO_API_URL`、`RENO_MOCK_CHAT=false`、必要に応じて `COGNITO_CLIENT_ID` を設定する。
3. 保存後、Amplifyの自動ビルド・公開を実行する。

`amplify.yml` は `npm ci` と `npm run build:react` を実行し、生成された `dist` を公開します。OpenAI APIキーなどの秘密値はフロントエンド環境変数へ設定しません。

バックエンドのAPI URLやCognitoクライアントIDが変わった場合は、Amplifyの環境変数を更新して再デプロイします。
