// Research benchmark (2026-11-17): what a Rust host costs for the wasi_python 0.1.4 artifact set.
use std::path::Path;
use std::time::Instant;
use wasmtime::*;
use wasmtime_wasi::p1::WasiP1Ctx;
use wasmtime_wasi::p2::pipe::MemoryOutputPipe;
use wasmtime_wasi::{FsPerms, WasiCtxBuilder};

struct Host { wasi: WasiP1Ctx, limits: StoreLimits }

fn ms(t: Instant) -> f64 { t.elapsed().as_secs_f64() * 1e3 }
fn rss_mib() -> f64 {
    let s = std::fs::read_to_string("/proc/self/status").unwrap();
    for l in s.lines() { if l.starts_with("VmHWM:") { return l.split_whitespace().nth(1).unwrap().parse::<f64>().unwrap() / 1024.0; } }
    0.0
}
fn rss_now() -> f64 {
    let s = std::fs::read_to_string("/proc/self/status").unwrap();
    for l in s.lines() { if l.starts_with(std::env::var("RSSKEY").as_deref().unwrap_or("VmRSS:")) { return l.split_whitespace().nth(1).unwrap().parse::<f64>().unwrap() / 1024.0; } }
    0.0
}
fn median(mut v: Vec<f64>) -> f64 { v.sort_by(|a, b| a.partial_cmp(b).unwrap()); v[v.len() / 2] }

fn config(fuel: bool, pooling: bool) -> Config {
    let mut c = Config::new();
    c.consume_fuel(fuel);
    c.epoch_interruption(true);
    c.async_stack_size(16 << 20);
    c.max_wasm_stack(8 << 20);
    if std::env::var_os("NO_UNWIND").is_some() { c.native_unwind_info(false); }
    if std::env::var_os("OPT0").is_some() { c.cranelift_opt_level(OptLevel::None); }
    if pooling {
        let mut p = PoolingAllocationConfig::new();
        p.total_memories(200);
        p.total_tables(200);
        p.table_elements(100_000);
        p.max_core_instance_size(4 << 20);
        p.total_core_instances(200);
        p.max_memory_size(4 << 30);
        p.max_unused_warm_slots(50);
        c.allocation_strategy(InstanceAllocationStrategy::Pooling(p));
    }
    c
}

/// Rewrite the snapshot binary so its data section is the image: one active segment per run of
/// non-zero 64 KiB pages, memory minimum = image pages. wasmtime then maps it copy-on-write.
fn cowify(wasm: &Path, image: &Path, out: &Path) -> Result<()> {
    let bytes = std::fs::read(wasm)?;
    let img = std::fs::read(image)?;
    let pages = (img.len() / 65536) as u64;
    let mut segs: Vec<(usize, usize)> = vec![];
    let mut i = 0;
    while i < img.len() {
        let page = &img[i..i + 65536];
        if page.iter().all(|&b| b == 0) { i += 65536; continue; }
        let start = i;
        while i < img.len() && !img[i..i + 65536].iter().all(|&b| b == 0) { i += 65536; }
        segs.push((start, i));
    }
    let mut m = wasm_encoder::Module::new();
    for p in wasmparser::Parser::new(0).parse_all(&bytes) {
        let p = p?;
        match &p {
            wasmparser::Payload::MemorySection(r) => {
                let mut ms = wasm_encoder::MemorySection::new();
                for mem in r.clone() { let mem = mem?;
                    ms.memory(wasm_encoder::MemoryType { minimum: pages.max(mem.initial), maximum: mem.maximum, memory64: mem.memory64, shared: mem.shared, page_size_log2: None }); }
                m.section(&ms);
            }
            wasmparser::Payload::DataCountSection { .. } => { m.section(&wasm_encoder::DataCountSection { count: segs.len() as u32 }); }
            wasmparser::Payload::DataSection(_) => {
                let mut ds = wasm_encoder::DataSection::new();
                for (a, b) in &segs { ds.active(0, &wasm_encoder::ConstExpr::i32_const(*a as i32), img[*a..*b].iter().copied()); }
                m.section(&ds);
            }
            wasmparser::Payload::CodeSectionEntry(_) | wasmparser::Payload::Version { .. } | wasmparser::Payload::End(_) => {}
            other => {
                if let Some((id, range)) = other.as_section() {
                    m.section(&wasm_encoder::RawSection { id, data: &bytes[range.start as usize..range.end as usize] });
                }
            }
        }
    }
    let data = m.finish();
    std::fs::write(out, &data)?;
    let nz: usize = segs.iter().map(|(a, b)| b - a).sum();
    println!("{{\"cow_wasm_bytes\":{},\"segments\":{},\"nonzero_bytes\":{},\"image_pages\":{}}}", data.len(), segs.len(), nz, pages);
    Ok(())
}

fn store(engine: &Engine, lib: &Path, root: &Path, code: &str, mem: usize, out: &MemoryOutputPipe, err: &MemoryOutputPipe) -> Result<Store<Host>> {
    let mut b = WasiCtxBuilder::new();
    b.args(&["python", "-c", code]);
    b.envs(&[("TMPDIR", "/tmp"), ("PYTHONTZPATH", ""), ("HOME", "/tmp/.home-snapshot")]);
    b.preopened_dir(lib, "/usr/local/lib", FsPerms::ReadOnly)?;
    b.preopened_dir(root, "/", FsPerms::ReadWrite)?;
    b.stdout(out.clone()); b.stderr(err.clone());
    let limits = StoreLimitsBuilder::new().memory_size(mem).build();
    let mut s = Store::new(engine, Host { wasi: b.build_p1(), limits });
    s.limiter(|h| &mut h.limits);
    s.set_epoch_deadline(1 << 40);
    if engine.config_has_fuel() { s.set_fuel(u64::MAX / 2)?; }
    Ok(s)
}

trait HasFuel { fn config_has_fuel(&self) -> bool; }
impl HasFuel for Engine { fn config_has_fuel(&self) -> bool { std::env::var_os("FUEL").is_some() } }

fn main() -> Result<()> {
    std::thread::Builder::new().stack_size(64 << 20).spawn(real_main).unwrap().join().unwrap()
}

fn real_main() -> Result<()> {
    let a: Vec<String> = std::env::args().collect();
    match a[1].as_str() {
        "cowify" => return cowify(Path::new(&a[2]), Path::new(&a[3]), Path::new(&a[4])),
        "compile" => {
            let engine = Engine::new(&config(std::env::var_os("FUEL").is_some(), false))?;
            let t = Instant::now();
            let m = Module::from_file(&engine, &a[2])?;
            let c = ms(t);
            let ser = m.serialize()?;
            std::fs::write(&a[3], &ser)?;
            println!("{{\"compile_ms\":{c:.0},\"cwasm_bytes\":{},\"rss_peak_mib\":{:.0}}}", ser.len(), rss_mib());
        }
        "bench" => {
            // bench <cwasm> <libdir> <rootdir> <pooling|ondemand> <image|-> <code> <n> [keep]
            let pooling = a[5] == "pooling";
            let engine = Engine::new(&config(std::env::var_os("FUEL").is_some(), pooling))?;
            let t = Instant::now();
            let module = unsafe { Module::deserialize_file(&engine, &a[2])? };
            let load_ms = ms(t);
            let mut linker: Linker<Host> = Linker::new(&engine);
            wasmtime_wasi::p1::add_to_linker_sync(&mut linker, |h: &mut Host| &mut h.wasi)?;
            linker.func_wrap("host", "call", |_c: Caller<'_, Host>, _p: i32, _l: i32, _op: i32, _ol: i32| -> i32 { -1 })?;
            let t = Instant::now();
            let pre = linker.instantiate_pre(&module)?;
            let pre_ms = ms(t);
            let image = if a[6] == "-" { None } else { Some(std::fs::read(&a[6])?) };
            let code = &a[7];
            let n: usize = a[8].parse()?;
            let keep = a.get(9).map(|s| s == "keep").unwrap_or(false);
            let (lib, root) = (Path::new(&a[3]), Path::new(&a[4]));
            let (mut inst_v, mut rest_v, mut run_v, mut drop_v, mut total_v, mut fuel_v) = (vec![], vec![], vec![], vec![], vec![], vec![]);
            let mut kept = vec![];
            let rss0 = rss_now();
            let mut last_out = String::new();
            for _ in 0..n {
                let (out, err) = (MemoryOutputPipe::new(1 << 20), MemoryOutputPipe::new(1 << 20));
                let t0 = Instant::now();
                let mut s = store(&engine, lib, root, code, 4 << 30, &out, &err)?;
                let inst = pre.instantiate(&mut s)?;
                inst_v.push(ms(t0));
                let t1 = Instant::now();
                if let Some(img) = &image {
                    let mem = inst.get_memory(&mut s, "memory").unwrap();
                    let have = mem.size(&s);
                    let want = (img.len() / 65536) as u64;
                    if want > have { mem.grow(&mut s, want - have)?; }
                    if std::env::var_os("MMAP").is_some() {
                        // Map the image file over linear memory, private and copy-on-write.
                        use std::os::fd::AsRawFd;
                        let f = std::fs::File::open(&a[6])?;
                        let base = mem.data_ptr(&s) as *mut libc::c_void;
                        let r = unsafe { libc::mmap(base, img.len(), libc::PROT_READ | libc::PROT_WRITE, libc::MAP_PRIVATE | libc::MAP_FIXED, f.as_raw_fd(), 0) };
                        assert!(r == base, "mmap failed");
                    } else {
                        mem.data_mut(&mut s)[..img.len()].copy_from_slice(img);
                    }
                }
                rest_v.push(ms(t1));
                let t2 = Instant::now();
                let run = inst.get_typed_func::<(), i32>(&mut s, "run")?;
                let r = run.call(&mut s, ());
                run_v.push(ms(t2));
                if std::env::var_os("FUEL").is_some() { fuel_v.push((u64::MAX / 2 - s.get_fuel()?) as f64); }
                if let Err(e) = &r { if e.downcast_ref::<wasmtime_wasi::I32Exit>().is_none() { eprintln!("trap: {e:?}"); } }
                let t3 = Instant::now();
                if keep { kept.push(s); } else { drop(s); }
                drop_v.push(ms(t3));
                total_v.push(ms(t0));
                last_out = String::from_utf8_lossy(&out.contents()).to_string() + &String::from_utf8_lossy(&err.contents());
            }
            let rss1 = rss_now();
            println!("{{\"load_ms\":{load_ms:.1},\"instance_pre_ms\":{pre_ms:.2},\"instantiate_med_ms\":{:.3},\"restore_med_ms\":{:.2},\"run_med_ms\":{:.2},\"drop_med_ms\":{:.2},\"total_med_ms\":{:.2},\"total_first_ms\":{:.2},\"fuel_med\":{:.0},\"rss_delta_per_kept_mib\":{:.1},\"rss_peak_mib\":{:.0},\"out\":{:?}}}",
                median(inst_v), median(rest_v), median(run_v), median(drop_v), median(total_v.clone()), total_v[0],
                if fuel_v.is_empty() { 0.0 } else { median(fuel_v) }, if keep { (rss1 - rss0) / n as f64 } else { 0.0 }, rss_mib(), last_out.chars().take(200).collect::<String>());
        }
        _ => panic!("mode"),
    }
    Ok(())
}
