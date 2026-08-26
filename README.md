# RENO

## 環境変数

ローカル設定は`.env`に置きます。`.env.example`をコピーして値を設定し、静的フロントエンド用の設定ファイルを生成してください。

```sh
npm run build:config
```

このコマンドが`.env`の公開設定（Supabase URL・Anon Key・API URL・モック設定）だけを`assets/reno-config.js`へ出力します。`OPENAI_API_KEY`と`TOKEN_SECRET`などのバックエンド専用値はブラウザへ出力しません。

`.env`はGit管理対象外です。デプロイ環境では、バックエンドの秘密値をSAMパラメータまたはLambda環境変数として設定してください。
