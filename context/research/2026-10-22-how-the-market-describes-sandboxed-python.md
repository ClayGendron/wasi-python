# How the market describes sandboxed Python

- **Status:** research, 2026-10-22. It feeds the README rewrite. It commits the project to nothing and writes none of the README; the choices are in section 7.
- **Owner:** Clay Gendron
- **Researcher:** a market-research agent (Claude Opus). It wrote none of the code or the documents it reads. Box: about 60 minutes. Nothing was executed and nothing was downloaded; only web pages were read.
- **The question:** how does the market for running untrusted or AI-generated Python talk about itself, what do buyers want, and where is wasi-python truly different, so the owner can write a README headline that is direct and true?

It extends `2026-10-17-market-research-use-cases.md` (the earlier memo) and does not repeat it. Prices, the Pyodide failures and the adjacent markets are there.

## Method and labels

- **READ** is a claim taken from a public page, with its link. Vendor numbers are vendor claims.
- **READ (repo)** is a fact from this repository, with its path.
- **INFERRED** is the researcher's reasoning. Every judgement of "unique", "competitive" or "behind" is INFERRED from the READ facts beside it.
- **SNIPPET** marks a fact seen only in a search engine's summary, not on the page itself.
- Headlines were read from each product's landing page or README on 2026-10-22. Some pages are rendered by script, so a quoted line may be the page's lead sentence rather than its banner.

Terms. A **sandbox** is the wall around code you do not trust. **In-process** means the sandboxed code runs inside your own program, as a library call: no VM, no container, no second process, no service. **Code mode** (also "programmatic tool calling") means a model writes one program that calls your tools, instead of calling them one by one. A **headline** is the first sentence a buyer reads.

## 0. What changed in five days

In the project (READ (repo): `docs/reference/packages.md`, `CHANGELOG.md`, the docs tree):

- scipy 1.18.1, scikit-learn 1.9.1, statsmodels 0.15.0, matplotlib 3.11.2, lxml 6.1.3, regex and about 40 pure-Python packages (openpyxl, xlsxwriter, pypdf, reportlab, seaborn, sympy, networkx, jinja2, bs4, pyyaml, ...) joined numpy and pandas. On 2026-10-17 only numpy and pandas were in.
- Every gap the earlier memo listed for "code mode with pandas" (its Proposal A) now exists: tools with a JSON protocol and MCP-style hints (`docs/how-to/tools.md`), bounded sessions (`docs/explanation/sessions.md`), mounts, `run_async`, matplotlib to PNG, and the `wasi-python run` JSON command.
- Each package's own upstream test suite now runs inside the guest before a release (README, "What runs").
- The project published its own advisory, GHSA-w99p-2jv3-fvj6, and yanked 0.1.0a3 (commit `2f218a29`). The runner carries two wasmtime fixes itself (`docs/explanation/security-model.md`).
- PyPI still shows 0.1.0a7 as a pre-release, with the summary "A statically linked CPython for WebAssembly hosts (wasm32-wasip1) with numpy, pandas and matplotlib compiled in." (READ, [PyPI](https://pypi.org/project/wasi-python/)). 0.1.0 is unreleased (`CHANGELOG.md`).

In the market (READ; some items predate 2026-10-17 but were not in the earlier memo):

- Pydantic now sells **Full Monty**, "the same `monty` workers behind a WebSocket, as a container image", and plans Monty V1 "with a stable API" after its third bounty round ([alternatives](https://pydantic.dev/docs/monty/reference/alternatives/), [hack-monty-3](https://pydantic.dev/articles/hack-monty-3)). Its **Logfire sandboxes** (2026-07-15) put Modal and Monty behind one interface ([article](https://pydantic.dev/articles/logfire-sandboxes)).
- Anthropic's code execution tool gained REPL state persistence and programmatic tool calling, and is now free when used with web search or web fetch ([docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool)).
- The hosted field is now at least 15 providers (Upstash, 2026-09-17, [comparison](https://upstash.com/blog/ai-agent-sandbox-providers-compared-2026)).
- Two public voices say a WASI Python with pandas cannot exist or is too slow (section 3.2). That belief is the README's opening.

## 1. The landscape in October 2026

Shape: **S** service (hosted VMs or containers), **L** library (in your process), **R** runtime or platform. Start times are the vendor's claim unless marked.

| product | shape | isolation | Python data stack, and how | start claim | price shape | headline (quoted) | URL |
|---|---|---|---|---|---|---|---|
| E2B | S | Firecracker microVM | numpy, pandas, scipy, scikit-learn, matplotlib, seaborn, openpyxl preinstalled in a template; no statsmodels or pyarrow ([requirements](https://raw.githubusercontent.com/e2b-dev/code-interpreter/main/template/requirements.txt)); pip allowed | "boots from a snapshot", no number | per vCPU-h and GiB-h; Pro $150/month | "The AI Agent Cloud" | [e2b.dev](https://e2b.dev/) |
| Modal Sandboxes | S | gVisor (earlier memo) | your image; pip at build | "Sub-second cold-starts" | per core-h and GiB-h | "Trusted infrastructure for untrusted agents" | [modal.com](https://modal.com/products/sandboxes) |
| Daytona | S | container, VM option | your image | "Sub 90ms sandbox creation" | $0.0504/vCPU-h, $0.0162/GiB-h | "Run AI Code." / "Secure and Elastic Infrastructure for Running Your AI-Generated Code." | [daytona.io](https://www.daytona.io/) |
| Vercel Sandbox | S | Firecracker microVM | your install | "in milliseconds" | active CPU plus memory | "The safest way to run code you didn't write" | [vercel.com](https://vercel.com/sandbox) |
| Cloudflare Sandbox | S | microVM per container; isolates for Dynamic Workers | not listed | none on the page; 1 to 3 s third party | Workers Paid plan | "A sandbox is an isolated place to run code." | [docs](https://developers.cloudflare.com/sandbox/) |
| Fly.io Sprites | S | hardware-isolated VM | your install | none; 1 to 2 s create (Upstash) | CPU and memory used, hourly | "Sprites: Linux computers for agents" / "full Linux computers designed for agents, not sandboxes." | [fly.io](https://fly.io/sprites) |
| Runloop | S | microVM plus container | your image | "10GB image startup time in <2s" | usage tiers | "Your AI Agent Accelerator" | [runloop.ai](https://runloop.ai/) |
| Blaxel | S | microVM | your image | "resume in ~25ms" | usage after credits | "Infrastructure for autonomous agents." | [blaxel.ai](https://blaxel.ai/) |
| Riza | S, self-host on Enterprise | not named | pandas, matplotlib, seaborn named | "<10ms after Riza gets it" | not listed | "AI writes code. Riza runs it." | [riza.io](https://riza.io/) |
| OpenAI Code Interpreter | S (tool) | container | preinstalled; list not on the page read | none | $0.03 (1 GB) to $1.92 (64 GB) per 20-minute session ([Fly](https://fly.io/learn/code-interpreter-pricing/)) | "The Code Interpreter tool allows models to write and run Python code in a sandboxed environment." | [docs](https://developers.openai.com/api/docs/guides/tools-code-interpreter) |
| Anthropic code execution and programmatic tool calling | S (tool) | container, no internet | pandas, numpy, scipy, scikit-learn, statsmodels, matplotlib, seaborn, pyarrow, openpyxl, pypdf, reportlab, sympy and more, preinstalled; no pip | none | 1,550 free hours/month, then $0.05/container-h; free with web search; not ZDR-eligible | "Run Python and Bash code in a sandboxed container to analyze data, generate files, and iterate on solutions." | [docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool) |
| Gemini code execution | S (tool) | not stated | numpy, pandas, scipy, scikit-learn, seaborn, matplotlib; "You can't install your own libraries"; 30 s maximum | none | tokens only | "The Gemini API provides a code execution tool that enables the model to generate and run Python code." | [docs](https://ai.google.dev/gemini-api/docs/code-execution) |
| Pydantic Monty (OSS) | L (Python, JS, Rust packages) | its own interpreter in Rust | none: "no third-party libraries" | "under 1ms from a running pool" | free, MIT | "A secure Python sandbox, written in Rust, for code written by AI." | [GitHub](https://github.com/pydantic/monty) |
| Full Monty | S you run (container) | Monty, "plus OS-level" | proxies to a full CPython VM | "2 ms" | "not free" | "The execution layer between reasoning and action" | [pydantic.dev](https://pydantic.dev/monty) |
| mcp-run-python | L (Pyodide in Deno) | archived 2026-01-30 | Pyodide's | - | - | "there's just no safe way to run Python within pyodide safely with reasonable latency" | [GitHub](https://github.com/pydantic/mcp-run-python) |
| HubSpot boomslang | L (Java, Python wheel, Rust) | WASI CPython 3.14 | NumPy, Pandas, Matplotlib, Pillow, Pydantic, Jinja2, ijson, compiled in; no scipy or scikit-learn | none | free, Apache-2.0; 6 stars | "Python, but Java." | [GitHub](https://github.com/HubSpot/boomslang) |
| hyperlight-sandbox | L, needs KVM, MSHV or Hyper-V | Wasm guest in a micro-VM | CPython guest; no package workflow (earlier memo) | none | free, Apache-2.0 | "A multi-backend sandboxing framework for running untrusted code with controlled host capabilities built on Hyperlight." | [GitHub](https://github.com/hyperlight-dev/hyperlight-sandbox) |
| hyperlight-wasm | L (Rust) | Wasm in a micro-VM | none | none | free | "Run Wasm Modules in a Virtual Machine backed Sandbox" | [GitHub](https://github.com/hyperlight-dev/hyperlight-wasm) |
| bashkit (everruns) | L (Rust, npm, Python) | in-process; Python via Monty or a CPython 3.14 Wasm guest | none named | none | free | "Awesomely fast virtual sandbox with bash and file system. Written in Rust." | [GitHub](https://github.com/everruns/bashkit) |
| Wasmer | R and S | Wasm (WASIX) | python/python package; numpy and pandas through dynamic linking (earlier memo) | "107× faster startup" than Docker | free runtime; cloud | "Universal compute. Built for AI" | [wasmer.io](https://wasmer.io/) |
| Cloudflare Python Workers and Code Mode | R | V8 isolates, Pyodide | Pyodide's packages | about 1 s with snapshots (Dec 2025, SNIPPET) | Workers plans | Code Mode: "enables LLMs to write and execute code that orchestrates your tools, instead of calling them one at a time." | [changelog](https://developers.cloudflare.com/changelog/post/2026-02-20-codemode-sdk-rewrite/) |
| cpython-wasi-build (Brett Cannon) | artifact | WASI | none | - | free | "Unofficial WASI builds of CPython" | [GitHub](https://github.com/brettcannon/cpython-wasi-build) |
| VMware webassembly-language-runtimes | artifact | WASI | none; Python 3.12.0 (2023) | - | "will be archived soon" | "provides popular language runtimes (Ruby, Python, …) precompiled to WebAssembly" | [GitHub](https://github.com/vmware-labs/webassembly-language-runtimes) |
| RestrictedPython | L | AST rewriting | any (no wall) | - | free | "A restricted execution environment for Python to run untrusted code." and "RestrictedPython is not a sandbox system or a secured environment" | [GitHub](https://github.com/zopefoundation/RestrictedPython) |
| smolagents LocalPythonExecutor | L | AST interpreter with an import allow-list and an operation cap | what you allow | - | free | "no local python sandbox can ever be completely secure" | [docs](https://huggingface.co/docs/smolagents/tutorials/secure_code_execution) |
| **wasi-python** | L (Python); CLI for other languages | WASI, two imports | numpy, pandas, scipy, scikit-learn, statsmodels, matplotlib, lxml, regex compiled in; about 40 pure-Python packages in the zip; no pip | 16 ms for `-c pass` on the snapshot, one arm64 Mac | free, Apache-2.0 | today's GitHub line: "A statically linked CPython for WebAssembly hosts (wasm32-wasip1) with numpy, pandas, scipy, and more compiled in. Built for running untrusted agent code server-side in web applications." | (repo) |

Framework executors, for where buyers meet sandboxes: smolagents offers Blaxel, E2B, Modal and Docker (READ, above). LangChain's Deep Agents list LangSmith, AgentCore, Daytona, Modal, Runloop, Vercel and E2B (SNIPPET, [docs](https://docs.langchain.com/oss/deepagents/code/remote-sandboxes.md)). Cloudflare's Code Mode `Executor` "is runtime agnostic" (READ, changelog above). Open Interpreter now appears to be a terminal coding agent, not a sandbox (SNIPPET, review sites only; not used).

What the table says (INFERRED):

- Every hosted product with pandas is a Linux machine somewhere else, paid by the hour.
- Every in-process product but two has no compiled libraries. The two are boomslang (numpy, pandas, matplotlib) and wasi-python (those plus scipy, scikit-learn, statsmodels).
- Anthropic's preinstalled list is the closest match to wasi-python's set. wasi-python has most of it; it lacks pyarrow, pytz, python-docx, python-pptx, pdfplumber and the PDF rasterisers (`docs/reference/packages.md`).
- **No headline in the table names a library.** pandas appears only in body text.

## 2. The words the market uses

An approximate count over the 26 headline and lead lines quoted in section 1 (INFERRED; one count per line, by hand):

| word or phrase | lines | examples |
|---|---|---|
| sandbox, sandboxed, sandboxing | 12 | Monty, Cloudflare, hyperlight, bashkit, OpenAI, Anthropic, Wasmer |
| AI, AI-generated, written by AI | 7 | Daytona, Monty, Riza, E2B, Runloop, Wasmer |
| agent, agents, autonomous | 6 | E2B, Modal, Sprites, Runloop, Blaxel |
| secure, safe, safest, trusted | 5 | Daytona, Vercel, Monty, Modal, Runloop |
| infrastructure, cloud, computer | 6 | Modal, Daytona, Blaxel, E2B, Sprites |
| untrusted, code you didn't write | 4 | Modal, Vercel, hyperlight, RestrictedPython |
| isolated | 3 | E2B, Cloudflare, Blaxel |
| fast, milliseconds | 4 | Blaxel, bashkit, Wasmer, Vercel |
| in-process | 1 | bashkit (body text) |
| pandas, numpy, a library name | 0 | - |
| no network, offline, your own server | 0 | - |

Overused to the point of saying nothing (INFERRED): **"secure"**, **"sandbox"** on its own, **"AI agents"**, **"infrastructure"**, **"isolated"** and **"fast"**. Every row can say them. "Code you didn't write" (Vercel) and "AI-generated code" (Daytona, Monty) are taken, and the owner's draft repeats them.

Unused, and true of wasi-python (INFERRED): a library name, **in-process** or **a library call**, **no network**, and **nothing leaves your server**. Note that Fly calls its product "not sandboxes", a sign the word is wearing out among VM vendors.

## 3. What buyers ask for and complain about

### 3.1 "Without Docker, on a laptop, in my process"

- Mozilla.ai's otari issue #1383 (2026-09-18) asks for in-process code execution as "the no-Docker default": "Code execution needs Docker today." That is "most people evaluating the project on a laptop, and everyone on a host without Docker." It picks Monty, but notes the default hint "promises numpy, pandas, scipy, sympy and matplotlib" while "monty runs a Python subset with no third-party packages." It rejected "Pyodide or WASI CPython" for "seconds of cold start per request and no snapshotting" (READ, [issue](https://github.com/mozilla-ai/otari/issues/1383)).
- Pydantic's own harness work found some cases "needed full CPython and/or a full VM to run effectively" (READ, [Logfire](https://pydantic.dev/articles/logfire-sandboxes)).

This one issue is the whole pitch in a buyer's words (INFERRED): in-process, no Docker, and the five libraries its prompt already promises. wasi-python carries all five, sympy included.

### 3.2 "pandas cannot run in WebAssembly" (a belief to answer)

- PandaStack, a microVM vendor (2026-10-08): "the Python ecosystem is C extensions: numpy, pandas, psycopg." "Those wheels do not exist for a WASI target." For model-written pandas, "WASM is the wrong tool" (READ, [blog](https://www.pandastack.ai/blog/best-wasm-runtimes-2026/)).
- A 2026 dev.to roundup: C-extension libraries such as NumPy and Pandas "don't work in Wasm yet" (SNIPPET, [dev.to](https://dev.to/mohameddiallo/4-ways-to-sandbox-untrusted-code-in-2026-1ffb)).
- HN: "you're going to take a huge performance hit by putting CPython into wasm" (READ, [HN 46500510](https://news.ycombinator.com/item?id=46500510)).
- Monty's comparison still lists "WASI / wasmtime" at 16 ms with "packages with C extensions need their own WASI build" and snapshotting "no", measured 2026-09-03 (READ, [alternatives](https://pydantic.dev/docs/monty/reference/alternatives/)).

Each statement is out of date for this project (READ (repo): packages page; the snapshot; compute 1.3 to 2.3 times native in `docs/explanation/performance-and-size.md`). The README's first lines can correct it simply by naming the libraries (INFERRED).

### 3.3 Cost and billing

- 1,000 short runs cost "from about $0.24 on Sprites to $7.50 or more on OpenAI containers" (READ, [Fly, 2026-10-05](https://fly.io/learn/code-interpreter-pricing/)).
- "Billing is the biggest hidden difference"; "Providers with no pause state keep charging the full rate" (READ, [Upstash](https://upstash.com/blog/ai-agent-sandbox-providers-compared-2026)).
- "a per-session product punishes an agent that waits on a model for hours"; "Every hosted sandbox has a timer, and the timer sets the bill" (READ, [Fly](https://fly.io/learn/agent-sandbox-providers/)).

### 3.4 State across turns

- "What survives a pause decides how you structure a session" (Upstash, above). "An agent that writes files and comes back later needs a disk that outlives the session" (Fly, above).
- Anthropic added interpreter state that "persists across requests that reuse the container"; OpenAI's container "expires if it is not used for 20 minutes" (READ, the two docs pages).
- Monty can "dump the whole sandbox state to bytes" at a tool call or the end of a snippet (READ, [get started](https://pydantic.dev/docs/monty/get-started/)).

### 3.5 Network egress and data leaving

- Egress "is the column to read closely if the sandbox runs code you did not write"; most providers start open (Upstash, above). "Filesystem isolation is not enough if the agent still has open egress" (Fly, above).
- Anthropic's code execution and programmatic tool calling are `zdr: not-eligible`; container data "is retained for up to 30 days" (READ, the two docs pages).

### 3.6 Trust in the wall

- Pyodide: one flaw, seven products, four CVEs up to 9.9; n8n moved Python to an external runner (READ, [Cyera](https://www.cyera.com/research/sandcastles-not-sandboxes-how-one-architectural-flaw-exposed-seven-products)).
- Monty: round 1 of its bounty was broken "in less than 48 hours" (a use-after-free through `list.sort`); rounds 2 and later held (READ, [round 2](https://pydantic.dev/articles/hack-monty-2), [round 3](https://pydantic.dev/articles/hack-monty-3)).
- wasmtime: two April 2026 escapes, CVE-2026-34971 and CVE-2026-34987, each needing a non-default configuration (Spectre mitigations and signal traps off; the Winch compiler) (SNIPPET, [GitLab](https://advisories.gitlab.com/cargo/wasmtime/CVE-2026-34971/)). The pinned wasmtime 49 postdates them (INFERRED from the fixed versions 36.0.7, 42.0.2, 43.0.1).
- HN on Wasm: "one sandbox escape in nine years is a pretty solid track record" (READ, [HN 48462759](https://news.ycombinator.com/item?id=48462759)).
- smolagents: "no local python sandbox can ever be completely secure" (READ, above).

### 3.7 Pluggable backends

- "the current sandbox abstractions aren't great, can you create a better one?" (READ, Logfire article). Cloudflare's Code Mode executor is "runtime agnostic"; LangChain and smolagents each keep a list of backends (READ, section 1). Buyers meet a sandbox through these lists (INFERRED).

### 3.8 Windows, determinism, cold start

- Windows: hyperlight needs KVM, MSHV or Hyper-V; hosted products are Linux VMs (READ, section 1). Little first-hand complaint was found in this box (INFERRED: a gap in the search, not proof of no demand).
- Cold start "is what matters least" for long agent tasks (Upstash). For code mode, where every model turn runs code, it still matters (Monty's table: 1,500 ms for a service).
- No new 2026 complaint about determinism was found; the earlier memo's section 3 stands.

## 4. Where wasi-python is unique, competitive, or behind

### Unique (INFERRED from the evidence beside each)

- **In-process with the scientific stack.** No other library in section 1 carries scipy, scikit-learn or statsmodels. boomslang stops at numpy, pandas, matplotlib; Monty, bashkit, hyperlight and micropython-wasm carry none (READ, section 1; `docs/reference/packages.md`).
- **No JavaScript, no kernel feature, no hypervisor underneath.** Pyodide's host is a JS engine the guest reached; hyperlight needs a hypervisor; hosted products need a VM. Here the guest imports WASI preview1 and one door, judged on every run (`docs/explanation/why-wasi.md`).
- **The packages' own test suites run inside the sandbox before each release.** No competitor states this; it answers section 3.2's doubt with evidence (README, "What runs").
- **A sealed file you can verify.** Signed build provenance per asset, rebuilt from pinned, hashed sources, with each upstream patch recorded (README, "Verifying a download", "Building from source"). No hosted image and no in-process competitor states a reproducible, attested build (READ, section 1).

### Competitive (INFERRED)

- **Start time.** 16 ms for an empty call on the snapshot is near Daytona's 90 ms claim and Blaxel's 25 ms resume, and far behind Monty's under 1 ms (READ, section 1; `docs/explanation/performance-and-size.md`).
- **Limits by default.** Memory, deadline, output, open files, optional fuel. Monty and the hosted tools also enforce limits (READ, Monty get-started; Simon Willison found Monty's limits "appear to work as advertised", [post](https://simonwillison.net/2026/May/22/monty-investigation/)).
- **Tools and sessions.** `tools=` with MCP-style hints and bounded sessions match Anthropic's programmatic tool calling and REPL persistence, and Monty's external functions (READ).
- **No network.** The same promise as Anthropic's and Gemini's tools; stronger than most hosted sandboxes, which start open (READ, Upstash).
- **Cost.** Zero per call, like Monty and Gemini's token-only tool (READ).

### Behind (said plainly)

- **Monty is faster and ships in more languages today.** Monty has Python, JavaScript and Rust packages, 8.8k stars, a commercial edition, and three public bounty rounds. wasi-python has a Python runner, a CLI, and untested recipes for other engines (READ, Monty get-started and GitHub; `docs/how-to/embed-from-other-languages.md`: "The project runs only wasmtime 49").
- **No JavaScript in-process path.** From Node, the documented route is a subprocess that needs Python and the wheel installed; Node's own WASI "must not be relied on to run untrusted code" (READ (repo), the embedding how-to; earlier memo). A JS core is after 0.1.0 (`context/roadmap.md`).
- **Other hosts lose the runner's protections.** An engine you drive yourself gets "none of the runner's limits, folder checks or clean-up", nor the two wasmtime fixes (READ (repo)).
- **A pandas call is not 16 ms.** The snapshot pre-imports no package: `import pandas` costs 4.66 billion instructions on it and 620 ms on the plain reactor, on one Mac (`docs/explanation/performance-and-size.md`). A session pays it once.
- **Fewer packages than hosted tools.** No pip, no pyarrow (no Parquet), no pytz, no python-docx or python-pptx, no OpenCV; E2B allows pip and Anthropic preinstalls pyarrow (READ, section 1; `docs/reference/limitations.md`).
- **Platform facts.** numpy's default integer is 32-bit; no threads; 4 GiB ceiling; compute 1.3 to 2.3 times slower; a 98 MB wheel (READ (repo), limitations and performance pages). Hosted VMs run native code on many cores.
- **Not a computer.** No shell, no processes, no long-lived disk. Coding agents that need a Linux box (Sprites, E2B) are a different market (READ, Fly).
- **Track record.** No external audit or bounty; one published advisory of its own. A 0.1.0 that PyPI does not yet show (READ, PyPI; commit `2f218a29`).

## 5. Candidate positioning lines

Each line, then what it claims and whether every word is true today.

1. **The owner's draft.** "A Python sandbox for running AI-generated code, or any untrusted code." then "wasi-python is a statically linked, embeddable CPython for WebAssembly hosts, with numpy, pandas, scipy, scikit-learn, statsmodels, matplotlib, lxml and many other packages compiled in. Embed it in Python, JavaScript, Rust or any language your server runs on."
   - The headline is true (`docs/explanation/security-model.md`: "made for running code nobody reviewed") but generic: Daytona, Monty and Vercel say the same (section 2).
   - "many other packages compiled in" overstates it: four more are compiled (Pillow, kiwisolver, contourpy, regex); the 40 others are pure Python in the zip.
   - "Embed it in ... JavaScript, Rust or any language" is **not true today**. JavaScript is a subprocess needing Python; Rust and the rest are untested and lose the runner's limits; hosts without exception handling (wasmer-go, wasmer-python, WAMR, wasmi) cannot load it (`docs/how-to/embed-from-other-languages.md`). Monty can say this line truthfully.
2. "A sandboxed Python with pandas, scipy and scikit-learn that runs inside your own process: no container, no network, no service."
   - Claims the unique pair (in-process plus the stack) and two defaults. True for the Python runner. The CLI is a subprocess, which "inside your own process" does not cover.
3. "Run AI-written pandas on your own server, in a WebAssembly sandbox, as a function call."
   - Claims audience, library, place and shape. True. "Function call" is `run()`.
4. "Real CPython 3.15 with numpy, pandas, scipy, scikit-learn, statsmodels and matplotlib, in a sandbox that sees only the folders and functions you hand it."
   - Claims a full language (against Monty's subset) and the capability wall. True (README; security model).
5. "The scientific Python stack, sealed in one verified WebAssembly file you run in-process."
   - Claims the stack, the attested build, and in-process. True for the Python runner; "one file" is loose (binary plus stdlib zip).
6. "A code interpreter you `pip install`: model-written Python with pandas and matplotlib, run in your process, with nothing sent anywhere."
   - True. "Code interpreter" is the market's generic term (OpenAI, Anthropic, E2B use it); it is also OpenAI's product name, so the owner may prefer to avoid it.
7. "Untrusted Python with pandas in 16 ms, free, on your own machine."
   - **Not true as a reader would take it.** 16 ms is an empty call on one Mac; importing pandas costs far more. Listed as a trap to avoid.

The best three (INFERRED): **2**, **4** and **3**. Line 2 states the difference. Line 4 answers "is it a subset?" and "what can it reach?". Line 3 is the shortest for the agent audience. Any of them can keep the owner's draft headline as the second sentence ("for running AI-generated code, or any untrusted code"), where it names the audience without having to differentiate.

## 6. Three claims no competitor can make

Each is checked against section 1 and the repository today (INFERRED: "no competitor" means no product found in this survey).

1. **"It runs numpy, pandas, scipy, scikit-learn, statsmodels and matplotlib inside your own process, with no container, VM or service."** Evidence: `docs/reference/packages.md`; the README's quickstart runs pandas from `run()`. boomslang lacks scipy, scikit-learn and statsmodels; Monty and bashkit have no libraries; everything else with them is hosted.
2. **"Each package's own test suite runs inside the sandbox before every release."** Evidence: README, "What runs"; `CHANGELOG.md` (the compiled and pure-Python packages' own tests; `tests/release_shards.toml`). No competitor states it; it answers "does pandas really work in Wasm?" with evidence rather than an assertion.
3. **"Its guest reaches the host through WASI and one function you supply, with no JavaScript, no hypervisor and no kernel feature underneath, and every asset is rebuilt from pinned sources and signed."** Evidence: `docs/explanation/why-wasi.md`, `docs/explanation/security-model.md` ("The guest imports two things only"); README, "Verifying a download". Pyodide sandboxes have a JS host; hyperlight needs a hypervisor; hosted images are not reproducible to the buyer; boomslang states no provenance.

A fourth was considered and held back: fuel as "the same count on every machine". The roadmap notes Linux CI fuel moving between runs and one guest path that differs on Linux (`context/roadmap.md`, the follow-ups after 0.1.0). Until that is explained, it is safer in the body than in a headline.

## 7. Questions for the owner

1. **Lead with the stack or with the audience?** The market never names a library in a headline; naming pandas is the one move nobody else makes. The draft leads with the audience, which everybody leads with.
2. **The JavaScript and Rust sentence.** Drop it until a host exists and is tested, or say "from any language, through a one-line JSON command"? (Section 5, line 1.)
3. **"Embeddable" and "in-process" need a qualifier** for other languages, since the runner's limits live in the Python package. Say so in the README's first screen, or only in Hosts?
4. **Pre-import pandas in a snapshot?** The 16 ms figure does not hold for a pandas call, and the otari issue rejected WASI Python for "seconds of cold start". A measured pandas-call time would answer it, or a second snapshot (a roadmap decision, not a README one).
5. **Outreach.** Pydantic's table and the otari issue both describe WASI Python as having no C extensions and no snapshot. Correct them, with measured numbers (constitution §4.10)?
6. **A bounty or an external review** for a public track record beside Monty's three rounds?
7. **One description everywhere.** The GitHub line ("server-side in web applications"), the PyPI summary ("numpy, pandas and matplotlib") and the README differ. Align them at 0.1.0?
8. **A comparison table in the docs** (Monty publishes one)? It would need a measured command for every number, and it would name competitors, which the README so far does not.

## One line

The market sells sandboxes as "secure infrastructure for AI agents" and believes pandas cannot run in WebAssembly; wasi-python's honest, unique headline is that real CPython with pandas, scipy and scikit-learn runs sandboxed inside your own process, and it must not yet claim JavaScript or "any language".
