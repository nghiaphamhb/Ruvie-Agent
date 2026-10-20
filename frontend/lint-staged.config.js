import path from 'node:path';
import { fileURLToPath } from 'node:url';

const frontend = fileURLToPath(new URL('.', import.meta.url));
const ignored = new Set(['archive', 'references', 'node_modules', 'dist', 'build', '.svelte-kit']);

// A root-level commit can also contain backend/docs files: keep them out of this hook.
export default (stagedFiles) => {
  const files = stagedFiles
    .map((file) => path.relative(frontend, file).split(path.sep).join('/'))
    .filter((file) => {
      const parts = file.split('/');
      return (
        !path.isAbsolute(file) &&
        parts[0] !== '..' &&
        !parts.some((part) => ignored.has(part.toLowerCase())) &&
        !file.startsWith('.husky/_/') &&
        file !== 'package-lock.json'
      );
    });
  const format = files.filter((file) => /\.(svelte|[cm]?js|ts|css|json|html|md)$/i.test(file));
  const lint = files.filter((file) => /\.(svelte|[cm]?js|ts)$/i.test(file));
  // lint-staged executes commands without a shell; quote filenames for its argument parser.
  const args = (paths) => paths.map((file) => JSON.stringify(file)).join(' ');
  return [
    ...(format.length ? [`prettier --write --ignore-unknown -- ${args(format)}`] : []),
    ...(lint.length ? [`eslint -- ${args(lint)}`] : []),
  ];
};
