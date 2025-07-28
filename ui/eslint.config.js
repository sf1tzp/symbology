import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import sveltePlugin from 'eslint-plugin-svelte';
import svelteParser from 'svelte-eslint-parser';
import svelteConfig from './svelte.config.js';
export default tseslint.config(
    js.configs.recommended,
    ...tseslint.configs.recommended,
    ...sveltePlugin.configs.recommended,
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
        files: ['**/*.svelte', '**/*.svelte.js', '**/*.svelte.ts'],
        languageOptions: {
            parserOptions: {
                // We recommend importing and specifying svelte.config.js.
                // By doing so, some rules in eslint-plugin-svelte will automatically read the configuration and adjust their behavior accordingly.
                // While certain Svelte settings may be statically loaded from svelte.config.js even if you don’t specify it,
                // explicitly specifying it ensures better compatibility and functionality.
                svelteConfig
            }
        }
    },
    {
        files: ['**/*.svelte', '**/*.svelte.ts'],
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
                document: 'readonly',
                localStorage: 'readonly',
                setTimeout: 'readonly',
                clearTimeout: 'readonly',
                setInterval: 'readonly',
                clearInterval: 'readonly',
                KeyboardEvent: 'readonly',
                navigator: 'readonly'
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
        // FIXME: Fix generated api types to not have `any` fields
        files: ['**/*.d.ts', '**/generated-api-types.ts'],
        rules: {
            '@typescript-eslint/no-explicit-any': 'off'
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