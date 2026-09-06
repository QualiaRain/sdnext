AI-authored note:

## Description

The individual extension Update action fills the hidden path input but never invokes the backend button. Its click guard expects HTMLInputElement, while Python creates the target with gr.Button.

Accept HTMLElement, matching the working install and uninstall handlers.

## Notes

Core ESLint, TypeScript checking, and the production build passed. Required bundle/map changes are included. No live server or extension download was performed. Other UI contributions may require regenerating built assets after merging.

Prepared by OpenAI Codex for Jamie (`QualiaRain`) and independently reviewed by a separate Codex agent.

## Environment and Testing

Linux, Node.js. The regression executes real TypeScript UI modules with a minimal DOM. Baseline: path input updates but the backend button receives no click. Fix: install, uninstall, and update each synchronize input before exactly one click; missing controls remain harmless.

Run: `node test/test-extension-update.mjs`.

Core lint, type checks, build, and whitespace checks passed.
