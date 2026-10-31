// Meaningful lifecycle/fault tests for the built plugin, using Node's test runner.
// The real DSH renderer is tested separately; this does not pretend to emulate it.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../dist/dsh-skin-local/lib/client.js', import.meta.url), 'utf8');

function environment({ reduced = false, failure, noBody = false } = {}) {
  const nodes = new Set(), timers = new Map(), layers = new Set(), warnings = [];
  let nextTimer = 0;
  class Element {
    constructor(tag) { this.tag = tag; this.attrs = new Map(); this.children = []; this.style = {}; }
    setAttribute(k, v) { this.attrs.set(k, v); }
    getAttribute(k) { return this.attrs.has(k) ? this.attrs.get(k) : null; }
    removeAttribute(k) { this.attrs.delete(k); }
    appendChild(el) {
      if (failure === 'stylesheet' && el.tag === 'style') throw Error('Simulated style insertion failure');
      if (failure === 'intro' && el.className === 'dsh-ef-intro') throw Error('Simulated overlay insertion failure');
      this.children.push(el); el.parent = this; nodes.add(el); return el;
    }
    remove() {
      this.parent?.children.splice(this.parent.children.indexOf(this), 1);
      nodes.delete(this);
      for (const child of [...this.children]) child.remove();
    }
  }
  const document = {
    head: new Element('head'), body: noBody ? null : new Element('body'),
    createElement: (tag) => new Element(tag),
    getElementById: (id) => [...nodes].find(n => n.id === id),
  };
  let module;
  const window = {
    __ModuleLoader__: { load: (value) => { module = value; } },
    matchMedia: () => ({ matches: reduced }),
    setTimeout: (fn, ms) => { timers.set(++nextTimer, {fn,ms}); return nextTimer; },
    clearTimeout: (id) => timers.delete(id),
  };
  vm.runInNewContext(source, { window, document, console: { warn: (...a) => warnings.push(a) } });
  const ctx = {
    theme: { overrideTokens: (name, tokens) => {
      if (failure === 'theme') throw Error('Simulated unavailable theme runtime');
      assert.equal(name, 'dsh-skin-local');
      assert.ok(Object.keys(tokens).length > 0);
      const layer = { tokens }; layers.add(layer);
      return () => layers.delete(layer);
    } },
    effect: (effect) => { const cleanup = effect(); if (typeof cleanup === 'function') cleanups.push(cleanup); },
  };
  const cleanups = [];
  return { ctx, document, nodes, timers, layers, warnings,
    load: () => module.factory().apply(ctx),
    dispose: () => { for (const fn of cleanups.splice(0).reverse()) fn(); },
    tick: () => { for (const { fn } of [...timers.values()]) fn(); },
  };
}

test('normal load: exactly one layer/style; startup is inert and self-removes within 1s', () => {
  const e = environment(); e.load();
  assert.equal(e.layers.size, 1);
  assert.equal(e.document.head.children.length, 1);
  const intro = e.document.body.children[0];
  assert.equal(intro.getAttribute('aria-hidden'), 'true');
  assert.match(intro.style.cssText, /position:fixed/);
  assert.match(intro.style.cssText, /pointer-events:none/);
  assert.equal(intro.children[0].children.map(n => n.textContent).join(' '), 'DEEPSEEK HARNESS');
  assert.ok([...e.timers.values()].every(t => t.ms <= 1000));
  e.tick();
  assert.equal(e.document.body.children.length, 0);
  assert.equal(e.timers.size, 0);
  assert.equal(e.layers.size, 1);
  e.dispose();
  assert.equal(e.nodes.size, 0);
  assert.equal(e.layers.size, 0);
  assert.equal(e.document.body.getAttribute('data-dsh-endfield-skin'), null);
});

test('unload during startup cancels timers and removes every owned effect', () => {
  const e = environment(); e.load(); e.dispose(); e.dispose(); e.tick();
  assert.equal(e.timers.size, 0); assert.equal(e.nodes.size, 0); assert.equal(e.layers.size, 0);
});

test('100 load/unload cycles and duplicate factories do not accumulate styles or layers', () => {
  const e = environment();
  for (let i = 0; i < 100; i++) {
    e.load(); e.load();
    assert.equal(e.layers.size, 1); assert.equal(e.document.head.children.length, 1);
    assert.equal(e.timers.size, 1);
    e.dispose();
    assert.equal(e.layers.size, 0); assert.equal(e.nodes.size, 0); assert.equal(e.timers.size, 0);
  }
});

test('reduced motion skips the overlay and all startup timers', () => {
  const e = environment({reduced:true}); e.load();
  assert.equal(e.layers.size, 1); assert.equal(e.timers.size, 0); assert.equal(e.document.body.children.length, 0);
  e.dispose();
});

for (const failure of ['theme','stylesheet','intro']) {
  test(`${failure} failure restores original state without escaping into DSH`, () => {
    const e = environment({failure});
    e.document.body.setAttribute('data-dsh-endfield-skin', 'previous-owner');
    assert.doesNotThrow(e.load);
    assert.equal(e.layers.size, 0); assert.equal(e.nodes.size, 0); assert.equal(e.timers.size, 0);
    assert.equal(e.document.body.getAttribute('data-dsh-endfield-skin'), 'previous-owner');
    assert.equal(e.warnings.length, 1);
    assert.doesNotThrow(e.dispose);
  });
}

test('missing body or missing theme service leaves DSH untouched', () => {
  const e = environment({noBody:true}); assert.doesNotThrow(e.load); assert.equal(e.layers.size, 0);
  const other = environment(); other.ctx.theme = undefined; assert.doesNotThrow(other.load);
  assert.equal(other.nodes.size, 0); assert.equal(other.timers.size, 0);
});
