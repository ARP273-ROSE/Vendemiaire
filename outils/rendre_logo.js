// Rend branding/logo.svg (SEULE source du logo) en PNG 16 → 1024 dans docs/.
// Usage : NODE_PATH=<dossier node_modules contenant @resvg/resvg-js> node outils/rendre_logo.js
// L'ICO et l'ICNS sont ensuite assemblés par « python -m vendemiaire.logo --assembler ».
const fs = require('fs');
const path = require('path');
const { Resvg } = require('@resvg/resvg-js');
const racine = path.resolve(__dirname, '..');
const svg = fs.readFileSync(path.join(racine, 'branding', 'logo.svg'));
for (const taille of [16, 24, 32, 48, 64, 128, 256, 512, 1024]) {
  const rendu = new Resvg(svg, { fitTo: { mode: 'width', value: taille }, background: 'rgba(0,0,0,0)' });
  fs.writeFileSync(path.join(racine, 'docs', `logo_${taille}.png`), rendu.render().asPng());
}
console.log('logo_{16..1024}.png écrits dans docs/');
