// Builds dist/loi-dong-am.html: the page as one file with the engine inlined, in the form Claude's Artifact viewer
// expects (no <html>/<head>/<body>; the viewer adds them). Run: node tools/build-artifact.js
const fs = require('node:fs');
const path = require('node:path');

const root = path.join(__dirname, '..');
const page = fs.readFileSync(path.join(root, 'loi-dong-am', 'index.html'), 'utf8');
const engine = fs.readFileSync(path.join(root, 'loi-dong-am', 'engine.js'), 'utf8');

const head = page.match(/<head>([\s\S]*?)<\/head>/)[1]
  .replace(/<meta charset[^>]*>\s*/, '')
  .replace(/<meta name="viewport"[^>]*>\s*/, '')
  .replace('</title>', '</title>\n<meta name="claude:viewport-fit-sides" content="cover">');
const body = page.match(/<body>([\s\S]*?)<\/body>/)[1];
const script = '<script src="engine.js"></script>';
if (!body.includes(script)) throw new Error(`index.html no longer loads the engine with ${script}`);

const out = head.trim() + '\n\n' + body.replace(script, () => `<script>\n${engine.trim()}\n</script>`).trim() + '\n';
fs.mkdirSync(path.join(root, 'dist'), { recursive: true });
fs.writeFileSync(path.join(root, 'dist', 'loi-dong-am.html'), out);
console.log('dist/loi-dong-am.html', out.length, 'bytes');
