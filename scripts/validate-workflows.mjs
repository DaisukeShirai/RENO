import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';

const files = {
  backend: '.github/workflows/deploy-backend.yml',
  all: '.github/workflows/deploy-all.yml',
  main: '.github/workflows/main-deploy.yml',
  localstack: '.github/workflows/localstack-test.yml'
};

const workflows = {};
for (const [name, file] of Object.entries(files)) {
  workflows[name] = await readFile(file, 'utf8');
}

for (const name of ['backend', 'all']) {
  assert.match(workflows[name], /if: github\.ref == 'refs\/heads\/main'/, `${name}: main branch restriction is missing`);
  assert.match(workflows[name], /uses: \.\/\.github\/workflows\/localstack-test\.yml/, `${name}: LocalStack test is missing`);
  assert.match(workflows[name], /needs: localstack-test/, `${name}: test dependency is missing`);
}

assert.match(workflows.main, /github\.ref == 'refs\/heads\/main'/, 'main-deploy: main branch restriction is missing');
assert.match(workflows.localstack, /workflow_call:/, 'LocalStack workflow_call is missing');
assert.match(workflows.backend, /OPENAI_API_KEY: \$\{\{ secrets\.OPENAI_API_KEY \}\}/, 'backend OpenAI key configuration is missing');
assert.match(workflows.all, /Show deployed API URL for Amplify/, 'Amplify API URL output is missing');
assert.doesNotMatch(workflows.all, /aws s3 sync dist|aws cloudfront create-invalidation/, 'direct S3/CloudFront deployment remains after Amplify migration');

console.log('Workflow validation passed: backend deployment is separated from Amplify frontend hosting.');
