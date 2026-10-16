import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';

// The site renders the reader-facing documentation, which lives at the
// repository root so there is a single source of truth (`README.md`).
const readme = defineCollection({
  loader: glob({ pattern: 'README.md', base: '..' }),
});

export const collections = { readme };
