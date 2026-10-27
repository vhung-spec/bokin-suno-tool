// Builds dist/loi-dong-am.html: the page as one file with its scripts inlined, in the form Claude's Artifact viewer
// expects (no <html>/<head>/<body>; the viewer adds them). Run: node tools/build-artifact.js
const fs = require('node:fs');
const path = require('node:path');

const root = path.join(__dirname, '..');
const dir = path.join(root, 'loi-dong-am');
const page = fs.readFileSync(path.join(dir, 'index.html'), 'utf8');

const head = page.match(/<head>([\s\S]*?)<\/head>/)[1]
  .replace(/<meta charset[^>]*>\s*/, '')
  .replace(/<meta name="viewport"[^>]*>\s*/, '')
  .replace('</title>', '</title>\n<meta name="claude:viewport-fit-sides" content="cover">');
const body = page.match(/<body>([\s\S]*?)<\/body>/)[1];
if (!body.includes('<script src="engine.js"></script>')) throw new Error('index.html no longer loads engine.js');

// Each <script src="x.js"> from loi-dong-am/ goes in as an inline script, in the same order.
const inlined = body.replace(/<script src="([\w.-]+\.js)"><\/script>/g,
  (_, file) => `<script>\n${fs.readFileSync(path.join(dir, file), 'utf8').trim()}\n</script>`);
const out = head.trim() + '\n\n' + inlined.trim() + '\n';
fs.mkdirSync(path.join(root, 'dist'), { recursive: true });
fs.writeFileSync(path.join(root, 'dist', 'loi-dong-am.html'), out);
console.log('dist/loi-dong-am.html', out.length, 'bytes');
