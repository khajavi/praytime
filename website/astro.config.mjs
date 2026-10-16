// @ts-check
import { defineConfig } from 'astro/config';
import remarkGithubBlockquoteAlert from 'remark-github-blockquote-alert';

import remarkLinks from './src/plugins/remark-links.mjs';

// Single-page documentation site for the `praytime` Python package, deployed to
// GitHub Pages at https://khajavi.github.io/praytime/.
//
// Change `site`/`base` if you host it elsewhere (a dedicated custom domain needs
// `base: '/'`).
export default defineConfig({
  site: 'https://khajavi.github.io',
  base: '/praytime',
  markdown: {
    remarkPlugins: [remarkGithubBlockquoteAlert, remarkLinks],
  },
});
