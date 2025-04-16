# Symbology UI

This directory contains the frontend UI code for the Symbology project, built with Svelte 5 and TypeScript.

## Configuration Files

### Package Management

- **package.json**: Defines project metadata, dependencies, and npm scripts.
  - Contains development dependencies like Svelte, TypeScript, ESLint, and Prettier.
  - Includes runtime dependencies such as DOMPurify and svelte-routing.
  - Defines scripts for development, building, previewing, and linting.

### TypeScript Configuration

- **tsconfig.json**: Main TypeScript configuration file.
  - Extends the Svelte TypeScript configuration.
  - Configures path aliases for easier imports (`$src`, `$components`, `$utils`).
  - Sets strict type checking options.
  - Includes references to the Node.js-specific TypeScript configuration.

- **tsconfig.node.json**: TypeScript configuration specifically for Node.js environments.
  - Used by the Vite configuration file.
  - Contains settings optimized for the build tools.

### Build Tools

- **vite.config.ts**: Configuration for the Vite build tool.
  - Sets up the Svelte plugin.
  - Configures path aliases for module resolution.
  - Defines development server proxy settings to forward API requests to the backend.

### Svelte Configuration

- **svelte.config.js**: Configuration for the Svelte compiler.
  - Enables Svelte 5 runes mode.

### Code Quality Tools

- **eslint.config.js**: ESLint configuration using the new flat config format.
  - Configures TypeScript and Svelte linting rules.
  - Sets up parser options for Svelte files.
  - Defines global browser variables.
  - Customizes rules for Svelte components.

- **.prettierrc**: Prettier configuration for code formatting.
