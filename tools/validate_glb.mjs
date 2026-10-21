// Valida un GLB con gltf-validator (Khronos) y comprueba los requisitos de Robin.
// Uso: node tools/validate_glb.mjs [assets/robin.glb]
import { readFile } from 'node:fs/promises';
import validator from 'gltf-validator';

const path = process.argv[2] ?? new URL('../assets/robin.glb', import.meta.url).pathname;
const data = new Uint8Array(await readFile(path));
const report = await validator.validateBytes(data, { maxIssues: 200 });
const { numErrors, numWarnings, numInfos, numHints, messages } = report.issues;
for (const m of messages) console.log(`[sev ${m.severity}] ${m.code}: ${m.message} (${m.pointer ?? ''})`);
const info = report.info;
console.log(`errores=${numErrors} avisos=${numWarnings} info=${numInfos} hints=${numHints}`);
console.log(`triangulos=${info.totalTriangleCount} animaciones=${info.animationCount} materiales=${info.materialCount}`);

// requisitos propios
const json = JSON.parse(new TextDecoder().decode(data.subarray(20, 20 + new DataView(data.buffer).getUint32(12, true))));
const anims = (json.animations ?? []).map((a) => a.name);
const req = ['idle', 'talk_1', 'talk_2', 'talk_3'];
const problems = [];
if (numErrors) problems.push('el validador reporta errores');
if (info.totalTriangleCount > 30000) problems.push('mas de 30 000 triangulos');
for (const r of req) if (!anims.includes(r)) problems.push(`falta el clip ${r}`);
if (!json.nodes.some((n) => n.name === 'FaceScreen')) problems.push('falta la malla FaceScreen');
if (!json.materials.some((m) => m.name === 'FaceScreenMat')) problems.push('falta el material FaceScreenMat');
if (json.nodes.some((n) => n.name.includes(':'))) problems.push('hay nombres de nodo con ":"');
console.log(problems.length ? `FALLA: ${problems.join('; ')}` : 'OK: robin.glb cumple los requisitos');
process.exit(problems.length ? 1 : 0);
