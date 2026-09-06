import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

// modules/ui_extensions.py renders the hidden action controls as gr.Button,
// with a shared gr.Textbox that supplies the selected extension path.
class HTMLElement extends EventTarget {
  value = '';
  innerHTML = '';
  click() { this.dispatchEvent(new Event('click')); }
}
class HTMLButtonElement extends HTMLElement {}
class HTMLInputElement extends HTMLElement {}
class HTMLTextAreaElement extends HTMLElement {}

const elements = new Map();
const modules = {
  './script': { gradioApp: () => ({ querySelector: (selector) => elements.get(selector) }), onAfterUiUpdate: () => {} },
  './logger': { log: () => {} },
};
const context = vm.createContext({
  window: {},
  HTMLElement,
  HTMLButtonElement,
  HTMLInputElement,
  HTMLTextAreaElement,
  Event,
  require: (name) => modules[name] || {},
});

function loadModule(name) {
  const source = fs.readFileSync(new URL(`../ui/${name}.ts`, import.meta.url), 'utf8');
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } });
  const exported = {};
  context.exports = exported;
  vm.runInContext(`(function(exports, require) { ${compiled.outputText}\n})(exports, require);`, context);
  modules[`./${name}`] = exported;
  return exported;
}

// Execute the real updateInput implementation as well as the extension handlers.
loadModule('ui');
const extensions = loadModule('extensions');
const textarea = new HTMLTextAreaElement();
elements.set('#extension_to_install textarea', textarea);
const events = [];
textarea.addEventListener('input', () => events.push(`input:${textarea.value}`));

for (const action of ['install', 'uninstall', 'update']) {
  const backendButton = new HTMLButtonElement();
  elements.set(`#${action}_extension_button`, backendButton);
  backendButton.addEventListener('click', () => events.push(`click:${textarea.value}`));
  const path = 'extensions/example-extension';
  events.length = 0;
  extensions[`${action}_extension`](new HTMLButtonElement(), path);
  assert.deepEqual(events, [`input:${path}`, `click:${path}`], `${action} must sync the path before triggering its Gradio button`);
}

elements.delete('#update_extension_button');
assert.doesNotThrow(() => extensions.update_extension(new HTMLButtonElement(), 'extensions/missing-button'));
elements.delete('#extension_to_install textarea');
assert.doesNotThrow(() => extensions.update_extension(new HTMLButtonElement(), 'extensions/missing-textbox'));
console.log('Extension button dispatch checks passed');
