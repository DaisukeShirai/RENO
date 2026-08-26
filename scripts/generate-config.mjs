import { readFile, writeFile } from 'node:fs/promises';

const env = {};
for (const line of (await readFile('.env', 'utf8')).split(/\r?\n/)) {
  const match = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
  if (match && !match[1].startsWith('#')) env[match[1]] = match[2].replace(/^['"]|['"]$/g, '');
}

const config = `// .envから生成。秘密情報をこのファイルへ出力しない。\nwindow.RENO_CONFIG = ${JSON.stringify({
  apiUrl: env.RENO_API_URL || '',
  mockChat: env.RENO_MOCK_CHAT !== 'false',
  supabaseUrl: env.SUPABASE_URL || '',
  supabaseAnonKey: env.SUPABASE_ANON_KEY || ''
}, null, 2)};\n`;
await writeFile('assets/reno-config.js', config, 'utf8');
console.log('Generated assets/reno-config.js');
