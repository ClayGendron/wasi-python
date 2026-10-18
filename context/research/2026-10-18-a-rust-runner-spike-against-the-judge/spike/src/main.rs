//! wasi-run-spike: a minimal Rust runner for the wasi_python artifact set (research, 2026-10-18).
//!
//! It reads one batch as JSON on stdin: an engine (fuel metering on or off, epoch interruption on
//! or off) and a list of jobs. Each job is one fresh store and instance of a guest module, with
//! its argv, env, folder grants (in the given order, read-only or writable), an optional fuel
//! budget, memory cap and wall-clock deadline. stdout and stderr are captured in memory and then
//! written to the paths the job names. One JSON line per job goes to stdout.
//!
//! Two host modes:
//! - "judge": `random_get` and `clock_time_get` are answered by the host from fixed streams, and
//!   `host::call` answers "no host" (-1). This is what the project's judge driver does
//!   (tests/harness/guest.py), so fuel repeats exactly.
//! - "runner": wasmtime's own WASI answers random and clocks; `host::call` answers -1.
//!
//! Fuel is metered from the end of instantiation: the store runs on an unmetered budget while
//! it instantiates, then gets the job's budget (spec 008's rule).

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::io::Read;
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};
use wasmtime::{
    Caller, Collector, Config, Engine, Linker, Module, Store, StoreLimits, StoreLimitsBuilder, Trap,
};
use wasmtime_wasi::p1::WasiP1Ctx;
use wasmtime_wasi::p2::pipe::MemoryOutputPipe;
use wasmtime_wasi::{FsPerms, I32Exit, WasiCtxBuilder};

const UNMETERED: u64 = (1u64 << 63) - 1;
const NO_HOST: i32 = -1;
const REALTIME_START_NS: u64 = 1_767_225_600_000_000_000; // 2026-01-01T00:00:00Z
const CLOCK_STEP_NS: u64 = 1_000;
const TICK: Duration = Duration::from_millis(10);
const NO_DEADLINE: u64 = 1 << 62;
const P1: &str = "wasi_snapshot_preview1";

#[derive(Deserialize)]
struct Batch {
    consume_fuel: bool,
    epoch_interruption: bool,
    /// "drc" picks the deferred reference-counting collector, which wasmtime-py's C library
    /// uses; absent, the crate's default (with default features: the copying collector).
    #[serde(default)]
    collector: Option<String>,
    jobs: Vec<Job>,
}

#[derive(Deserialize)]
struct Job {
    id: String,
    wasm: PathBuf,
    /// Where the compiled module is cached: read if present, else written after compiling.
    #[serde(default)]
    cwasm: Option<PathBuf>,
    argv: Vec<String>,
    #[serde(default)]
    env: Vec<(String, String)>,
    /// (host folder, guest path, writable), granted in this order.
    #[serde(default)]
    preopens: Vec<(PathBuf, String, bool)>,
    #[serde(default)]
    fuel: Option<u64>,
    #[serde(default)]
    memory_bytes: Option<usize>,
    #[serde(default)]
    deadline_s: Option<f64>,
    /// "judge" or "runner".
    mode: String,
    stdout_path: PathBuf,
    stderr_path: PathBuf,
    /// Only compile (or load) the module, writing `cwasm` if it is named and absent.
    #[serde(default)]
    compile_only: bool,
}

#[derive(Serialize)]
struct Outcome {
    id: String,
    exit_code: Option<i32>,
    trapped: Option<String>,
    trap_cause: Option<String>,
    fuel_used: Option<u64>,
    module_from: &'static str,
    module_ms: f64,
    run_ms: f64,
    stdout_bytes: usize,
    stderr_bytes: usize,
}

struct Host {
    wasi: WasiP1Ctx,
    limits: StoreLimits,
    random_counter: u64,
    ticks: u64,
}

#[derive(Clone, Copy, PartialEq)]
enum Kind {
    Command,
    Reactor,
    Snapshot,
}

fn kind(module: &Module) -> wasmtime::Result<Kind> {
    let names: Vec<&str> = module.exports().map(|e| e.name()).collect();
    let has = |n: &str| names.contains(&n);
    if has("_start") {
        Ok(Kind::Command)
    } else if has("run") && has("_initialize") {
        Ok(Kind::Reactor)
    } else if has("run") {
        Ok(Kind::Snapshot)
    } else {
        wasmtime::bail!("no _start and no run export")
    }
}

/// The judge's random stream: SHA-256 of a little-endian counter, concatenated.
fn take_random(counter: &mut u64, n: usize) -> Vec<u8> {
    let mut out = Vec::with_capacity(n + 32);
    while out.len() < n {
        out.extend_from_slice(&Sha256::digest(counter.to_le_bytes()));
        *counter += 1;
    }
    out.truncate(n);
    out
}

fn memory_write(caller: &mut Caller<'_, Host>, offset: i32, data: &[u8]) -> wasmtime::Result<()> {
    let mem = caller
        .get_export("memory")
        .and_then(|e| e.into_memory())
        .ok_or_else(|| wasmtime::format_err!("guest exports no memory"))?;
    mem.write(caller, offset as u32 as usize, data)?;
    Ok(())
}

fn linker(engine: &Engine, judge: bool) -> wasmtime::Result<Linker<Host>> {
    let mut linker: Linker<Host> = Linker::new(engine);
    wasmtime_wasi::p1::add_to_linker_sync(&mut linker, |h: &mut Host| &mut h.wasi)?;
    linker.allow_shadowing(true);
    if judge {
        linker.func_wrap(
            P1,
            "random_get",
            |mut caller: Caller<'_, Host>, buf: i32, n: i32| -> wasmtime::Result<i32> {
                let data = take_random(&mut caller.data_mut().random_counter, n as u32 as usize);
                memory_write(&mut caller, buf, &data)?;
                Ok(0)
            },
        )?;
        linker.func_wrap(
            P1,
            "clock_time_get",
            |mut caller: Caller<'_, Host>, clock: i32, _precision: i64, out: i32| -> wasmtime::Result<i32> {
                let start = if clock == 0 { REALTIME_START_NS } else { 0 };
                caller.data_mut().ticks += 1;
                let value = start + caller.data().ticks * CLOCK_STEP_NS;
                memory_write(&mut caller, out, &value.to_le_bytes())?;
                Ok(0)
            },
        )?;
    }
    // The door: this spike has no host behind it, so it answers as an embedder with none does.
    linker.func_wrap(
        "host",
        "call",
        |_c: Caller<'_, Host>, _p: i32, _l: i32, _op: i32, _ol: i32| -> i32 { NO_HOST },
    )?;
    Ok(linker)
}

/// The first line of wasmtime's own words, and the line after "Caused by:", as the judge reads
/// them (wasmtime-py's message is the error's Debug form, crates/c-api/src/trap.rs).
fn words(e: &wasmtime::Error) -> (String, Option<String>) {
    let text = format!("{e:?}");
    let lines: Vec<&str> = text.lines().map(str::trim).collect();
    let first = lines.first().copied().unwrap_or("trap").to_string();
    let cause = lines
        .iter()
        .position(|l| *l == "Caused by:")
        .and_then(|i| lines[i + 1..].iter().find(|l| !l.is_empty()))
        .map(|s| s.to_string());
    (first, cause)
}

fn module_for(
    engine: &Engine,
    cache: &mut HashMap<PathBuf, Module>,
    job: &Job,
) -> wasmtime::Result<(Module, &'static str, f64)> {
    let t = Instant::now();
    if let Some(m) = cache.get(&job.wasm) {
        return Ok((m.clone(), "memory", 0.0));
    }
    let (module, from) = match &job.cwasm {
        Some(c) if c.is_file() => {
            // SAFETY: the spike reads only .cwasm files it wrote itself, in its own build folder.
            (unsafe { Module::deserialize_file(engine, c)? }, "cwasm")
        }
        _ => {
            let m = Module::from_file(engine, &job.wasm)?;
            if let Some(c) = &job.cwasm {
                std::fs::write(c, m.serialize()?)?;
            }
            (m, "compiled")
        }
    };
    cache.insert(job.wasm.clone(), module.clone());
    Ok((module, from, t.elapsed().as_secs_f64() * 1e3))
}

fn run_job(engine: &Engine, batch: &Batch, job: &Job, cache: &mut HashMap<PathBuf, Module>) -> wasmtime::Result<Outcome> {
    let (module, module_from, module_ms) = module_for(engine, cache, job)?;
    if job.compile_only {
        return Ok(Outcome {
            id: job.id.clone(),
            exit_code: None,
            trapped: None,
            trap_cause: None,
            fuel_used: None,
            module_from,
            module_ms,
            run_ms: 0.0,
            stdout_bytes: 0,
            stderr_bytes: 0,
        });
    }
    let how = kind(&module)?;
    let judge = match job.mode.as_str() {
        "judge" => true,
        "runner" => false,
        other => wasmtime::bail!("unknown mode {other}"),
    };

    let stdout = MemoryOutputPipe::new(usize::MAX);
    let stderr = MemoryOutputPipe::new(usize::MAX);
    let mut b = WasiCtxBuilder::new();
    b.args(&job.argv);
    b.envs(&job.env);
    for (host, guest, writable) in &job.preopens {
        let perms = if *writable { FsPerms::ReadWrite } else { FsPerms::ReadOnly };
        b.preopened_dir(host, guest, perms)?;
    }
    b.stdout(stdout.clone());
    b.stderr(stderr.clone());
    let mut limits = StoreLimitsBuilder::new();
    if let Some(n) = job.memory_bytes {
        limits = limits.memory_size(n);
    }
    let host = Host { wasi: b.build_p1(), limits: limits.build(), random_counter: 0, ticks: 0 };
    let mut store = Store::new(engine, host);
    store.limiter(|h| &mut h.limits);
    if batch.consume_fuel {
        store.set_fuel(UNMETERED)?;
    }
    let ticks = job.deadline_s.map(|s| ((s / TICK.as_secs_f64()).ceil() as u64).max(1));
    if batch.epoch_interruption {
        store.set_epoch_deadline(ticks.unwrap_or(NO_DEADLINE));
    }
    let linker = linker(engine, judge)?;

    // The epoch ticker: one thread for the job's life, only when it has a deadline.
    let stop = Arc::new(AtomicBool::new(false));
    let ticker = (batch.epoch_interruption && ticks.is_some()).then(|| {
        let (engine, stop) = (engine.clone(), stop.clone());
        std::thread::spawn(move || {
            while !stop.load(Ordering::Relaxed) {
                std::thread::sleep(TICK);
                engine.increment_epoch();
            }
        })
    });

    let t = Instant::now();
    let mut metered = false;
    let budget = job.fuel.unwrap_or(UNMETERED);
    let result: wasmtime::Result<i32> = (|| {
        let instance = linker.instantiate(&mut store, &module)?;
        if batch.consume_fuel {
            store.set_fuel(budget)?;
            metered = true;
        }
        match how {
            Kind::Command => {
                instance.get_typed_func::<(), ()>(&mut store, "_start")?.call(&mut store, ())?;
                Ok(0)
            }
            Kind::Reactor | Kind::Snapshot => {
                if how == Kind::Reactor {
                    instance.get_typed_func::<(), ()>(&mut store, "_initialize")?.call(&mut store, ())?;
                }
                instance.get_typed_func::<(), i32>(&mut store, "run")?.call(&mut store, ())
            }
        }
    })();
    let run_ms = t.elapsed().as_secs_f64() * 1e3;
    stop.store(true, Ordering::Relaxed);
    if let Some(h) = ticker {
        let _ = h.join();
    }

    let (mut exit_code, mut trapped, mut trap_cause) = (None, None, None);
    match result {
        Ok(code) => exit_code = Some(code),
        Err(e) => {
            if let Some(exit) = e.downcast_ref::<I32Exit>() {
                exit_code = Some(exit.0);
            } else if e.downcast_ref::<Trap>() == Some(&Trap::OutOfFuel) {
                trapped = Some("out of fuel".to_string());
            } else if e.downcast_ref::<Trap>() == Some(&Trap::Interrupt) {
                trapped = Some("deadline".to_string());
            } else {
                let (first, cause) = words(&e);
                trapped = Some(first);
                trap_cause = cause;
            }
        }
    }
    let deadline_hit = trapped.as_deref() == Some("deadline");
    let fuel_used = if !batch.consume_fuel || deadline_hit {
        None
    } else if metered {
        Some(budget - store.get_fuel()?)
    } else {
        Some(0)
    };
    drop(store); // the WASI context holds clones of the pipes
    let (out, err) = (stdout.contents(), stderr.contents());
    std::fs::write(&job.stdout_path, &out)?;
    std::fs::write(&job.stderr_path, &err)?;
    Ok(Outcome {
        id: job.id.clone(),
        exit_code,
        trapped,
        trap_cause,
        fuel_used,
        module_from,
        module_ms,
        run_ms,
        stdout_bytes: out.len(),
        stderr_bytes: err.len(),
    })
}

fn main() -> wasmtime::Result<()> {
    let mut input = String::new();
    std::io::stdin().read_to_string(&mut input)?;
    let batch: Batch = serde_json::from_str(&input)?;
    let mut config = Config::new();
    config.consume_fuel(batch.consume_fuel);
    config.epoch_interruption(batch.epoch_interruption);
    match batch.collector.as_deref() {
        None => {}
        Some("drc") => {
            config.collector(Collector::DeferredReferenceCounting);
        }
        Some(other) => wasmtime::bail!("unknown collector {other}"),
    }
    let engine = Engine::new(&config)?;
    let mut cache = HashMap::new();
    for job in &batch.jobs {
        match run_job(&engine, &batch, job, &mut cache) {
            Ok(o) => println!("{}", serde_json::to_string(&o)?),
            Err(e) => println!(
                "{}",
                serde_json::json!({"id": job.id, "error": format!("{e:?}")})
            ),
        }
    }
    Ok(())
}
