import test from 'node:test';
import assert from 'node:assert/strict';
import {rankFamily} from '../src/rankings.js';

const entries = values => values.map((richness, i) => ({areaCode: `area${i}`, richness}));

test('ties receive average and dense ranks without mutating input', () => {
  const input = entries([0, 4, 2, 4]);
  const original = structuredClone(input);
  const rows = rankFamily(input);
  assert.deepEqual(input, original);
  assert.deepEqual(rows.map(d => d.rank), [1.5, 1.5, 3, 4]);
  assert.deepEqual(rows.map(d => d.denseRank), [1, 1, 2, 3]);
  assert.deepEqual(rows.map(d => d.tieCount), [2, 2, 1, 1]);
  assert.deepEqual(rows.map(d => d.tieLabel), ['1 (2-way tie)', '1 (2-way tie)', '2', '3']);
  assert.deepEqual(rows.map(d => d.pctAboveAvg), [0.6, 0.6, null, null]);
});

test('all-zero inputs have null percentages and tied ranks', () => {
  const rows = rankFamily(entries([0, 0]));
  assert.deepEqual(rows.map(d => d.pctAboveAvg), [null, null]);
  assert.deepEqual(rows.map(d => d.rank), [1.5, 1.5]);
  assert.deepEqual(rows.map(d => d.denseRank), [1, 1]);
});

test('empty and single-area inputs', () => {
  assert.deepEqual(rankFamily([]), []);
  for (const value of [0, 10]) {
    assert.deepEqual(rankFamily(entries([value])), [{
      areaCode: 'area0', richness: value, rank: 1, denseRank: 1,
      tieCount: 1, tieLabel: '1', pctAboveAvg: value === 0 ? null : 0,
    }]);
  }
});

test('equal positive values are at the mean', () => {
  assert.deepEqual(rankFamily(entries([3, 3, 3])).map(d => d.pctAboveAvg), [0, 0, 0]);
});
