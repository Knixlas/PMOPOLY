// Gör en publicerbar sida av bygget: CSS och JS inline, bilderna publiceras bredvid (bilder/).
// Artefakten får inget eget <html>/<head>/<body> (plattformen lägger till dem).
//   npm run build && node verktyg/artefakt.mjs
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';

const dist = new URL('../dist/', import.meta.url);
const html = readFileSync(new URL('index.html', dist), 'utf8');
const css = [...html.matchAll(/href="\.\/(assets\/[^"]+\.css)"/g)].map(m => readFileSync(new URL(m[1], dist), 'utf8'));
const js = [...html.matchAll(/src="\.\/(assets\/[^"]+\.js)"/g)].map(m => readFileSync(new URL(m[1], dist), 'utf8'));
if (js.some(k => /^\s*import\s/m.test(k))) throw new Error('bygget har flera JS-delar; artefakten kräver en');
const typsnitt = html.match(/<link rel="stylesheet" href="https:\/\/fonts\.googleapis\.com[^>]+>/)?.[0] ?? '';
const sida = `<title>Kvarterspusslet</title>
${typsnitt}
<style>${css.join('\n')}</style>
<div id="app"></div>
<script type="module">${js.join('\n').replace(/<\/script/g, '<\\/script')}</script>
`;
writeFileSync(new URL('artefakt.html', dist), sida);
const bilder = readdirSync(new URL('bilder/', dist));
console.log(`dist/artefakt.html (${Math.round(sida.length / 1024)} kB) + ${bilder.length} bilder`);
