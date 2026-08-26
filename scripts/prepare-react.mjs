import { mkdir, readFile, writeFile } from 'node:fs/promises';

const source = await readFile('index.html', 'utf8');
const body = source.match(/<body[^>]*>([\s\S]*?)<\/body>/i)?.[1];
const styles = [...source.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/gi)].map((match) => match[1]);
const inlineScripts = [...source.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi)];

if (!body || styles.length === 0 || inlineScripts.length < 2) {
  throw new Error('index.htmlからReact互換資材を抽出できませんでした。');
}

// body内のscriptはReact描画後に別ファイルとして実行するため、マークアップから除外する。
const markup = body.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '').trim();
const applicationScript = inlineScripts.at(-1)[1].trim();
const compatibilityCss = `
#root, .react-legacy-host { display: contents; }
.react-bootstrap-error {
  position: fixed; inset: 16px 16px auto; z-index: 100000;
  padding: 12px 16px; color: #8a2424; background: #fff4f2;
  border: 1px solid #d8a29b; border-radius: 8px; font: 13px sans-serif;
}
`;

await mkdir('react/generated', { recursive: true });
await mkdir('react/public', { recursive: true });
await writeFile('react/generated/legacy-markup.js', `export default ${JSON.stringify(markup)};\n`, 'utf8');
await writeFile('react/generated/legacy.css', `${styles.join('\n')}\n${compatibilityCss}`, 'utf8');
await writeFile('react/public/legacy-bootstrap.js', `${applicationScript}\n`, 'utf8');
console.log('現行index.htmlからReact互換資材を生成しました。');
