import { readFileSync } from "node:fs";
import { WASI } from "node:wasi";
const [wasmPath, code, n, imagePath] = process.argv.slice(2);
const isBun = typeof Bun !== "undefined";
let t = performance.now();
const mod = await WebAssembly.compile(readFileSync(wasmPath));
const compile_ms = performance.now() - t;
const image = imagePath ? readFileSync(imagePath) : null;
const times = [];
let out = "";
for (let i = 0; i < Number(n); i++) {
  const t0 = performance.now();
  const wasi = new WASI({ version: "preview1", args: ["python", "-c", code], env: { TMPDIR: "/tmp", PYTHONTZPATH: "", HOME: "/tmp/.home-snapshot" },
    preopens: { "/usr/local/lib": new URL("./lib", import.meta.url).pathname, "/": new URL("./root", import.meta.url).pathname }, returnOnExit: true });
  const inst = await WebAssembly.instantiate(mod, { wasi_snapshot_preview1: wasi.wasiImport, host: { call: () => -1 } });
  if (image) { const mem = inst.exports.memory; const want = image.length / 65536 - mem.buffer.byteLength / 65536; if (want > 0) mem.grow(want); new Uint8Array(mem.buffer).set(image); }
  wasi.initialize ? (() => { try { wasi.initialize(inst); } catch (e) { if (!String(e).includes("_initialize")) throw e; } })() : null;
  let rc;
  try { rc = inst.exports.run(); } catch (e) { rc = "trap: " + String(e).slice(0, 160); }
  times.push(performance.now() - t0);
  if (i === 0) out = String(rc);
}
times.sort((a, b) => a - b);
console.log(JSON.stringify({ engine: isBun ? "bun " + Bun.version : "node " + process.version, compile_ms: Math.round(compile_ms), first_ms: Math.round(times[0] === undefined ? 0 : times[0]), med_ms: Math.round(times[Math.floor(times.length / 2)]), rc: out, rss_peak_mib: Math.round(process.memoryUsage().rss / 2**20) }));
