import { defineConfig } from 'vitest/config';

// Vitest 4.x + Node 22: running test files concurrently accumulates IPC listeners
// on shared ChildProcess objects, exceeding Node's default limit of 10.
// Sequential execution (fileParallelism: false) caps concurrent listeners to 3.
export default defineConfig({
  test: {
    globals: true,
    fileParallelism: false,
  },
});
