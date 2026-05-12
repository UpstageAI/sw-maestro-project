import js from "@eslint/js";
import importPlugin from "eslint-plugin-import";
import reactHooks from "eslint-plugin-react-hooks";
import simpleImportSort from "eslint-plugin-simple-import-sort";
import tseslint from "typescript-eslint";

const styleSheetCreateRestriction = {
  selector:
    "CallExpression[callee.object.name='StyleSheet'][callee.property.name='create']",
  message: "Move component styles into a colocated .style.ts file.",
};

export default tseslint.config(
  {
    ignores: [
      ".expo/",
      "babel.config.js",
      "coverage/",
      "node_modules/",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["src/**/*.{ts,tsx}", "App.tsx", "__tests__/**/*.ts"],
    plugins: {
      import: importPlugin,
      "react-hooks": reactHooks,
      "simple-import-sort": simpleImportSort,
    },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "error",

      "@typescript-eslint/consistent-type-imports": [
        "error",
        { prefer: "type-imports" },
      ],
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
        },
      ],

      "array-callback-return": ["error", { checkForEach: true }],
      "import/no-duplicates": "error",
      "max-depth": ["error", 3],
      "max-lines-per-function": [
        "warn",
        {
          max: 100,
          skipBlankLines: true,
          skipComments: true,
        },
      ],
      "no-nested-ternary": "error",
      "no-promise-executor-return": "error",
      "require-atomic-updates": "error",
      "simple-import-sort/exports": "error",
      "simple-import-sort/imports": "error",
    },
  },
  {
    files: ["src/**/*.tsx", "App.tsx"],
    rules: {
      "no-restricted-syntax": ["warn", styleSheetCreateRestriction],
    },
  },
  {
    files: ["src/features/**/*.tsx"],
    rules: {
      "no-restricted-syntax": ["error", styleSheetCreateRestriction],
    },
  },
  {
    files: ["**/*.style.ts"],
    rules: {
      "max-lines-per-function": "off",
    },
  },
  {
    files: ["__tests__/**/*.ts"],
    languageOptions: {
      globals: {
        describe: "readonly",
        expect: "readonly",
        it: "readonly",
        test: "readonly",
      },
    },
  },
);
