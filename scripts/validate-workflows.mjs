import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';

const files = {
  backend: '.github/workflows/deploy-backend.yml',
  pages: '.github/workflows/deploy-pages.yml',
  main: '.github/workflows/main-deploy.yml',
  localstack: '.github/workflows/localstack-test.yml'
};

const workflows = {};
for (const [name, file] of Object.entries(files)) {
  workflows[name] = await readFile(file, 'utf8');
}

for (const name of ['backend']) {
  assert.match(workflows[name], /if: github\.ref == 'refs\/heads\/main'/, `${name}: main branch restriction is missing`);
  assert.match(workflows[name], /uses: \.\/\.github\/workflows\/localstack-test\.yml/, `${name}: LocalStack test is missing`);
  assert.match(workflows[name], /needs: localstack-test/, `${name}: test dependency is missing`);
}

assert.match(workflows.main, /github\.ref == 'refs\/heads\/main'/, 'main-deploy: main branch restriction is missing');
assert.match(workflows.localstack, /workflow_call:/, 'LocalStack workflow_call is missing');
assert.match(workflows.backend, /OPENAI_API_KEY: \$\{\{ secrets\.OPENAI_API_KEY \}\}/, 'backend OpenAI key configuration is missing');
assert.match(workflows.pages, /actions\/upload-pages-artifact@v3/, 'GitHub Pages artifact upload is missing');
assert.match(workflows.pages, /actions\/deploy-pages@v4/, 'GitHub Pages deployment is missing');
assert.doesNotMatch(workflows.pages, /Amplify|aws s3 sync|aws cloudfront create-invalidation/, 'legacy hosting deployment remains in Pages workflow');

console.log('Workflow validation passed: GitHub Pages frontend and AWS backend deployments are separated.');
