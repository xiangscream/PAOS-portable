#!/usr/bin/env node

import { readFile, readdir, stat } from 'node:fs/promises';
import { resolve, relative, extname } from 'node:path';

const projectRoot = resolve(process.argv[2] ?? process.cwd());
const requestedSlideDir = process.argv[3] ? resolve(projectRoot, process.argv[3]) : null;

async function exists(path) {
  try {
    await stat(path);
    return true;
  } catch {
    return false;
  }
}

async function walk(dir, result = []) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    if (['node_modules', 'dist', '.git'].includes(entry.name)) continue;
    const full = resolve(dir, entry.name);
    if (entry.isDirectory()) await walk(full, result);
    else result.push(full);
  }
  return result;
}

const allFiles = await walk(projectRoot);
const sourceFiles = allFiles.filter((file) => ['.tsx', '.ts', '.jsx', '.js'].includes(extname(file)));
const candidateFiles = requestedSlideDir
  ? sourceFiles.filter((file) => file.startsWith(requestedSlideDir))
  : sourceFiles.filter((file) => /slides?|pages?|notes|theme/i.test(relative(projectRoot, file)));

const packagePath = resolve(projectRoot, 'package.json');
let scripts = {};
if (await exists(packagePath)) {
  const pkg = JSON.parse(await readFile(packagePath, 'utf8'));
  scripts = pkg.scripts ?? {};
}

const scenes = [];
const warnings = [];
const stableIds = [];
let noteLiterals = 0;

for (const file of candidateFiles) {
  const source = await readFile(file, 'utf8');
  const rel = relative(projectRoot, file);

  for (const match of source.matchAll(/export\s+const\s+Scene(\d+)/g)) {
    scenes.push({ id: match[1], file: rel });
  }
  noteLiterals += (source.match(/【第\d+页/g) ?? []).length;

  for (const match of source.matchAll(/data-(?:node|slide)-id\s*=\s*["']([^"']+)["']/g)) {
    stableIds.push({ id: match[1], file: rel });
  }

  source.split(/\r?\n/).forEach((line, index) => {
    const jsxCount = (line.match(/<[A-Z_a-z][^>]*>/g) ?? []).length;
    if ((line.length > 500 && jsxCount > 0) || jsxCount >= 4) {
      warnings.push({
        type: 'compressed-jsx',
        file: rel,
        line: index + 1,
        detail: `${line.length} chars, ${jsxCount} JSX openings`,
      });
    }
    if (/\.map\s*\(/.test(line) && /<\w/.test(line)) {
      warnings.push({
        type: 'repeated-callsite',
        file: rel,
        line: index + 1,
        detail: 'map-generated JSX may be ambiguous for source-patching Inspectors',
      });
    }
    if (/style=\{\{\s*\.\.\./.test(line)) {
      warnings.push({
        type: 'spread-style',
        file: rel,
        line: index + 1,
        detail: 'computed style spreads are harder to patch safely',
      });
    }
  });
}

const sceneCounts = new Map();
for (const scene of scenes) sceneCounts.set(scene.id, (sceneCounts.get(scene.id) ?? 0) + 1);
const duplicateScenes = [...sceneCounts].filter(([, count]) => count > 1).map(([id]) => id);

const idCounts = new Map();
for (const item of stableIds) idCounts.set(item.id, (idCounts.get(item.id) ?? 0) + 1);
const duplicateStableIds = [...idCounts].filter(([, count]) => count > 1).map(([id]) => id);

const report = {
  projectRoot,
  slideScope: requestedSlideDir ?? 'heuristic project scan',
  scripts: {
    dev: scripts.dev ?? null,
    validate: scripts.validate ?? scripts['validate:v2'] ?? null,
    build: scripts.build ?? null,
    preview: scripts.preview ?? null,
  },
  scenes: {
    count: scenes.length,
    ids: scenes.map((scene) => scene.id),
    duplicateIds: duplicateScenes,
  },
  notes: {
    headingOccurrences: noteLiterals,
  },
  editorReadiness: {
    stableIdOccurrences: stableIds.length,
    duplicateStableIds,
    sourcePatchWarnings: warnings.length,
  },
  warningSample: warnings.slice(0, 40),
};

console.log(JSON.stringify(report, null, 2));
