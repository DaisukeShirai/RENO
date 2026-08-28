# GitHub Actions運用

## 現在の公開構成

フロントエンドはAmplify HostingのGitHubリポジトリ連携で公開します。`main` ブランチへのpushを契機にAmplifyがビルド・デプロイします。GitHub ActionsからGitHub PagesやS3へ直接配信するフローは使用しません。

```text
GitHub main push
      ↓
Amplify Hosting（amplify.ymlでReact/Viteをビルド）
      ↓
Amplify管理の配信基盤
      ↓
API Gateway → Lambda → OpenAI API / DynamoDB / S3
```

## フロントエンドのビルド

リポジトリ直下の `amplify.yml` を使用します。

```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - node scripts/generate-config.mjs
        - npm run build:react
  artifacts:
    baseDirectory: dist
    files:
      - '**/*'
```

`RENO_API_URL`、`RENO_MOCK_CHAT`、`COGNITO_CLIENT_ID` などの公開可能な設定値はAmplifyの環境変数で管理します。OpenAI APIキーやトークン秘密鍵はフロントエンドへ渡さず、バックエンドのSecretsとして管理します。

## Actionsの使い分け

### `main-deploy.yml`

LocalStack、SAM、React、PlaywrightのCIを実行します。AWSへの実デプロイは、手動実行で入力を明示的に有効化した場合だけ行います。

### `deploy-backend.yml`

`main` ブランチからAWS SAMでLambda、API Gateway、DynamoDB、S3、Cognitoを手動デプロイします。デプロイ後、出力されたAPI URLとCognitoクライアントIDをAmplifyの環境変数へ反映します。

### `localstack-test.yml`

他のWorkflowから呼び出す再利用可能なテストWorkflowです。単独では通常実行しません。

## 操作手順

### 画面を公開・更新する場合

1. `main` へpushする。
2. Amplify Hostingのビルド結果を確認する。
3. Amplifyの公開URLで画面、チャット、画像処理を確認する。

### バックエンドを更新する場合

1. `PROD: Deploy backend to AWS (SAM)` を手動実行する。
2. `reno-mvp` の更新成功を確認する。
3. API URLやCognitoクライアントIDが変わった場合はAmplifyの環境変数を更新し、再デプロイする。

GitHub Pages用の `deploy-pages.yml` は `.github/workflows/` から移動し、[アーカイブ](archive/workflows/deploy-pages.yml) として保存しています。Actions画面には表示されません。
