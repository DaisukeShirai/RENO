# Fork中心の環境昇格ワークフロー

## 目的

Fork元（`IFLAG-hps/RENO`）では、Feature単位の実装とCIだけを行う。Amplifyへの接続権限を持つFork先（`DaisukeShirai/RENO`）で、開発確認・受入確認・公開を完結させる。

## リポジトリとブランチの役割

| リポジトリ | ブランチ | 役割 |
| --- | --- | --- |
| Fork元 | `feature/<内容>` | 実装、ユニット／E2E／SAMのCI |
| Fork先 | `feature/<内容>` | CI成功済みFeatureの読み取り専用ミラー |
| Fork先 | `dev` | 開発環境。Featureを結合して開発用URLで確認 |
| Fork先 | `staging` | 上長の受入確認用環境 |
| Fork先 | `main` | 承認済みの公開環境。現在の動作デモ完成版を基準にする |

Fork先の`dev`、`staging`、`main`がリリースの正本である。Fork元の`main`、`dev`、`staging`は環境昇格には使用しない。

## 標準フロー

```mermaid
flowchart LR
  OF["Fork元 feature/<内容>"] -->|"CI成功後に自動同期"| FF["Fork先 feature/<内容>"]
  FF -->|"PR・CI"| D["Fork先 dev\n開発用Amplify・devスタック"]
  D -->|"PR・CI"| S["Fork先 staging\n受入用Amplify・stagingスタック"]
  S -->|"上長承認・PR"| M["Fork先 main\n公開用Amplify・prodスタック"]
```

1. Notionにタスク、完了条件、見積工数を登録する。
2. Fork元の`main`を基点に`feature/<内容>`を作成し、実装・ローカルテストを行う。
3. Fork元のCIが成功すると、同期WorkflowがFork先の同名`feature/<内容>`へ反映する。Fork先のFeatureブランチはミラーのため直接変更しない。
4. Fork先で`feature/<内容>`から`dev`へのPRを作成する。CI成功後にマージすると、Amplifyの開発用URLと`reno-mvp-dev`が更新される。
5. 開発用URLで確認した変更を、Fork先の`dev`から`staging`へPRで昇格する。マージ後、Amplifyの受入用URLと`reno-mvp-staging`が更新される。
6. 上長がstaging URLで受入確認を行う。
7. 承認後、Fork先の`staging`から`main`へPRを作成してマージする。`reno-mvp-prod`と公開用Amplify URLが更新される。
8. 本番バックエンドのデプロイ成功後、Fork先の`main`をFork元の`main`へ自動同期する。Fork元の`main`は公開済みリリースのミラーであり、承認経路には含めない。
9. Notionに実績工数、確認URL、リリース結果を記録する。

## マージとデプロイの規則

- 同じ機能変更を`feature → dev → staging → main`の順に進める。環境ごとに別実装を作らない。
- Fork先の`dev`、`staging`、`main`への直接pushは禁止し、必ずPRで昇格する。
- Fork元のCIに失敗したFeatureはFork先へ同期しない。
- Fork先のFeatureブランチはFork元の内容で強制同期される。Fork先で直接コミットすると失われる。
- Fork先`main`の公開内容は、デプロイ成功後にFork元`main`へ同期する。次のFeatureはFork元`main`を基点に作成する。
- Fork先の`dev`、`staging`、`main`へのpushで、それぞれ`reno-mvp-dev`、`reno-mvp-staging`、`reno-mvp-prod`を自動デプロイする。
- GitHub Environmentの承認ルールを設定した場合、バックエンドデプロイは承認待ちで停止する。PR承認だけで自動公開したい場合は、`production` Environmentに追加承認を設定しない。
- Amplifyのブランチ自動ビルドとバックエンドデプロイは並行して動く。API変更は後方互換性を保つか、段階的なリリースにする。

## Phaseとの関係

Phaseは機能範囲、Fork先のブランチは環境昇格の経路である。

| フェーズ | 主な成果物 | 昇格経路 |
| --- | --- | --- |
| Phase 1：動作デモ | 現在のReact画面・既存導線 | 完了済み。Fork先`main`を基準版として維持 |
| Phase 2：MVP接続版 | S3アップロード、相談保存、受付API、SES、履歴取得 | Fork先`feature` → `dev` → `staging` → `main` |
| Phase 3：本番MVP | 画像生成・ファイル保存・エラー処理・AWS結合テスト | Fork先`feature` → `dev` → `staging` → `main` |

## ロールバック

- `dev`／`staging`：問題のPRをrevertし、対象ブランチへマージする。
- `main`：公開済みPRをrevertし、Fork先`main`へマージする。Amplifyと`reno-mvp-prod`が再デプロイされる。
- データ形式を破壊する変更は、先に互換性のあるスキーマ・移行処理を入れ、ロールバック手順をPRに記載する。
