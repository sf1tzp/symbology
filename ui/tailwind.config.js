/** @type {import('tailwindcss').Config} */
import kampsyUI from 'kampsy-ui/preset';
export default {

    presets: [kampsyUI],
    content: [
        './index.html',
        './src/**/*.{js,ts,svelte}',
    ],
    theme: {
        extend: {
            // You can extend Tailwind's default theme here
            // For example, add your custom colors from your existing CSS variables
            colors: {
                'gruvbox': {
                    'green': '#689d6a',
                    'light-green': '#8ec07c',
                    'yellow': '#98971a',
                    'dark0': '#3c3836',
                    'dark2': '#d5c4a1',
                    'light0': '#d4d0c0',
                    'light1': '#e9e5d6',
                    'light3': '#d5c4a1',
                    'red': '#cc241d',
                }
            },
            fontFamily: {
                'sans': ['Inter', 'system-ui', 'Avenir', 'Helvetica', 'Arial', 'sans-serif'],
            }
        },
    },
    plugins: [],
}
