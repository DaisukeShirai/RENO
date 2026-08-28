# GitHub Actions運用整理

## 現在の公開構成

現在はAmplify Hostingではなく、GitHub Pagesをフロントエンドの公開先として使用する。

```text
GitHub Pages
  ↓ HTTPS
API Gateway → Lambda → OpenAI API
                    ├→ DynamoDB
                    └→ S3
```

フロントエンドはリポジトリ内の`index.html`、`assets/`、`pages/`を静的ファイルとして公開する。
API URLはGitHub Actionsで`assets/reno-config.js`へ生成する。OpenAI APIキーなどの秘密情報はブラウザへ出力しない。

将来Amplify Hostingへ切り替える場合は、リポジトリ連携を有効化し、ルートの`amplify.yml`を使用する。
AWSバックエンド用のActionsはそのまま継続利用する。

## Amplify公開時との差分

| 項目 | Amplify公開時 | 現在のGitHub Pages公開 |
|---|---|---|
| フロント公開先 | Amplify Hosting | GitHub Pages |
| ビルド | React/Viteで`dist`を生成 | 静的な`index.html`と関連ファイルを`_site`へコピー |
| 公開トリガー | Amplifyのリポジトリ連携 | `main`へのpushで`deploy-pages.yml`を実行 |
| 設定値 | Amplify環境変数 | GitHub Repository VariablesまたはWorkflowの既定API URL |
| CDN | Amplify管理の配信基盤 | GitHub Pagesの配信基盤 |
| アクセス制限 | Amplify Access Control（過去のBasic認証） | 現在は公開ページ。デモ用途の自動セッション発行 |
| バックエンド | API Gateway / Lambdaなど | 同じAWSバックエンドを継続利用 |
| Supabase | 旧構成に残っていた | 使用しない |

## Actionsの仕分け

### 今使うもの

#### `deploy-pages.yml`

GitHub Pagesへフロントエンドを公開するWorkflow。`main`へのpushで自動実行する。
動作デモではこれがフロント公開の基本Workflowになる。

#### `main-deploy.yml`（CIテスト用途）

LocalStack、SAMの検証、React互換ビルド、PlaywrightのE2Eを実行する。
通常のpush・Pull Requestで品質確認に使用する。

AWSへの実デプロイ部分は、必要な場合に手動実行するものとして扱う。

#### `localstack-test.yml`

他のWorkflowから呼び出す再利用可能なテストWorkflow。単独で通常実行するものではないが、削除しない。

### 本番環境時に使うもの

#### `deploy-backend.yml`

AWS SAMで`reno-mvp`を手動デプロイするWorkflow。
本番バックエンドの更新時に使用する。

必要な主なSecrets / Variables：

- Secrets：`AWS_ACCESS_KEY_ID`
- Secrets：`AWS_SECRET_ACCESS_KEY`
- Secrets：`OPENAI_API_KEY`
- Secrets：`TOKEN_SECRET`
- Variables：`OPENAI_MODEL`
- Variables：`ADMIN_EMAIL`
- Variables：`DEMO_PIN`

フロントエンドはGitHub Pagesが自動更新するため、バックエンド更新時にフロントをAWSへ同期する必要はない。

### 使わないもの（削除）

#### `deploy-all.yml`

削除対象。Amplify向けの旧名称・旧出力が残っており、`deploy-backend.yml`とバックエンドデプロイ処理が重複している。

## 運用手順

### デモ画面を更新する場合

1. `main`へpushする。
2. `Deploy frontend to GitHub Pages`の成功を確認する。
3. GitHub Pagesの公開URLで確認する。

### バックエンドを更新する場合

1. `Deploy backend to AWS`を手動実行する。
2. `reno-mvp`の更新成功を確認する。
3. GitHub Pagesからチャット・画像処理を確認する。

### デモと本番の違い

現在のデモではPIN入力を省略し、ブラウザごとにデモセッションを発行する。
正式公開時には、PIN、利用回数制限、レート制限、管理者認証を再検討する。
