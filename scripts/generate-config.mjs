import { readFile, writeFile } from 'node:fs/promises';

const env = {};
let dotenv = '';
try {
  dotenv = await readFile('.env', 'utf8');
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}
for (const line of dotenv.split(/\r?\n/)) {
  const match = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
  if (match && !match[1].startsWith('#')) env[match[1]] = match[2].replace(/^['"]|['"]$/g, '');
}

// CIでは.envが存在しないため、環境変数を優先して参照する。
const value = (name) => process.env[name] ?? env[name] ?? '';
const config = `// 公開設定のみ出力。秘密情報はこのファイルへ出力しない。\nwindow.RENO_CONFIG = ${JSON.stringify({
  apiUrl: value('RENO_API_URL'),
  mockChat: value('RENO_MOCK_CHAT') !== 'false',
  supabaseUrl: value('SUPABASE_URL'),
  supabaseAnonKey: value('SUPABASE_ANON_KEY'),
  cognitoClientId: value('COGNITO_CLIENT_ID'),
  cognitoRegion: value('AWS_REGION') || 'ap-northeast-1'
}, null, 2)};\n`;
await writeFile('assets/reno-config.js', config, 'utf8');
console.log('Generated assets/reno-config.js');
