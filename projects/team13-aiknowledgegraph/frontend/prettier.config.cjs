module.exports = {
  semi: true,
  singleQuote: true,
  trailingComma: 'all',
  tabWidth: 2,
  useTabs: false,
  bracketSpacing: true,
  printWidth: 100,
  endOfLine: 'lf',

  plugins: ['@trivago/prettier-plugin-sort-imports'],

  importOrder: ['^react$', '<THIRD_PARTY_MODULES>', '^@(/.*)?$', '^[./]'],
  importOrderSeparation: true,
  importOrderSortSpecifiers: true,
};
