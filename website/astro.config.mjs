// @ts-check
import { defineConfig } from 'astro/config';
import remarkGithubBlockquoteAlert from 'remark-github-blockquote-alert';

import remarkLinks from './src/plugins/remark-links.mjs';

// Single-page documentation site for the `praytime` Python package, deployed to
// GitHub Pages. Because the account has a custom Pages domain, project sites are
// served under it; update `site`/`base` if you host it elsewhere (a dedicated
// custom domain needs `base: '/'`).
export default defineConfig({
  site: 'https://blog.khajavi.ir',
  base: '/praytime',
  markdown: {
    remarkPlugins: [remarkGithubBlockquoteAlert, remarkLinks],
  },
});
