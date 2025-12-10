const { v4: uuidv4 } = require('crypto');

let count = 0;

module.exports = {
  v4: jest.fn(() => `test-uuid-v4-${++count}`),
  v1: jest.fn(() => `test-uuid-v1-${++count}`),
  v3: jest.fn(() => `test-uuid-v3-${++count}`),
  v5: jest.fn(() => `test-uuid-v5-${++count}`),
  validate: jest.fn(() => true),
  version: jest.fn(() => 4),
};