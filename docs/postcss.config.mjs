/** Tailwind v4 runs as a PostCSS plugin; without this file Next emits the
 * raw `@theme` blocks and no utility classes at all. */
export default {
  plugins: {
    '@tailwindcss/postcss': {},
  },
};
