# ブランチ運用と fork 同期フロー

## この図の前提

このリポジトリでは、`origin`（開発元）でIssueブランチを実装・検証し、CIに成功した同名ブランチだけを`fork`へ同期します。その後、`fork`側で`dev`、`staging`、`main`へPRで昇格します。Amplify Hostingは`fork`側の環境ブランチを参照します。

リモート名は次の意味です。

- `origin`: 開発元 `IFLAG-hps/RENO`
- `fork`: fork 先 `DaisukeShirai/RENO`
- Issueブランチ: `[Issue番号]-<内容>`（例：`30-実装-相談セッション履歴api`）

## ブランチ間の関係

```mermaid
flowchart LR
    I[issueブランチ<br/>課題ごとの作業・検証]
    PR[Pull Request<br/>fork側でレビュー・差分確認]
    M[fork側 dev<br/>開発環境の統合先]
    T[CI / E2E / SAM検証<br/>main-deploy.yml]
    S[sync-fork.yml<br/>workflow_run が成功した場合のみ]
    F[fork側 Issueブランチ<br/>DaisukeShirai/RENO]
    A[Amplify Hosting<br/>dev / staging / main を公開]

    I -->|push| PR
    PR -->|merge| M
    M --> T
    T -->|成功| S
    S -->|同じテスト済みコミットを push| F
    F --> A

    T -->|失敗| X[forkへは同期しない]
```

## 各ブランチの位置づけ

| 対象 | 役割 | 主な操作 | 公開環境への影響 |
| --- | --- | --- | --- |
| originのIssueブランチ | Issue単位の実装、修正、ローカル検証を行う作業場所 | `push`、CI実行 | CI成功後にforkへ自動同期 |
| forkのIssueブランチ | CI成功済みIssueブランチの読み取り専用ミラー | GitHub Actionsからpush | `dev`へのPR元になる |
| fork `dev` / `staging` / `main` | 開発・受入・公開環境の統合先 | PRをmerge | Amplifyの各環境を更新 |

## 通常の作業フロー

1. `fork/main`を基点に、`origin`で`[Issue番号]-<内容>`のIssueブランチを作成する。
2. Issueブランチを`origin`へpushし、`main-deploy.yml`で検証する。
3. CIが成功すると、`sync-fork.yml`が同名ブランチを`fork`へ自動同期する。
4. `fork`のIssueブランチから`fork/dev`へのPull Requestを作成する。
5. `dev`で確認後、`staging`、`main`へ順にPRで昇格する。
6. Amplify Hostingが各環境ブランチの更新を検知してビルド・公開する。

## 運用上の注意

- forkのIssueブランチへは手動でコミットせず、同期ワークフローによる更新を基本とする。
- CIが失敗した場合はforkへ同期されないため、失敗原因を修正して再度pushする。
- `fork/dev`、`fork/staging`、`fork/main`への直接pushは禁止し、必ずPRで昇格する。
- AWSバックエンドのデプロイは、環境ブランチのCI成功後に必要に応じて手動実行する。

## 関連設定

- [GitHub Actions運用](../github-actions運用.md)
- [`main-deploy.yml`](../../.github/workflows/main-deploy.yml)
- [`sync-fork.yml`](../../.github/workflows/sync-fork.yml)
