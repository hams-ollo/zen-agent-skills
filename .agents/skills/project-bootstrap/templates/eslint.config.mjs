// House eslint flat config for project-bootstrap (optional, JS/TS only).
//
// Emitted into the target repo as eslint.config.mjs. Minimal by design: it turns on
// eslint's recommended rules and defers all formatting to prettier (see prettierrc.json),
// so the two never fight. This is configs-only: the skill does NOT install eslint or any
// plugin; it surfaces `npm install -D eslint` (and, for TS, `typescript-eslint`) for the
// user to run. An existing eslint config in the target repo is never overwritten.
//
// For TypeScript, add typescript-eslint:
//   import tseslint from 'typescript-eslint';
//   export default [js.configs.recommended, ...tseslint.configs.recommended];

import js from '@eslint/js';

export default [
  js.configs.recommended,
  {
    linterOptions: {
      reportUnusedDisableDirectives: true,
    },
  },
];
