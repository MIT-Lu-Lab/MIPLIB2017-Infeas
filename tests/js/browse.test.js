'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {rowMatches} = require('../../website/assets/browse.js');

const row = {
  values: {instance: 'Example-Instance'},
  matches: new Set(['vars-lt50k', 'cons-lt10k', 'tag-network']),
};

test('filter groups are OR within a facet and AND across facets', () => {
  assert.equal(rowMatches(row, [
    ['vars-gt500k', 'vars-lt50k'],
    ['cons-lt10k'],
  ], ''), true);
  assert.equal(rowMatches(row, [
    ['vars-gt500k'],
    ['cons-lt10k'],
  ], ''), false);
});

test('name search is case-normalised before the pure matcher', () => {
  assert.equal(rowMatches(row, [], 'example'), true);
  assert.equal(rowMatches(row, [], 'missing'), false);
});
