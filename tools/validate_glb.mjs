// Valida un GLB con gltf-validator (Khronos) y comprueba los requisitos del personaje.
// Uso: node tools/validate_glb.mjs [assets/robin.glb | assets/ignis.glb]
// El perfil sale del nombre del archivo: 'ignis*' añade los requisitos de la boca de Ignis.
import { readFile } from 'node:fs/promises';
import { basename } from 'node:path';
import validator from 'gltf-validator';

const path = process.argv[2] ?? new URL('../assets/robin.glb', import.meta.url).pathname;
const file = basename(path);
const data = new Uint8Array(await readFile(path));
const report = await validator.validateBytes(data, { maxIssues: 200 });
const { numErrors, numWarnings, numInfos, numHints, messages } = report.issues;
for (const m of messages) console.log(`[sev ${m.severity}] ${m.code}: ${m.message} (${m.pointer ?? ''})`);
const info = report.info;
console.log(`errores=${numErrors} avisos=${numWarnings} info=${numInfos} hints=${numHints}`);
console.log(`triangulos=${info.totalTriangleCount} animaciones=${info.animationCount} materiales=${info.materialCount}`);

// requisitos comunes
const json = JSON.parse(new TextDecoder().decode(data.subarray(20, 20 + new DataView(data.buffer).getUint32(12, true))));
const anims = json.animations ?? [];
const req = ['idle', 'talk_1', 'talk_2', 'talk_3'];
const problems = [];
if (numErrors) problems.push('el validador reporta errores');
if (info.totalTriangleCount > 30000) problems.push('mas de 30 000 triangulos');
for (const r of req) if (!anims.some((a) => a.name === r)) problems.push(`falta el clip ${r}`);
if (!json.nodes.some((n) => n.name === 'FaceScreen')) problems.push('falta la malla FaceScreen');
if (!json.materials.some((m) => m.name === 'FaceScreenMat')) problems.push('falta el material FaceScreenMat');
// three.js resuelve las pistas por nombre de nodo y elimina ':' y '.'
const named = json.nodes.map((n) => n.name ?? '');
if (named.some((n) => n.includes(':'))) problems.push('hay nombres de nodo con ":"');
if (named.some((n) => n.includes('.'))) problems.push('hay nombres de nodo con "."');

// requisitos de Ignis: mandibula y shape keys controlados en tiempo de ejecucion
if (file.startsWith('ignis')) {
  const jaw = json.nodes.findIndex((n) => n.name === 'Jaw');
  const joints = new Set((json.skins ?? []).flatMap((s) => s.joints));
  if (jaw < 0 || !joints.has(jaw)) problems.push('falta el hueso Jaw en el skin');
  const targets = (json.meshes ?? []).flatMap((m) => m.extras?.targetNames ?? []);
  for (const k of ['MouthWide', 'MouthRound']) if (!targets.includes(k)) problems.push(`falta el shape key ${k}`);
  for (const a of anims) {
    for (const ch of a.channels) {
      if (ch.target.node === jaw) problems.push(`el clip ${a.name} anima Jaw (${ch.target.path})`);
      if (ch.target.path === 'weights') problems.push(`el clip ${a.name} anima shape keys`);
    }
  }
  const ds = (json.materials ?? []).filter((m) => m.doubleSided).map((m) => m.name);
  console.log(`doble cara: ${ds.join(', ') || 'ninguno'} · shape keys: ${targets.join(', ')}`);
}
console.log(problems.length ? `FALLA: ${[...new Set(problems)].join('; ')}` : `OK: ${file} cumple los requisitos`);
process.exit(problems.length ? 1 : 0);
