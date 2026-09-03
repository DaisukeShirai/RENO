# 環境別開発ワークフロー

## 目的

2026年9月3日時点の `main` は、動作デモ完成版として固定する。追加のMVP実装は `dev` で行い、レビュー可能な単位で `staging` に反映する。

フェーズとブランチは別の概念である。フェーズは「何を作るか」という実装範囲、ブランチは「同じ変更をどの環境で確認するか」という昇格経路を表す。Phase 2・Phase 3の変更も、すべて `dev` → `staging` → `main` の順に同じコミットを進める。

## ブランチと環境

| ブランチ | 用途 | Amplify Hosting | 変更の扱い |
| --- | --- | --- | --- |
| `main` | 動作デモ完成版・承認済み公開版 | 本番デモURL | 直接pushしない。承認済みの`staging`だけをマージ |
| `staging` | 上長確認・受入確認 | ステージングURL | `dev`からレビュー済みの機能をマージ |
| `dev` | 日常の開発・結合 | 開発用URL | 作業ブランチからPRをマージ |
| `feature/<内容>` | 個別タスクの実装 | 原則なし | `dev`向けPRを作成 |

Amplifyには `main`、`staging`、`dev` をそれぞれ別ブランチとして接続し、各ブランチのpushで対応するプレビュー環境を更新する。環境ごとにAPI URL、モック設定、Cognitoクライアントなどの公開設定を分ける。バックエンドはブランチ単位ではなく、`dev`、`staging`、`production`の3スタックで分離する。

## 標準フロー

1. Notionでタスク、完了条件、見積工数を登録する。
2. `dev`から `feature/<内容>` ブランチを作成する。
3. 実装・ローカルテストを行い、作業ブランチから `dev` へPRを作成する。
4. CI（バックエンド、SAM、E2E、Reactビルド）が成功したことを確認して `dev` にマージする。`dev`へのpushは `reno-mvp-dev` バックエンドスタックを更新する。
5. `dev`のプレビュー環境で動作確認し、タスクの実績工数と検証結果をNotionに記録する。
6. まとまった機能単位で `dev` から `staging` へPRを作成する。
7. `staging`のバックエンドデプロイを手動実行して `reno-mvp-staging` を更新し、プレビューURLを上長へ共有して受入確認を受ける。
8. 承認された変更だけを `staging` から `main` へPRでマージする。`production`スタックの更新は、`main`から手動実行する。
9. `main`のCI成功後、動作デモURLで最終確認する。

## マージルール

- `main`、`staging`、`dev`への直接pushは行わない。
- `main`には動作デモを壊さない、受入確認済みの変更だけを反映する。
- 1つのPRは原則として1機能・1課題に分ける。
- PRには変更内容、確認URL、テスト結果、既知の制約を記載する。
- `dev`で不安定な実験的変更は `staging`へ上げない。
- 本番AWSバックエンドのデプロイは、別途承認を得てから実施する。ブランチの自動ビルドとAWSバックエンドのデプロイは分けて扱う。

## フェーズと昇格経路

| フェーズ | 主な成果物 | 昇格経路 |
| --- | --- | --- |
| Phase 1：動作デモ | 現在のReact画面・既存導線 | 完了済み。`main`を基準版として維持 |
| Phase 2：MVP接続版 | S3アップロード、相談保存、受付API、SES、履歴取得 | `feature/*` → `dev` → `staging` → `main` |
| Phase 3：本番MVP | 画像生成・ファイル保存・エラー処理・AWS結合テスト | `feature/*` → `dev` → `staging` → `main` |

例えば「写真のS3保存」を実装したコミットは、まず`dev`のAPI・画面で確認し、同じコミットを`staging`で上長に確認してもらい、承認後に`main`へ反映する。`staging`にだけ存在する機能、`main`にだけ存在する別実装を作らない。

## バックエンドデプロイの扱い

| Gitブランチ | CloudFormationスタック | 実行方法 | GitHub Environment |
| --- | --- | --- | --- |
| `dev` | `reno-mvp-dev` | push時に自動デプロイ | `dev` |
| `staging` | `reno-mvp-staging` | 手動実行 | `staging` |
| `main` | `reno-mvp-prod` | 手動実行・承認必須 | `production` |

`main-deploy.yml` は `main`、`staging`、`dev` へのpushと、それらを対象とするPRで検証を実行する。`deploy-backend.yml` がLocalStackテスト後に対象スタックを更新する。各スタックはDynamoDB、S3、Cognitoを個別に作成するため、データは環境間で共有されない。
