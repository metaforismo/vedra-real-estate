import assert from 'node:assert/strict';
import {test} from 'node:test';
import {parseAmount,formatAmount} from '../frontend/src/forms.js';

test('amounts read the way they are written in Italian',()=>{
  assert.equal(parseAmount('586.000'),586000);
  assert.equal(parseAmount('€ 1.250.000'),1250000);
  assert.equal(parseAmount('1.500,50'),1500.5);
  assert.equal(parseAmount('1500.5'),1500.5);
  assert.equal(parseAmount('100000'),100000);
  assert.equal(parseAmount(''),null);
  assert.ok(Number.isNaN(parseAmount('dieci')));
});
test('formatting on blur is stable and keeps cents only when present',()=>{
  assert.equal(formatAmount(586000),'586.000');
  assert.equal(formatAmount(1500.5),'1.500,5');
  assert.equal(formatAmount(parseAmount(formatAmount(1234567))),'1.234.567');
  assert.equal(formatAmount(''),'');
});
