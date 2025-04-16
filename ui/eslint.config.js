import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import sveltePlugin from 'eslint-plugin-svelte';
import svelteParser from 'svelte-eslint-parser';

export default tseslint.config(
    js.configs.recommended,
    ...tseslint.configs.recommended,
    {
        ignores: ['node_modules/**', 'dist/**']
    },
    {
        languageOptions: {
            parserOptions: {
                warnOnUnsupportedTypeScriptVersion: false
            }
        }
    },
    {
        files: ['**/*.svelte'],
        languageOptions: {
            parser: svelteParser,
            parserOptions: {
                parser: tseslint.parser,
                extraFileExtensions: ['.svelte'],
                warnOnUnsupportedTypeScriptVersion: false
            },
            // Add globals for browser environment
            globals: {
                window: 'readonly',
                fetch: 'readonly',
                console: 'readonly',
                CustomEvent: 'readonly',
                document: 'readonly'
            }
        },
        plugins: {
            svelte: sveltePlugin
        },
        rules: {
            ...sveltePlugin.configs.recommended.rules,
            // Disable problematic rules for Svelte components
            'no-inner-declarations': 'off',
            'svelte/no-at-html-tags': 'off' // Since we're using DOMPurify for sanitization
        }
    },
    {
        linterOptions: {
            reportUnusedDisableDirectives: true,
        },
        rules: {
            'no-unused-vars': 'warn',
            'no-console': 'warn'
        }
    }
);