# フロントエンドのデプロイ

## 一時公開：S3 + CloudFront

`.github/workflows/deploy-cloudfront.yml`をGitHub Actionsから手動実行する。
フロントエンドだけをS3へ同期し、CloudFrontのキャッシュを無効化する。LambdaやDynamoDBのリソースは変更しない。

RENO専用の配信基盤は`infra/frontend-cloudfront.yaml`で作成する。既存のS3バケットやCloudFrontディストリビューションは使用しない。

GitHubの`production`環境に次のSecretsを登録する。

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

次のVariablesを登録する。

- `FRONTEND_BUCKET`: CloudFrontのオリジンになっているS3バケット
- `CLOUDFRONT_DISTRIBUTION_ID`: CloudFrontディストリビューションID
- `RENO_API_URL`: API Gatewayの`/agent`エンドポイント
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`

`RENO_MOCK_CHAT=false`を固定しているため、設定したAPI Gateway経由でLambdaを呼び出す。
OpenAIの秘密鍵はフロントエンドへ渡さず、Lambdaの環境変数またはGitHub Secretsから設定する。

## 正式公開：Amplify Hosting + Lambda

正式公開時はAmplify Hostingのリポジトリ連携へ切り替える。ビルド前に同じ環境変数を設定し、リポジトリルートを成果物として配信する。

```yaml
version: 1
frontend:
  phases:
    build:
      commands:
        - node scripts/generate-config.mjs
        - rm -rf dist
        - mkdir -p dist
        - cp index.html dist/index.html
        - cp -R assets dist/assets
        - cp -R pages dist/pages
  artifacts:
    baseDirectory: dist
    files:
      - '**/*'
```

APIの実装とURLは共通なので、CloudFront用ワークフローを停止してAmplifyの自動デプロイを有効にするだけで移行できる。

## 全機能を一度にデプロイ

バックエンドとフロントエンドを同時に更新して動作確認する場合は、
`Deploy full MVP`を手動実行する。Lambdaを先にデプロイし、CloudFormationの出力からAPI URLを自動取得してCloudFrontへ反映する。

このワークフローには、既存のAWS Secretsに加えて次のSecretsが必要になる。

- `OPENAI_API_KEY`
- `TOKEN_SECRET`

`OPENAI_MODEL`、`SES_FROM_EMAIL`、`SES_TO_EMAIL`は必要に応じてVariablesへ登録する。

## 本番デプロイのブランチ制限

本番リソースを更新するジョブは`main`ブランチからの実行に限定している。
featureブランチから手動実行した場合は、LocalStackのスモークテストだけを実行し、本番デプロイジョブはスキップする。

## バックエンドだけを更新

`Deploy backend only`を手動実行すると、Lambda / API Gateway / DynamoDB / S3 / Cognitoのバックエンドだけを更新する。
CloudFrontやフロントエンドのS3ファイルは変更しない。API URLは実行ログに表示される。
