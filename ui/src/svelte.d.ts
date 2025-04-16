// This is a special type declaration file (.d.ts) that tells TypeScript how to handle Svelte component imports. Here's what each part does:

// declare module '*.svelte' - This creates a module declaration for any file ending in .svelte
// const component: ComponentType<any> - This declares that each Svelte file exports a component that matches Svelte's ComponentType interface. The any type parameter represents the props that the component accepts.
// export default component - This tells TypeScript that Svelte files export their component as the default export.
// Yes, you do need to export a default component here because this is how Svelte components are typically imported and used in TypeScript projects. When you write code like:
//
// import MyComponent from './MyComponent.svelte';
//

// TypeScript uses this declaration file to understand that MyComponent will be a Svelte component.

// The any type is used here because this is a global declaration that needs to work with any Svelte component, regardless of what props it accepts. While the ESLint rule is complaining about it, this is actually one of the rare cases where using any is acceptable because:

// It's in a type declaration file
// It needs to work with all possible prop types
// It's specifically for module augmentation
declare module '*.svelte' {
  import type { ComponentType } from 'svelte';
  const component: ComponentType<any>;
  export default component;
}
