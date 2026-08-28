# GitHub Actions一覧

Actions画面で迷った場合は、次の基準で選択してください。

| 表示名 | ファイル | いつ使うか | 実行内容 |
|---|---|---|---|
| `PROD: Deploy frontend to GitHub Pages` | `deploy-pages.yml` | フロントを公開・更新するとき | `index.html`、`assets/`、`pages/`をGitHub Pagesへ公開 |
| `CI: Test and optionally deploy backend` | `main-deploy.yml` | 通常は自動実行 | LocalStack、SAM、Playwrightのテスト。AWSデプロイ部分は手動入力時のみ |
| `PROD: Deploy backend to AWS (SAM)` | `deploy-backend.yml` | AWSバックエンドを更新するとき | `reno-mvp`のLambda、API Gateway、DynamoDB、S3、Cognitoをデプロイ |
| `REUSABLE: LocalStack smoke tests` | `localstack-test.yml` | 単独では使わない | 他のWorkflowから呼び出す共通テスト |

## 迷ったときの選び方

- 画面の修正を公開する：`PROD: Deploy frontend to GitHub Pages`
- バックエンドを変更した：`PROD: Deploy backend to AWS (SAM)`
- テストだけ確認したい：`CI: Test and optionally deploy backend`
- `REUSABLE: LocalStack smoke tests`は直接実行しない

## 現在使わないWorkflow

Amplify向けの旧`deploy-all.yml`は削除済みです。

将来Amplify Hostingへ切り替える場合は、Actionsを増やすのではなく、リポジトリ連携と`amplify.yml`を使用します。AWSバックエンド用の`deploy-backend.yml`は継続利用します。
