import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

// Run the actual gallery module with only the DOM primitives needed at startup.
class Element {
  style = {};
  append() {}
  attachShadow() { return {}; }
}

const registry = new Map();
const source = fs.readFileSync(new URL('../ui/gallery.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } });
vm.runInNewContext(compiled.outputText, {
  exports: {},
  require: () => ({}),
  HTMLElement: Element,
  CSSStyleSheet: class {},
  document: { createElement: () => new Element() },
  customElements: { define: (name, cls) => registry.set(name, cls) },
  window: {},
  AbortController,
});

const GalleryFolder = registry.get('gallery-folder');
// /browser/folders returns raw strings in these objects, including literal %.
for (const path of ['outputs/text', 'outputs/100% complete', 'outputs/literal%20space', 'C:/images/100%']) {
  const label = path.split('/').pop();
  const folder = new GalleryFolder({ path, label });
  assert.equal(folder.name, path);
  assert.equal(folder.label, label);
}
const fallbackLabel = new GalleryFolder({ path: 'outputs/100%' });
assert.equal(fallbackLabel.label, 'outputs/100%');
// Preserve support for the older URI-encoded string response.
const legacyFolder = new GalleryFolder('outputs/old%20folder');
assert.equal(legacyFolder.name, 'outputs/old folder');
assert.equal(legacyFolder.label, 'outputs/old folder');
console.log('Gallery folder API response checks passed');
