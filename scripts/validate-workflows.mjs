import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';

const files = {
  backend: '.github/workflows/deploy-backend.yml',
  frontend: '.github/workflows/deploy-cloudfront.yml',
  all: '.github/workflows/deploy-all.yml',
  main: '.github/workflows/main-deploy.yml',
  localstack: '.github/workflows/localstack-test.yml'
};

const workflows = {};
for (const [name, file] of Object.entries(files)) {
  workflows[name] = await readFile(file, 'utf8');
}

// 本番デプロイ用ワークフローは、必ずmainブランチだけを許可する。
for (const name of ['backend', 'frontend', 'all']) {
  assert.match(workflows[name], /if: github\.ref == 'refs\/heads\/main'/, `${name}: main限定条件がありません`);
  assert.match(workflows[name], /uses: \.\/\.github\/workflows\/localstack-test\.yml/, `${name}: LocalStackテストがありません`);
  assert.match(workflows[name], /needs: localstack-test/, `${name}: テスト依存関係がありません`);
}

assert.match(workflows.main, /github\.ref == 'refs\/heads\/main'/, 'main-deploy: main限定条件がありません');
assert.match(workflows.localstack, /workflow_call:/, 'LocalStackテストが再利用可能になっていません');
assert.match(workflows.backend, /OPENAI_API_KEY: \$\{\{ secrets\.OPENAI_API_KEY \}\}/, 'バックエンドにOpenAIキー設定がありません');
assert.match(workflows.all, /Get deployed API URL/, '一括デプロイのAPI URL自動取得がありません');
assert.match(workflows.all, /npm run build:react/, '一括デプロイがReact版をビルドしていません');
assert.doesNotMatch(workflows.frontend, /OPENAI_API_KEY/, 'フロントエンドへOpenAIキーを渡してはいけません');
assert.match(workflows.frontend, /npm run build:react/, 'CloudFrontデプロイがReact版をビルドしていません');
assert.match(workflows.frontend, /aws cloudfront create-invalidation/, 'CloudFrontキャッシュ無効化がありません');

console.log('Workflow validation passed: main制限、LocalStack依存、秘密情報分離、CloudFront反映を確認しました。');
