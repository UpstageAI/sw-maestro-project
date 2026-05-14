import eslint from '@eslint/js';
import eslintConfigPrettier from 'eslint-config-prettier/flat';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist', 'node_modules/*', 'prettier.config.cjs', '!src/**/*'] },
  {
    settings: {
      react: {
        version: 'detect',
      },
    },
  },

  // JS / TS Recommended
  eslint.configs.recommended,
  tseslint.configs.recommended,

  // React Recommended + React 17 JSX-Runtime
  react.configs.flat.recommended,
  react.configs.flat['jsx-runtime'],

  // Hooks preset (v5.2.0)
  reactHooks.configs['recommended-latest'],

  // Vite 전용 Fast-Refresh preset
  reactRefresh.configs.vite,

  // 프로젝트 전용(추가) 규칙
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
  },

  // Prettier 충돌 제거
  eslintConfigPrettier,
);
