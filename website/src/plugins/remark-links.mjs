// Rewrites the relative links found in the Markdown source (the README) so they
// point at the GitHub repository, while leaving absolute URLs and in-page
// anchors untouched.
const GITHUB_BLOB = 'https://github.com/khajavi/praytime/blob/master/';

function walk(node) {
  if (!node || typeof node !== 'object') return;

  if (node.type === 'link' && typeof node.url === 'string') {
    const url = node.url;
    if (!/^(?:[a-z][a-z0-9+.-]*:|\/\/|#)/i.test(url)) {
      node.url = GITHUB_BLOB + url.replace(/^\.\//, '');
    }
  }

  if (Array.isArray(node.children)) {
    for (const child of node.children) walk(child);
  }
}

export default function remarkLinks() {
  return (tree) => walk(tree);
}
