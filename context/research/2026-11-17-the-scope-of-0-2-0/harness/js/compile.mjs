import { readFileSync } from "node:fs";
const f = process.argv[2];
const b = readFileSync(f);
const t = performance.now();
try {
  const m = await WebAssembly.compile(b);
  console.log(JSON.stringify({ engine: typeof Bun !== "undefined" ? "bun " + Bun.version : "node " + process.version, compile_ms: Math.round(performance.now() - t), imports: WebAssembly.Module.imports(m).length, rss_mib: Math.round(process.memoryUsage().rss / 2**20) }));
} catch (e) { console.log(JSON.stringify({ engine: typeof Bun !== "undefined" ? "bun " + Bun.version : "node " + process.version, error: String(e).slice(0, 200) })); }
