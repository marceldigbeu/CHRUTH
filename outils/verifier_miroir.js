/* Verifie que le miroir HTML s'execute vraiment, ecran par ecran.
 *
 * Une inspection du DOM ne suffit pas : le contenu est rendu dans <main>, qui
 * precede la balise <script>, et un fichier casse peut rendre un DOM volumineux
 * fait du seul code source. On charge donc le script avec un faux document, et
 * on appelle chaque fonction de rendu pour voir ce qu'elle produit.
 *
 * Usage :  node outils/verifier_miroir.js [chemin.html]
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const fichier = process.argv[2] ||
  path.join(__dirname, "..", "CHRUTH_PLATEFORME.html");

const html = fs.readFileSync(fichier, "utf8");
const script = /<script[^>]*>([\s\S]*)<\/script>/.exec(html);
if (!script) {
  console.error("ECHEC : aucune balise script trouvee.");
  process.exit(1);
}

/* Faux document : juste assez pour que le script s'installe sans navigateur. */
function faireElement(id) {
  return {
    id, innerHTML: "", textContent: "", value: "0", dataset: {}, style: {},
    classList: { add() {}, remove() {}, toggle() {} },
    setAttribute() {}, removeAttribute() {}, appendChild() {},
    addEventListener() {}, querySelectorAll: () => [], querySelector: () => null,
    getAttribute: () => null,
  };
}

const elements = {};
const document = {
  documentElement: faireElement("html"),
  body: faireElement("body"),
  getElementById(id) { return (elements[id] = elements[id] || faireElement(id)); },
  querySelector() { return faireElement("q"); },
  querySelectorAll() { return []; },
  createElement(t) { return faireElement(t); },
  addEventListener() {},
};

const localStorage = {
  _d: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this._d, k) ? this._d[k] : null; },
  setItem(k, v) { this._d[k] = String(v); },
  removeItem(k) { delete this._d[k]; },
};

const contexte = {
  document, localStorage, console,
  window: { matchMedia: () => ({ matches: false, addEventListener() {} }), addEventListener() {} },
  matchMedia: () => ({ matches: false, addEventListener() {} }),
  setTimeout, clearTimeout, setInterval, clearInterval,
  navigator: { userAgent: "verificateur" },
};
contexte.window.document = document;
contexte.window.localStorage = localStorage;
contexte.globalThis = contexte;

/* Le script est encapsule dans une fonction anonyme : ses fonctions de rendu ne
 * sont pas accessibles de l'exterieur. On ne les appelle donc pas — on fixe la
 * page dans l'etat persiste, puis on relit le script, qui rend cette page au
 * demarrage. C'est le chemin reel, celui qu'emprunte un navigateur. */
const CLE = "chruth_html_v1";

const ecrans = [
  ["accueil", ["Echeances les plus proches", "Retenus par le tri"]],
  ["veille", ["Score minimum", 'id="jauge"']],
  ["pilotage", ["En attente de tri", "Par departement"]],
  ["acheteurs", []],
  ["messages", []],
  ["reglages", []],
];

let echecs = 0;
for (const [page, attendus] of ecrans) {
  const elements2 = {};
  const doc = {
    documentElement: faireElement("html"),
    body: faireElement("body"),
    getElementById(id) { return (elements2[id] = elements2[id] || faireElement(id)); },
    querySelector() { return faireElement("q"); },
    querySelectorAll() { return []; },
    createElement(t) { return faireElement(t); },
    addEventListener() {},
  };
  const stockage = Object.create(localStorage);
  stockage._d = { [CLE]: JSON.stringify({ page, ov: {}, theme: null }) };

  const ctx = {
    document: doc, localStorage: stockage, console,
    window: { matchMedia: () => ({ matches: false, addEventListener() {} }), addEventListener() {} },
    matchMedia: () => ({ matches: false, addEventListener() {} }),
    setTimeout, clearTimeout, setInterval, clearInterval,
    navigator: { userAgent: "verificateur" },
  };
  ctx.window.document = doc;
  ctx.window.localStorage = stockage;
  ctx.globalThis = ctx;

  try {
    vm.createContext(ctx);
    vm.runInContext(script[1], ctx, { filename: "miroir.js" });
  } catch (e) {
    console.error(`ECHEC ${page} : ${e.message}`);
    echecs++;
    continue;
  }

  const rendu = String((elements2.main && elements2.main.innerHTML) || "");
  if (rendu.length < 200) {
    console.error(`ECHEC ${page} : rendu vide ou trop court (${rendu.length}).`);
    echecs++;
    continue;
  }
  const manquants = attendus.filter((a) => rendu.indexOf(a) === -1);
  if (manquants.length) {
    console.error(`ECHEC ${page} : attendus absents ${JSON.stringify(manquants)}`);
    echecs++;
    continue;
  }
  console.log(`  OK ${page} : ${rendu.length} caracteres rendus`);
}

if (echecs) {
  console.error(`\n${echecs} ecran(s) en echec.`);
  process.exit(1);
}
console.log("\nTous les ecrans du miroir s'affichent.");
