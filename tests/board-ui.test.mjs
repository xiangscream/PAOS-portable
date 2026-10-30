import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const html = readFileSync(new URL('../front/index.html', import.meta.url), 'utf8');
function helper(name) {
  const line = html.split('\n').find(row => row.startsWith(`function ${name}(`));
  assert.ok(line, `${name} is present in the shipped page`);
  return vm.runInNewContext(`(${line})`);
}

test('TODO, Mail and CAT text preserve ampersands and angle brackets', () => {
  assert.equal(helper('esc')('A & B <正文>'), 'A &amp; B &lt;正文&gt;');
});
test('existing entity text is displayed literally', () => {
  assert.equal(helper('esc')('&amp;'), '&amp;amp;');
});
test('explicit unknown outcome cannot be blindly resubmitted', () => {
  assert.equal(helper('retryAllowed')({ retry: false }), false);
});
test('ordinary rejection can be corrected and submitted again', () => {
  assert.equal(helper('retryAllowed')({ retry: true }), true);
  assert.equal(helper('retryAllowed')({}), true);
});
