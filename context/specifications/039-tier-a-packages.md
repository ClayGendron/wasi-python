# 039 — Tier A: the pure-Python packages

- **Status:** drafted 2026-10-17. It changes the build recipe and the artifact set, so it is
  reviewed once more before it is built (constitution §5.6). It is build-class: it touches
  `scripts/`, `recipes/`, `downloads/SHA256SUMS` and the release workflow (§5.7).
- **Owner:** Clay Gendron
- **Kind:** the build recipe (31 pins in `downloads/SHA256SUMS` and `scripts/00_download.sh`;
  `scripts/steps/70_zip.sh`; `scripts/assemble_artifacts.py`), one recipe line
  (`recipes/ctypes_stand_in/util.py` gains `dllist`), judge additions and changes (seven golden
  jobs and the oracle's pins, six other checks, the judge's package and licence lists, two
  source-tree patterns, one bound of spec 035 re-based, two known gaps), the release workflow's
  tree count, `README.md`, `CHANGELOG.md`, `LICENSES/`.
- **Depends on:** three specifications not yet built, each landing first (Decision 14):
  033 (the zip keeps `METADATA` and `entry_points.txt`; `make_stdlib_zip.py --metadata`;
  `tree_members`; the `ctypes` stand-in package), 035 (the zip's directory is read once; the
  owner's decisions 44 and 45 put tier A and sympy after it) and 023 (matplotlib M1, which pins
  `packaging` 26.3, patsy's one requirement). Landed: 020 (each source tree equals its tarball
  plus the recorded patches), 012 (the same bytes from any host), 018 (no litter in the zip),
  004 and 009 (the licence notices). Where 033, 035 or 023 lands in another shape than its text,
  this specification uses what landed and says so in its landing notes.
- **Research it stands on:** `../research/2026-10-17-what-else-the-default-profile-carries.md`
  and its folder: tier A ("The tiers"), findings 3 to 5 (each candidate measured and run in the
  guest; the five catches; 77,912 fuel per member), `outputs/measure.tsv`,
  `outputs/guest/probes.tsv`, `outputs/followup.tsv`, `outputs/native-parity.txt`. The owner's
  decisions 43 (tier A and its licences), 45 (sympy after spec 035), 46 (Excel output with
  nothing writable is documented, not enabled) and 47 (no pytz) in `../decisions.md`.
  Spec 033's Decision 6 leaves threadpoolctl's stand-in to this specification. **The drafting
  runs** (EXECUTED 2026-10-17 in the session's scratch folder, outside the repository; nothing
  in the repository was changed by them):
  - PyPI's JSON for each package: the current release, its upload date, its files and their
    SHA-256; each chosen file downloaded and its hash recomputed (`shasum -a 256`, all equal);
  - each wheel's `.dist-info` read for licence files and `entry_points.txt`;
  - the members and deflated bytes step 70 would add, computed with step 70's own
    `wheel_members`, `walk`, `pyc` and `member` (imported read-only from `scripts/`) under the
    line's Python 3.15.0, plus spec 033's two kept files;
  - seven drafted job programs, run natively (Python 3.15.0, the pinned versions) under
    `PYTHONHASHSEED` 0 and 1 (the outputs agree), then in today's plain `python.wasm` on a
    scratch zip: today's 1,751 members plus this specification's 2,014, with numpy's and
    pandas' `METADATA` from their `PKG-INFO` and the `packaging` 26.3 wheel (what 033 and 023
    bring), and a two-name scratch `ctypes` (`c_long`, `sizeof`) in place of 033's stand-in.
    All seven equal native byte for byte (one with a variant noted in Decision 11);
  - threadpoolctl 3.7.0 on the host with `sys.platform` set to `"wasi"` and a model of 033's
    stand-in, with and without `ctypes.util.dllist`;
  - the wheel's size today, and PyPI's upload limit (READ, `https://pypi.org/help/`).

## The problem

Agents read and write spreadsheets, PDFs, HTML, YAML and templates; they draw graphs, solve
equations, build model formulas and lean on a handful of utility libraries. Every hosted code
sandbox the memo read ships most of these (finding 1). Today's zip carries none of them, so the
guest answers `ModuleNotFoundError` for `openpyxl`, `pypdf`, `bs4`, `yaml`, `jinja2`, `networkx`,
`sympy` and the rest.

The memo ran each one inside today's `python.wasm` (finding 4). Most work as they are. Five
catches stood in the way:
- **a.** packages that read their own metadata (tabulate, so `df.to_markdown()`): spec 033;
- **b.** openpyxl writes through `tempfile`, which needs a writable folder: decision 46;
- **c.** sympy and threadpoolctl need more of `ctypes` than today's stub: spec 033, and
  threadpoolctl's discovery (Decision 5 here);
- **d.** pandas' Styler reads its templates by file path: a follow-up (Decision 15);
- **e.** each zip member costs fuel on every plain start: spec 035.

With 033 and 035 landed, what is left is this specification: pin about thirty pure-Python
distributions, pack them, ship their notices, prove each family against native Python, and say
in the README what works and what does not.

## Decisions

1. **What goes in: thirty distributions in seven families.** Each family has one golden job
   (Decision 11). Members and bytes are what step 70 adds, metadata included (EXECUTED while
   drafting; the bytes are deflated members as a standalone zip holds them):

   | family (job) | distributions | members | bytes |
   |---|---|---|---|
   | `excel` | openpyxl 3.1.5, et-xmlfile 2.0.0, xlsxwriter 3.2.9, xlrd 2.0.2 | 249 | 1,028,538 |
   | `pdf` | pypdf 6.21.1 | 61 | 837,913 |
   | `markup` | beautifulsoup4 4.15.0, soupsieve 3.0.3, html5lib 1.1, webencodings 0.6.1, defusedxml 0.7.1, xmltodict 1.0.4 | 78 | 562,491 |
   | `text_formats` | pyyaml 6.0.3, tomli-w 1.2.0, jinja2 3.1.6, markupsafe 3.0.4, tabulate 0.10.0, charset-normalizer 3.5.2 | 72 | 588,328 |
   | `modelling` | networkx 3.7, patsy 1.0.3 | 323 | 2,115,136 |
   | `symbolic` | sympy 1.14.0, mpmath 1.3.0 | 934 | 9,405,999 |
   | `utilities` | attrs 26.1.0, more-itertools 11.2.1, toolz 1.2.0, tqdm 4.70.1, typing-extensions 4.16.0, joblib 1.6.0, cloudpickle 3.1.2, threadpoolctl 3.7.0, narwhals 2.27.1 | 297 | 1,942,062 |
   | **all** | **30** | **2,014** | **16,480,467** |

   The 2,014 include 36 metadata members: 28 wheels' `METADATA`, six `entry_points.txt`
   (charset-normalizer, jinja2, networkx, sympy, tabulate, tqdm) and the two sdists' `METADATA`.
   Every licence is approved by decision 43 (§4.12). html5lib's `six` and patsy's `packaging`
   are not new: `six` is in today's zip, `packaging` comes with spec 023 (Decision 7). tqdm's
   `colorama` is required on Windows only and stays out. Nothing here needs the
   `importlib_metadata` or `importlib_resources` backports, which spec 035's Scope asked this
   specification to check (READ: no wheel requires them on 3.15).

   **seaborn and reportlab are not here** (Decision 15): a follow-up after 023.
2. **The pins.** Each version is the current release on PyPI on 2026-10-17 and the version the
   memo ran in the guest, with one exception: **mpmath is 1.3.0, not the memo's 1.4.1**, because
   sympy 1.14.0 (still the current sympy) declares `mpmath<1.4,>=1.1.0` (READ: its `METADATA`).
   The memo installed each package `--no-deps`, so it never met that bound. sympy does not check
   the bound at run time; the pin follows it so that the pair is one upstream tested. Some are
   recent (pypdf 6.21.1 was uploaded on 2026-10-17, soupsieve 3.0.3 on 2026-10-12,
   more-itertools 11.2.1 on 2026-10-14): each is the version the memo's probes passed on.

   The `get` lines for `scripts/00_download.sh`, in a new block after the three existing
   pure-Python pins (one line per pin, as spec 003 requires), and the last one in the licence
   block (Decision 8):

   ```sh
   get https://files.pythonhosted.org/packages/c0/da/977ded879c29cbd04de313843e76868e6e13408a94ed6b987245dc7c8506/openpyxl-3.1.5-py2.py3-none-any.whl openpyxl-3.1.5-py2.py3-none-any.whl
   get https://files.pythonhosted.org/packages/c1/8b/5fe2cc11fee489817272089c4203e679c63b570a5aaeb18d852ae3cbba6a/et_xmlfile-2.0.0-py3-none-any.whl et_xmlfile-2.0.0-py3-none-any.whl
   get https://files.pythonhosted.org/packages/3a/0c/3662f4a66880196a590b202f0db82d919dd2f89e99a27fadef91c4a33d41/xlsxwriter-3.2.9-py3-none-any.whl xlsxwriter-3.2.9-py3-none-any.whl
   get https://files.pythonhosted.org/packages/1a/62/c8d562e7766786ba6587d09c5a8ba9f718ed3fa8af7f4553e8f91c36f302/xlrd-2.0.2-py2.py3-none-any.whl xlrd-2.0.2-py2.py3-none-any.whl
   get https://files.pythonhosted.org/packages/85/e6/24c944e473c34e818cf1b98085796fcd780465ecfe17663f2bf8fee1958b/pypdf-6.21.1-py3-none-any.whl pypdf-6.21.1-py3-none-any.whl
   get https://files.pythonhosted.org/packages/07/6c/aa3f2f849e01cb6a001cd8554a88d4c77c5c1a31c95bdf1cf9301e6d9ef4/defusedxml-0.7.1-py2.py3-none-any.whl defusedxml-0.7.1-py2.py3-none-any.whl
   get https://files.pythonhosted.org/packages/88/c6/92fcd42f1ba33e1184263f25bfabf3d27c383410470f169e4b8163bf9c17/beautifulsoup4-4.15.0-py3-none-any.whl beautifulsoup4-4.15.0-py3-none-any.whl
   get https://files.pythonhosted.org/packages/49/ca/f639c80449997b88aba7bc9705d25dd76cc0844f45f187862fd8f8bb18fa/soupsieve-3.0.3-py3-none-any.whl soupsieve-3.0.3-py3-none-any.whl
   get https://files.pythonhosted.org/packages/6c/dd/a834df6482147d48e225a49515aabc28974ad5a4ca3215c18a882565b028/html5lib-1.1-py2.py3-none-any.whl html5lib-1.1-py2.py3-none-any.whl
   get https://files.pythonhosted.org/packages/77/c6/040cbc72480d789a5f40d63fb484d3106554c4dfa2d2b70ad5022057750f/webencodings-0.6.1-py3-none-any.whl webencodings-0.6.1-py3-none-any.whl
   get https://files.pythonhosted.org/packages/05/8e/961c0007c59b8dd7729d542c61a4d537767a59645b82a0b521206e1e25c2/pyyaml-6.0.3.tar.gz pyyaml-6.0.3.tar.gz
   get https://files.pythonhosted.org/packages/c7/18/c86eb8e0202e32dd3df50d43d7ff9854f8e0603945ff398974c1d91ac1ef/tomli_w-1.2.0-py3-none-any.whl tomli_w-1.2.0-py3-none-any.whl
   get https://files.pythonhosted.org/packages/62/a1/3d680cbfd5f4b8f15abc1d571870c5fc3e594bb582bc3b64ea099db13e56/jinja2-3.1.6-py3-none-any.whl jinja2-3.1.6-py3-none-any.whl
   get https://files.pythonhosted.org/packages/38/9b/e422a865e1d5d57d0e509b4e0bf1c1a70a7f6382c29a5aa428df994c8bc8/markupsafe-3.0.4.tar.gz markupsafe-3.0.4.tar.gz
   get https://files.pythonhosted.org/packages/99/55/db07de81b5c630da5cbf5c7df646580ca26dfaefa593667fc6f2fe016d2e/tabulate-0.10.0-py3-none-any.whl tabulate-0.10.0-py3-none-any.whl
   get https://files.pythonhosted.org/packages/fc/ad/d07d7862a62ffa6d79d68074d14823243dd235a77c45262acbf6adeb28bf/charset_normalizer-3.5.2-py3-none-any.whl charset_normalizer-3.5.2-py3-none-any.whl
   get https://files.pythonhosted.org/packages/38/34/98a2f52245f4d47be93b580dae5f9861ef58977d73a79eb47c58f1ad1f3a/xmltodict-1.0.4-py3-none-any.whl xmltodict-1.0.4-py3-none-any.whl
   get https://files.pythonhosted.org/packages/7e/cd/fe58041e9011f307c490e3e17dd48cc516448f7c698a3f2d9d9d65d7e6a8/networkx-3.7-py3-none-any.whl networkx-3.7-py3-none-any.whl
   get https://files.pythonhosted.org/packages/a2/09/77d55d46fd61b4a135c444fc97158ef34a095e5681d0a6c10b75bf356191/sympy-1.14.0-py3-none-any.whl sympy-1.14.0-py3-none-any.whl
   get https://files.pythonhosted.org/packages/43/e3/7d92a15f894aa0c9c4b49b8ee9ac9850d6e63b03c9c32c0367a13ae62209/mpmath-1.3.0-py3-none-any.whl mpmath-1.3.0-py3-none-any.whl
   get https://files.pythonhosted.org/packages/20/70/cd3cf5cff538323076a879edef02cce6f13f7d75e03d12f211b0a0dbd178/patsy-1.0.3-py2.py3-none-any.whl patsy-1.0.3-py2.py3-none-any.whl
   get https://files.pythonhosted.org/packages/64/b4/17d4b0b2a2dc85a6df63d1157e028ed19f90d4cd97c36717afef2bc2f395/attrs-26.1.0-py3-none-any.whl attrs-26.1.0-py3-none-any.whl
   get https://files.pythonhosted.org/packages/5d/57/3c4b1c6f2e0cc29ba023802458ea3d2a996f87085559e4a5f2192d549532/more_itertools-11.2.1-py3-none-any.whl more_itertools-11.2.1-py3-none-any.whl
   get https://files.pythonhosted.org/packages/db/17/4c8beb6c8c4176c6bf143bfd7e1e4dd6719b00ced90738c7ac471b71c1df/toolz-1.2.0-py3-none-any.whl toolz-1.2.0-py3-none-any.whl
   get https://files.pythonhosted.org/packages/a7/03/921a3d3c75785aca9ebfbfcabfbc3a1be12e2ab5265deb026d55a5a3f83e/tqdm-4.70.1-py3-none-any.whl tqdm-4.70.1-py3-none-any.whl
   get https://files.pythonhosted.org/packages/49/d3/b8441a820a491ddfc024b0b0cf0393375b75ea13866d9c66727e54c2fc80/typing_extensions-4.16.0-py3-none-any.whl typing_extensions-4.16.0-py3-none-any.whl
   get https://files.pythonhosted.org/packages/18/53/84099323c2ec4be98d935f63c033ac4151ee83836ca1050ede3b3aadf155/joblib-1.6.0-py3-none-any.whl joblib-1.6.0-py3-none-any.whl
   get https://files.pythonhosted.org/packages/88/39/799be3f2f0f38cc727ee3b4f1445fe6d5e4133064ec2e4115069418a5bb6/cloudpickle-3.1.2-py3-none-any.whl cloudpickle-3.1.2-py3-none-any.whl
   get https://files.pythonhosted.org/packages/43/3f/f88a53f60a472b46f4023f56d204dd7de33d34c5d2acbfa0d70a674e639e/threadpoolctl-3.7.0-py3-none-any.whl threadpoolctl-3.7.0-py3-none-any.whl
   get https://files.pythonhosted.org/packages/d1/89/5d4c86da1130d9059681e5b6cd7645df5c10279a6a079c5c37dcb2cc6f3f/narwhals-2.27.1-py3-none-any.whl narwhals-2.27.1-py3-none-any.whl
   get https://raw.githubusercontent.com/spdx/license-list-data/31ba1a50e5397e00a304dbadc76531740e89ee48/text/MPL-2.0.txt spdx-31ba1a50-MPL-2.0.txt
   ```

   The lines for `downloads/SHA256SUMS` (each equal to PyPI's published digest, and recomputed
   from the downloaded file while drafting):

   ```
   5282c12b107bffeef825f4617dc029afaf41d0ea60823bbb665ef3079dc79de2  openpyxl-3.1.5-py2.py3-none-any.whl
   7a91720bc756843502c3b7504c77b8fe44217c85c537d85037f0f536151b2caa  et_xmlfile-2.0.0-py3-none-any.whl
   9a5db42bc5dff014806c58a20b9eae7322a134abb6fce3c92c181bfb275ec5b3  xlsxwriter-3.2.9-py3-none-any.whl
   ea762c3d29f4cca48d82df517b6d89fbce4db3107f9d78713e48cd321d5c9aa9  xlrd-2.0.2-py2.py3-none-any.whl
   553e2d42f5bb3bb2a785a7d3de8ef90bb7df74b5413eff5a7b4388007ea9254b  pypdf-6.21.1-py3-none-any.whl
   a352e7e428770286cc899e2542b6cdaedb2b4953ff269a210103ec58f6198a61  defusedxml-0.7.1-py2.py3-none-any.whl
   d6f88de62e1d4e38ecb1077eb9724cd0eff29d2a08ca16a401e9b9e93f117cf9  beautifulsoup4-4.15.0-py3-none-any.whl
   fa30e3ba4809cb81ce1f3209f2fbe3e779fc445f0439bc147a0d7c4601743f21  soupsieve-3.0.3-py3-none-any.whl
   0d78f8fde1c230e99fe37986a60526d7049ed4bf8a9fadbad5f00e22e58e041d  html5lib-1.1-py2.py3-none-any.whl
   7fab6269c8bf237c657876b52058ccb182e861518d1c695c1a9aaa8c1c105d5b  webencodings-0.6.1-py3-none-any.whl
   d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f  pyyaml-6.0.3.tar.gz
   188306098d013b691fcadc011abd66727d3c414c571bb01b1a174ba8c983cf90  tomli_w-1.2.0-py3-none-any.whl
   85ece4451f492d0c13c5dd7c13a64681a86afae63a5f347908daf103ce6d2f67  jinja2-3.1.6-py3-none-any.whl
   2e9ad7dd851bf45fab9f75cbff4cb493fee9979e8d8c7c9c3ee119022518edd6  markupsafe-3.0.4.tar.gz
   f0b0622e567335c8fabaaa659f1b33bcb6ddfe2e496071b743aa113f8774f2d3  tabulate-0.10.0-py3-none-any.whl
   b6b751274acb69d77b3323d6b7dbaa3c7fdfc1eb829b7eb61d262f32e1af9685  charset_normalizer-3.5.2-py3-none-any.whl
   a4a00d300b0e1c59fc2bfccb53d7b2e88c32f200df138a0dd2229f842497026a  xmltodict-1.0.4-py3-none-any.whl
   e3fd2c13a7814cee3746340d8d7f8598a67f16a58bf47fb7f8793fab6efca1b0  networkx-3.7-py3-none-any.whl
   e091cc3e99d2141a0ba2847328f5479b05d94a6635cb96148ccb3f34671bd8f5  sympy-1.14.0-py3-none-any.whl
   a0b2b9fe80bbcd81a6647ff13108738cfb482d481d826cc0e02f5b35e5c88d2c  mpmath-1.3.0-py3-none-any.whl
   d3dbebe8fd5f46e29912d030b63c6268647b59bf788a99e2af28a30234cf357c  patsy-1.0.3-py2.py3-none-any.whl
   c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309  attrs-26.1.0-py3-none-any.whl
   35a7377edd1dd6608dcb2cdf534ded55ea32d49448875ad042cd3f879fb1ded0  more_itertools-11.2.1-py3-none-any.whl
   890f820b1cb8152785aaf9386d8707770110809035800985ca65cb24ce1120ef  toolz-1.2.0-py3-none-any.whl
   c293e525e6fef9c20e8728fd4612df02a0aa31bb5fe91ecd93e123b1b7bffa73  tqdm-4.70.1-py3-none-any.whl
   481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8  typing_extensions-4.16.0-py3-none-any.whl
   3dbbf9f6e4b592a2357b854608e980fe6390d131d7a82f011a377ef2ebef7aba  joblib-1.6.0-py3-none-any.whl
   9acb47f6afd73f60dc1df93bb801b472f05ff42fa6c84167d25cb206be1fbf4a  cloudpickle-3.1.2-py3-none-any.whl
   cd8b60b5641b45c67bbf73c64c843235fc2d8a480c87389f52f5dbee893b86be  threadpoolctl-3.7.0-py3-none-any.whl
   d057df13f5852b8e157596e82eb5e955fad267425df5e420e0ee9863da483b31  narwhals-2.27.1-py3-none-any.whl
   66a3107d5ad6a058aab753eaac2047ccb2ed0e39465dd0fe5844da3e300d5172  spdx-31ba1a50-MPL-2.0.txt
   ```

   Every pin is host-neutral: one file for every build host, as the three existing pure-Python
   pins are. `MANIFEST` gains a `pin` line for each, through `assemble_artifacts.py`'s existing
   loop.
3. **Pure Python only, and how.** Twenty-eight of the thirty publish a `py3-none-any` (or
   `py2.py3-none-any`) wheel, and that wheel is pinned. One of them, charset-normalizer, also
   publishes mypyc-compiled platform wheels; its pure wheel is the pin. **pyyaml and markupsafe
   publish no pure wheel** (READ: PyPI lists 72 and 150 platform wheels and one sdist each). For
   those two the pin is the **sdist**, and the zip takes only its pure package folder:
   - pyyaml: `lib/yaml/` (17 modules). Its `yaml/__init__.py` imports `.cyaml` in a `try` and
     sets `__with_libyaml__ = False` when `yaml._yaml` is missing, so the pure loader and dumper
     serve every call (READ; EXECUTED in the guest by the memo and while drafting). The sdist's
     `lib/_yaml/` stand-in for the old C module is left out: without libyaml it only raises
     `ModuleNotFoundError: No module named '_yaml'`, which a missing module raises anyway.
   - markupsafe: `src/markupsafe/`. Its `__init__.py` imports `._speedups` in a `try` and falls
     back to `._native` (READ). The `_speedups.c` and `_speedups.pyi` files are skipped by step
     70's existing suffix rule; `py.typed` goes in, as it does from every wheel that has one.

   **Why sdists and not a platform wheel with its `.so` dropped.** Step 70 would drop the `.so`
   silently (its `SKIP_SUFFIXES`), and the memo's measurements did exactly that. But pinning a
   `manylinux` or `macosx` wheel for a `wasm32-wasip1` build hides what the zip holds, and the
   wheel's native file would be bytes we pin and never use. The sdist is the project's source
   release: spec 020's tree check proves the unpacked tree equals it, and spec 033's
   `--metadata` takes its `PKG-INFO` as the `METADATA` (`Name: PyYAML`, `Version: 6.0.3`;
   `Name: MarkupSafe`, `Version: 3.0.4`; READ). This is the pattern numpy and pandas already
   follow.

   No native file enters the zip: the v1.2 check that the zip holds no shared library
   (`rules.shared_library_errors`) stays as it is and covers all thirty.
4. **Step 70.** Three changes, in this order in `scripts/steps/70_zip.sh`:
   - **The two sdists, unpacked and staged.** Before the zip is built:
     `remove "$B/pyyaml-6.0.3" "$B/markupsafe-3.0.4" "$B/pure-install"`; each tarball unpacked
     from `pinned …` into `$B` and passed to `patch_tree` (no patches today; spec 020's rule
     applies as to every tree); then `$B/pure-install/` is made with exactly two folders,
     `cp -R "$B/pyyaml-6.0.3/lib/yaml" "$B/pure-install/yaml"` and
     `cp -R "$B/markupsafe-3.0.4/src/markupsafe" "$B/pure-install/markupsafe"`. The staging
     folder is needed because both sdists keep an `.egg-info` folder beside the package
     (`lib/PyYAML.egg-info/`, `src/MarkupSafe.egg-info/`; READ), and spec 033's `tree_members`
     stops the build on an `.egg-info` at a tree's top, as its Decision 9 foresaw. This is
     step 50's pattern for pandas (`cp -R "$SRC/pandas" "$SITE"`).
   - **The zip's inputs.** `--tree "$B/pure-install"`, `--metadata "$B/pyyaml-6.0.3/PKG-INFO"`,
     `--metadata "$B/markupsafe-3.0.4/PKG-INFO"`, and one `--wheel "$(pinned <file>)"` line for
     each of the 28 wheels, in Decision 2's order.
   - Nothing else changes: `make_stdlib_zip.py` is spec 033's, untouched here. Each wheel goes
     in as step 70 packs every wheel (tests and sources skipped, `.data/` skipped, `METADATA` and
     `entry_points.txt` kept). Compiling sympy prints one `SyntaxWarning` (a `return` inside
     `finally` in `sympy/testing/runtests.py`; EXECUTED while drafting); it goes to the step's
     log and changes nothing.
5. **threadpoolctl: the real package, and one true function in the `ctypes` stand-in.** Spec
   033's Decision 6 left the choice here: the real threadpoolctl over 033's stand-in, or a
   stand-in module of ours that reports no native thread pools. Neither as 033 imagined:
   - **What the real one does on WASI** (READ, threadpoolctl 3.7.0, `_load_libraries`): on a
     platform that is not Linux or Emscripten it tries `from ctypes.util import dllist`
     (CPython 3.14's list of loaded shared libraries); with that, it lists libraries through
     it. Without it, on a platform that is none of macOS, Windows or Pyodide, it calls
     `_get_libc()`, which is `ctypes.CDLL(None, …)`. 033's stand-in refuses `CDLL` with
     `OSError`, so `threadpool_info()` and `threadpool_limits(…)` would raise.
   - **The change:** `recipes/ctypes_stand_in/util.py` gains `dllist()`, returning `[]`. That is
     a true answer on wasm32-wasi: the guest is one statically linked module and loads no shared
     library (no `dlopen`), as `find_library` returning `None` already says. It follows 033's
     rule: a name exists so that an import succeeds, and every answer is true on wasm32.
   - **EXECUTED while drafting** (host Python 3.15.0, `sys.platform` set to `"wasi"`, a model of
     033's stand-in): without `dllist`, `threadpool_info()`, `threadpool_limits(limits=1,
     user_api="blas")` and `ThreadpoolController().select(user_api="openmp").info()` each raised
     `OSError: ctypes is unavailable on wasm32-wasi`. With `dllist` returning `[]`, they gave
     `[]`, entered and left the limit, and gave `[]`, with no warning.
   - **Why not a stand-in module.** A module of ours named `threadpoolctl` would have to copy
     the API scikit-learn calls (`ThreadpoolController`, `select`, `limit`, `wrap`, `info`,
     `threadpool_limits` as a context manager and a decorator, `register`, `LibController`),
     follow it release by release, and would hide the real package's version. The real package
     with a true `dllist` is one line of ours. scikit-learn (tier B) then gets "no native
     thread pools", which is what this platform has.
6. **sympy and mpmath.** sympy imports `c_long` and `sizeof` from `ctypes` at import
   (`sympy/external/gmpy.py:3`); spec 033's stand-in serves both. `sizeof(c_long)` is 4 in the
   guest and 8 natively on 64-bit hosts. sympy uses it only for `LONG_MAX`, which only its gmpy2
   and python-flint branches read (READ, `gmpy.py:187`, `:226`, `:288`); with neither present
   the ground types are pure Python, so the answer does not reach any result. `sympy.lambdify`
   with its default modules imports `numpy.ctypeslib`, which needs 033's stand-in (the drafting
   run's two-name `ctypes` failed there with `AttributeError: … 'c_void_p'`; 033's review
   EXECUTED `import numpy.ctypeslib` on its stand-in). sympy's own `isympy.py` top-level module
   goes in with the wheel.
7. **patsy's `packaging` comes from spec 023,** which pins `packaging-26.3-py3-none-any.whl`
   (SHA-256 `d7193f7c…cd1c`, equal to PyPI's, READ). patsy imports it at import
   (`patsy/util.py:46`; the drafting run without it failed there). This specification is built
   after 023 (Decision 14). If the order is ever changed, this specification pins that same
   wheel itself and 023 drops its line; the bytes do not change.
8. **Licences and notices** (§4.12: each approved by decision 43; each ships with its notice).
   - `scripts/assemble_artifacts.py`: `PACKAGES` gains the thirty, by their PyPI names in
     Decision 1's order (`openpyxl`, `et-xmlfile`, …, `pyyaml`, …, `markupsafe`, …,
     `narwhals`); `WHEELS` gains the 28 wheels. Each wheel's notice is built by the existing
     `wheel_licences`, which takes every `LICEN[CS]E`, `COPYING` or `NOTICE` file in its
     `.dist-info` (READ while drafting: each of the 28 has at least one; et-xmlfile has two,
     `LICENCE.rst` and `LICENCE.python`, the second for the code it takes from Python's
     standard library under the PSF licence, and both go in).
   - pyyaml's notice is `build/pyyaml-6.0.3/LICENSE`, markupsafe's
     `build/markupsafe-3.0.4/LICENSE.txt`, each named in the `licences` dict as zlib's is.
   - **tqdm (MPL-2.0 AND MIT).** Its wheel's `LICENCE` holds the MIT text and MPL-2.0's
     Exhibit A, not the MPL's full text (READ). The zip ships tqdm as bytecode, which MPL-2.0
     calls the Executable Form: §3.2 asks that its recipients can get the Source Code Form and
     receive the licence. So `LICENSES/tqdm.txt` holds three parts: the wheel's `LICENCE`; the
     full MPL-2.0 text, pinned by URL and SHA-256 (`spdx-31ba1a50-MPL-2.0.txt`, SPDX's
     `license-list-data` at commit `31ba1a50`, an immutable URL; Decision 2); and a part headed
     `tqdm source` saying that tqdm 4.70.1's Source Code Form is the pinned wheel
     `tqdm-4.70.1-py3-none-any.whl` (its URL and SHA-256 as in Decision 2), which holds its
     `.py` files, and the project's repository at tag `v4.70.1`.
   - The other licences (MIT, BSD-2-Clause, BSD-3-Clause, BSD, PSF-2.0) ask for their notice to
     travel with the work, which `LICENSES/` does; none asks for source.
   - The judge's `paths.PACKAGES` and `paths.LICENCE_COMPONENTS` gain the thirty, so
     `test_manifest_is_well_formed` and `test_licence_notices_cover_every_component` require a
     `package` line and a notice holding the pinned archive's top-level licence for each (the
     existing `licence_source` finds wheels and sdists by `is_version_of`). A new check holds
     tqdm's three parts (Decision 12).
9. **What a guest sees: the edges, stated.** Each is either a check or a golden line (Decisions
   11 and 12), and each goes in the README (Design).
   - **Excel output with nothing writable (decision 46).** pandas 3.0.6 picks xlsxwriter as the
     default `.xlsx` writer when it is present (`get_default_engine("xlsx", mode="writer")` is
     `xlsxwriter`; EXECUTED natively), and openpyxl as the reader. Both writers use `tempfile`:
     xlsxwriter for each worksheet unless `in_memory` is set, openpyxl always (memo finding 4b:
     "No usable temporary directory"). So a call with nothing writable can **read** any `.xlsx`
     and can **write** one only through
     `pd.ExcelWriter(buf, engine="xlsxwriter", engine_kwargs={"options": {"in_memory": True}})`
     or `xlsxwriter.Workbook(buf, {"in_memory": True})`. A writable grant at `/tmp`
     (`Grant(folder, "/tmp", writable=True)`) or `root=True` makes every writer work. The
     default stays: nothing writable (§4.15).
   - **`pd.read_html` needs `flavor="bs4"`** until lxml is in (tier B): with no `flavor` pandas
     tries lxml first and raises `ImportError` (`` `Import lxml` failed. ``) without trying
     bs4 (EXECUTED natively, where lxml is also absent). With `flavor="bs4"` it parses through
     beautifulsoup4 and html5lib.
   - **pypdf reads and writes, and encrypts with RC4, but AES needs `cryptography`,** a Rust and
     OpenSSL package (tier C): `encrypt(…, algorithm="AES-128")` and decrypting an AES file
     raise `pypdf.errors.DependencyError: cryptography>=3.1 is required for AES algorithm`
     (EXECUTED natively without `cryptography`).
   - **joblib runs serially:** `Parallel(n_jobs=2)` returns the same result as `n_jobs=1`
     (no threads, no processes; memo finding 4f; EXECUTED in the job). `joblib.Memory` needs a
     writable folder for its cache.
   - **tqdm warns once that it cannot start its monitor thread**
     (`TqdmMonitorWarning … can't start new thread`, on stderr; EXECUTED in the guest); setting
     `tqdm.tqdm.monitor_interval = 0` first silences it. Bars write to stderr as natively.
   - **threadpoolctl finds no native thread pools** (Decision 5).
   - **networkx algorithms that need scipy** (`pagerank`, the spectral and linear-algebra ones)
     raise `ModuleNotFoundError: scipy` until spec 037 lands, as natively without scipy.
     **`import networkx` reads entry points** (`networkx/utils/backends.py:102`,
     `entry_points(group="networkx.backends")`, READ), so it pays an `importlib.metadata` scan
     at import, which spec 035 makes cheap.
   - **networkx's graph atlas fails from a zip** (`nx.graph_atlas`, `nx.graph_atlas_g`): it
     opens `importlib.resources.files("networkx.generators") / "atlas.dat.gz"` with
     `gzip.open`, which takes a path, and a resource in a zip is a `Traversable`, not a path:
     `TypeError: filename must be a str or bytes object, or a file` (EXECUTED in the guest while
     drafting). It is a known gap, closed with pandas' Styler by the follow-up (Decision 15).
   - **pandas' Styler, and so `df.style` and `df.to_latex()`,** fail with
     `jinja2.exceptions.TemplateNotFound` (memo finding 4d). A known gap, closed by the
     follow-up (Decision 15). `df.to_html()` and `df.to_markdown()` work.
   - **pytz is absent** (decision 47); `zoneinfo` on the zip's tzdata is the route, as today.
   - **What is not carried:** sympy's `parse_latex` needs antlr4 or lark; pandas'
     `engine="odf"` needs odfpy; `.xlsb` needs pyxlsb (LGPL, tier D). Each raises its
     `ImportError`, as natively without them.
10. **The snapshot does not pre-import any of them.** Step 80 and `PREIMPORT` are unchanged. A
    call that imports openpyxl or sympy pays that import; a call that does not pays nothing for
    them but the directory. Pre-importing would make every call's finalization and the
    snapshot's bytes larger for packages most calls never touch, as question 34 found for
    matplotlib (+23.4 M fuel on every call). The landing notes record each family's import fuel
    on the snapshot (`import openpyxl, xlsxwriter`, `import pypdf`, `import bs4, html5lib`,
    `import yaml, jinja2, tabulate`, `import networkx, patsy`, `import sympy`, `import joblib,
    narwhals`), so a later decision has the numbers. The snapshot still changes: it holds the
    larger zip's directory (Decision 13).
11. **Seven golden jobs, one per family**, `tests/jobs/<family>.py`, each run on the plain
    binary and checked against its `.expected` like the existing five (`jobs.compare`, the
    versions line first). Each prints only what native Python prints the same way on every host
    and under both hash seeds, so:
    - container bytes that go through deflate are never printed whole (the oracle's zlib is
      1.2.12 on macOS, the guest's 1.3.1, EXECUTED: `zlib.ZLIB_RUNTIME_VERSION`); an `.xlsx` is
      shown as the SHA-256 of each of its parts, which xlsxwriter writes the same bytes for once
      its creation date is fixed (EXECUTED: two writes a second apart were equal);
    - openpyxl stamps the save time into its output (EXECUTED: two saves differed), so its
      output is read back and printed as values;
    - no line depends on whether scipy is present (spec 037 may land first or after), and none
      on the host's time zone.

    The jobs, as drafted and run (each EXECUTED natively under both seeds with equal output,
    and in the guest equal to native, with the drafting set's additions named in "Research it
    stands on"):
    - **`excel`:** xlsxwriter writes a workbook in memory with a fixed creation date (strings,
      numbers, a date with a number format, a `SUM` formula with its cached value); each part's
      SHA-256; openpyxl reads it back (rows, the formula, the cached value with
      `data_only=True`); pandas reads it with openpyxl and writes a groupby through
      `pd.ExcelWriter(…, engine="xlsxwriter", engine_kwargs={"options": {"in_memory": True}})`;
      `sales.csv` makes the same round trip; openpyxl writes a workbook after
      `tempfile.tempdir = data_dir` (the README's pattern: a writable folder for its temporary
      files) and reads it back; `xlrd.open_workbook(file_contents=<the .xlsx>)` raises xlrd's
      own `XLRDError: Excel xlsx file; not supported`.
    - **`pdf`:** a two-line PDF built in memory by the job (its own few lines of PDF syntax,
      Helvetica, no compression); `PdfReader` extracts its text; `PdfWriter` merges it with a
      second, sets a title, writes, and reads back the pages, title and texts; the written
      bytes' length and SHA-256 (pypdf compresses nothing here, and its output was the same
      bytes across runs, EXECUTED); RC4-128 encryption round trip; AES-128 raising
      `DependencyError` (Decision 9).
    - **`markup`:** one messy HTML page through `BeautifulSoup` with `html.parser` and with
      `html5lib`, CSS selectors (soupsieve); `pd.read_html(…, flavor="bs4")`; the default
      flavor's `ImportError` line; a `webencodings` lookup; `xmltodict` parse and unparse;
      `defusedxml.ElementTree` parsing a plain document and refusing an entity-expansion one
      with `EntitiesForbidden`.
    - **`text_formats`:** a YAML round trip through `safe_dump`/`safe_load`, `safe_load_all`,
      and `safe_load` refusing a `!!python/object/apply` tag; `tomli_w.dumps` read back by the
      stdlib's `tomllib`; a jinja2 template with autoescape, `StrictUndefined`, a loop and
      filters; `markupsafe.escape` and `Markup` formatting; `df.to_markdown()` and
      `tabulate(…, tablefmt="grid")`; charset-normalizer naming UTF-8, cp1252 and UTF-16 bytes
      of one German sentence and decoding each back to it.
    - **`modelling`:** networkx on Zachary's karate club (sizes, a shortest path, the top three
      by betweenness, Louvain community sizes with a fixed seed), a weighted directed graph
      (Dijkstra, topological order, a minimum spanning tree); patsy's `dmatrices("y ~ x + C(g)")`
      on a small frame, its column names and matrix, and a least-squares fit with numpy.
    - **`symbolic`:** sympy `solve`, `factor`, `expand`, `integrate` (indefinite and a Gaussian
      over the real line), `diff`, `limit`, `series`, a matrix inverse and eigenvalues, `dsolve`
      of `f'' + f = 0`, `nsimplify`, rationals, `N(pi, 40)`, `isprime(2**61 - 1)`, `latex`,
      and `lambdify` with its default modules; mpmath at 30 digits (`pi`, a quadrature,
      `zeta(3)`). The drafting run used `lambdify(…, modules="math")`, because its scratch
      `ctypes` lacked what `numpy.ctypeslib` needs (Decision 6); the built job uses the
      default, which 033's stand-in serves.
    - **`utilities`:** attrs (a validated, ordered class, `asdict`, `evolve`, a validator's
      `ValueError`); more-itertools and toolz helpers; tqdm counting into a `StringIO` and
      `format_meter` with a fixed elapsed time; `typing_extensions.TypedDict` with `NotRequired`;
      joblib `Parallel` with `n_jobs=1` and `n_jobs=2`, `Memory` caching in the data folder,
      `hash`, `dump`/`load` through a buffer; cloudpickle round-tripping a closure and a class;
      a narwhals group-by over a pandas frame.

    Each job's first line is `versions <name>=<version> …` from `importlib.metadata.version`,
    so it also proves spec 033's metadata for its family. The drafting fuel of each job on the
    plain reactor (before spec 035, on a zip of 3,765 to 3,791 members) was 2.07 G (`pdf`) to
    9.29 G (`symbolic`) (EXECUTED); the judge records the built numbers as each check's metric.

    **The oracle.** `tests/jobs/oracle/pyproject.toml` gains the thirty at the same versions,
    and `uv.lock` is regenerated with every download under `build/oracle/` (spec 002). It pins
    charset-normalizer's pure wheel by URL (`[tool.uv.sources]`), the same file as the guest.
    pyyaml and markupsafe have no pure wheel, so the oracle installs their platform wheels with
    the C speedups. No job prints which path ran, and the projects guarantee the same results
    from both, so the goldens hold; the guest's pure paths are checked separately (Decision
    12). `jobs.JOBS` gains the seven, so `regen.py` and
    `test_goldens_reproduce_under_the_pinned_oracle` cover them.
12. **The guest checks** (Acceptance lists each with how it was seen failing first).
    - **v1.3, `tests/checks/test_v1_3_default_profile.py`, a new file:** the seven
      `test_<family>_job_matches_native` checks (plain, `slow`, as the existing job checks);
      `test_the_default_profile_runs_its_pure_python_paths[plain, snapshot]`: `yaml.__with_libyaml__
      is False`, `import _yaml` raises `ModuleNotFoundError`, `markupsafe._escape_inner.__module__
      == "markupsafe._native"`, and `charset_normalizer.md.__file__` ends in `.pyc` (no mypyc
      module); `test_threadpoolctl_finds_no_native_pools[plain, snapshot]`:
      `ctypes.util.dllist() == []`, `threadpool_info() == []`, `threadpool_limits(limits=1,
      user_api="blas")` entered and left, and `ThreadpoolController().select(user_api="openmp")
      .info() == []`, all with warnings turned into errors;
      `test_pandas_styler_renders_from_the_zip[plain]` and
      `test_networkx_atlas_reads_from_the_zip[plain]`, each failing today in exactly the named
      way and each a known gap (Decision 9).
    - The helper that runs a job in the guest (`_run_job` in `test_v1_3_data_stack.py`) moves to
      `tests/harness/jobs.py` as `run_in_guest(guest, job)`, used by both files, unchanged.
    - **v1.3, spec 033's `test_packages_carry_their_metadata`:** its set of distributions gains
      the thirty, each at its `MANIFEST` version, as 033 asks of every specification that adds a
      package.
    - **v1.4, `test_excel_output_needs_a_writable_folder_or_xlsxwriter_in_memory`** in
      `tests/checks/test_v1_4_embedding.py`, through `wasi_python.run` (the runner's own
      defaults, which the judge's driver does not have: its root is writable):
      - with no root and no grant: `openpyxl.Workbook().save(io.BytesIO())` raises
        `FileNotFoundError` naming no usable temporary directory; `df.to_excel(io.BytesIO())`
        raises `xlsxwriter.exceptions.FileCreateError`; the `in_memory` writer works and its
        bytes read back through `pd.read_excel` equal the frame;
      - with `grants=[Grant(<a temporary folder>, "/tmp", writable=True)]`: openpyxl's save and
        `df.to_excel(io.BytesIO())` both work.
    - **v1.1, `test_tqdm_notice_carries_the_mpl_and_its_source`:** `LICENSES/tqdm.txt` holds
      the wheel's `LICENCE`, the pinned MPL-2.0 text byte for byte, and the `tqdm source` part
      naming the pinned wheel's file name and SHA-256.
    - **Unit, `test_the_ctypes_stand_in_names_and_refuses`** (spec 033's) gains
      `util.dllist() == []`.
13. **What it costs, stated so growth can be told from regression.**

    **Members and bytes** (EXECUTED while drafting): **+2,014 members** (Decision 1) and
    **about +16.48 MB** of zip: 16,480,467 bytes as the families' members stand alone
    (Decision 1's table), and the drafting set's zip, today's 1,751 members plus these with its
    scratch `ctypes` in place of today's, was 27,620,810 bytes against today's 11,140,635. The
    plain binary does not change. `MANIFEST` gains 30
    `package` lines and 31 `pin` lines; the `recipe` lines of `scripts/steps/70_zip.sh`,
    `scripts/00_download.sh`, `scripts/assemble_artifacts.py` and
    `recipes/ctypes_stand_in/util.py` change.

    **Fuel on a plain start.** Before spec 035, the same 2,014 members cost 156,824,942 more
    fuel on a plain `-c pass` (241,166,128 to 397,991,070; 77,867 per member; EXECUTED while
    drafting, close to the memo's 77,912). After 035 a member costs about 26,700 (its
    Decision 10, INFERRED; its check 2 bounds it at 30,000). So:

    | metric | expected (INFERRED) | cap |
    |---|---|---|
    | plain `-c pass` | +2,014 × 26,700 ≈ +53.8 M | ≤ +2,014 × 30,000 = +60.4 M |
    | every other plain check | the same, plus the collector's timing on heavy programs | ≤ +60.4 M + 0.2% of its accepted value |
    | snapshot checks that neither read metadata nor resources | ≈ +4.8 M (about 2,400 per member: spec 023's review measured +2.0% on snapshot `pass` for 681 members) | ≤ +3,500 per member, +7.0 M |
    | snapshot checks that query `importlib.metadata` | up to 6,000 per member more (035's plain slope bound) | ≤ +6,000 per member, +12.1 M |
    | the zip's `bytes` | about +16.48 MB | ≤ +17.0 MB |
    | the snapshot's `bytes` | about +0.6 to +1 MB: zipimport's dict takes 489 bytes per entry on a 64-bit host with a long archive path (EXECUTED: 936,848 bytes for 1,917 entries), less on wasm32 | ≤ +1,000 per member, +2.0 MB |
    | the plain binary's `bytes` | 0 | 0 |

    The caps use the members this change really adds, if 023 or 037 have changed the count by
    then. The pre-build review measures plain and snapshot `pass`, the snapshot's bytes and one
    metadata miss on a prototype set (033 and 035 built, this zip), as 033's review did, and its
    confirmation re-bases any cap the measurement shows to be wrong. A growth above a cap is a
    finding for the build review, not a reason to accept.

    **One of spec 035's bounds is re-based, as a judge change.** 035's check 6 bounds a missing
    `version("nope")` on the snapshot at **20 M**, set against a zip of about 1,758 members with
    9.7 M measured. Its cost grows about 4,600 fuel per member (035's Decision 7: the split of
    each name). With 023's about 610 members and these 2,014 it is about 9.7 M + 2,624 × 4,600
    ≈ 21.8 M (INFERRED), past 20 M, for growth 035 planned for ("Tier A waits for this one") but
    did not bound. The bound becomes **20 M + 6,000 × (the artifact zip's members − 1,758)**:
    the same slope 035 allows the plain binary (≤ 6,000 per member), on the snapshot too. It is
    named in `--accept-judge` with this reason. 035's other absolute bounds stay: a zone load
    and the pandas time-zone job read resources, whose cost does not grow with members after
    035 (its check 4's slope bound is 1,000 per member, about +2.6 M here at most).

    **The wheel.** The `wasi-python` wheel carries the zip, which is already deflated, so the
    wheel grows by about the zip's growth: +16.5 MB, from about 38.7 MB today (EXECUTED while
    drafting: zlib level 6 of today's three large files, 7.6 + 20.1 + 10.9 MB). The landing
    notes record the built wheel's size. PyPI refuses a file over 100.0 MiB unless the
    project's limit is raised (READ); with matplotlib, scipy and tier B the wheel nears that
    (question 64).
14. **Ordering, and one builder.** This specification changes step 70, `00_download.sh`,
    `SHA256SUMS`, `assemble_artifacts.py` and a recipe, so it is build-class and overlaps no
    other build-class change (§5.7).
    - **It builds after 033, 035 and 023.** 033 gives the metadata rule, `--metadata`,
      `tree_members` and the stand-in it extends; 035 must cut the per-member cost first
      (decision 44; sympy after it, decision 45); 023 brings `packaging` and is ahead in the
      queue (035's Decision 12). Spec 037's Decision 16 places tier A after 037 and 038; nothing
      here depends on scipy (Decision 11's jobs print nothing that scipy changes), so if 037 or
      038 stalls, this one may go first. Whichever of them builds second rebases onto the other's
      step 70, `00_download.sh` and `assemble_artifacts.py`, and adds its packages to the
      metadata set.
    - **Not split.** Thirty distributions go in through one seam (pins, `--wheel` lines, notices)
      with one rebuild, one review and one accept; splitting by family would repeat the rebuild,
      the review and the growth account seven times for no new design. One builder builds it in
      three steps, each green before the next: (1) pins, step 70, notices and the judge's
      package and licence lists, with the zip's names checked (criterion 2); (2) the seven jobs
      and the oracle; (3) the guest checks, the README, and the growth account.
15. **Two follow-ups, numbered now.**
    - **041, files read by path from a zip:** pandas' Styler (`jinja2.FileSystemLoader` on
      `Path(__file__).parent / "templates"`, `pandas/io/formats/style_render.py:75`; memo
      finding 4d) and networkx's atlas (`gzip.open` on a `Traversable`, Decision 9). Each needs
      a one-line upstream change (a `PackageLoader`; opening the resource and passing the file
      object), carried as a patch with its upstream pull request drafted (§4.1, question 32's
      "any project"). networkx comes as a wheel, so 041 also decides how a wheel takes a patch.
      It builds after this one, which brings jinja2 and networkx. It closes the two known gaps.
    - **042, seaborn and reportlab** (tier A, approved by decision 43), after 023 lands. The
      memo never ran them (no matplotlib or Pillow in its set; "Where it stopped"), so a
      specification now would rest on no executed research (§5.1). 042 first runs them in the
      guest with 023's set: seaborn needs matplotlib's writable cache folder (023's Decision 7),
      and reportlab looks for its fonts under `reportlab/fonts/` by path (INFERRED from its
      layout), which may fail from a zip as plotly's validators did. Their pins are known
      (seaborn 0.13.2, `636f8336…1987`; reportlab 5.0.1, `1c36e6bb…91e8`; both
      `py3-none-any`, READ) and would add 247 members and 3,312,570 bytes (EXECUTED while
      drafting, step 70's rules).

## Intent

An agent's code in the default profile can read and write `.xlsx` files, read and merge PDFs,
parse HTML and XML, round-trip YAML and TOML, render templates, print markdown tables, guess a
file's encoding, run graph algorithms, do symbolic maths and build model formulas, with the
utility libraries such code reaches for; every result equals native Python's, and where the
sandbox says no, the README says so first.

## Design

| file | change |
|---|---|
| `downloads/SHA256SUMS` | the 31 lines of Decision 2 |
| `scripts/00_download.sh` | the 30 package `get` lines after the three existing pure-Python pins; the MPL-2.0 text's line in the licence-notice block, under a comment naming it as a licence text tqdm's notice needs |
| `scripts/steps/70_zip.sh` | Decision 4: unpack and stage the two sdists; `--tree "$B/pure-install"`, two `--metadata` lines, 28 `--wheel` lines |
| `scripts/assemble_artifacts.py` | `PACKAGES` (+30), `WHEELS` (+28), pyyaml's and markupsafe's notices from their trees, tqdm's three-part notice (Decision 8) |
| `recipes/ctypes_stand_in/util.py` | `dllist()` returning `[]` (Decision 5) |
| `tests/jobs/{excel,pdf,markup,text_formats,modelling,symbolic,utilities}.py` and `.expected` | Decision 11; goldens written by `regen.py` |
| `tests/jobs/oracle/pyproject.toml`, `uv.lock` | the thirty, charset-normalizer's pure wheel by URL |
| `tests/harness/jobs.py` | `JOBS` gains the seven; `run_in_guest` moved here |
| `tests/harness/paths.py` | `PACKAGES` and `LICENCE_COMPONENTS` gain the thirty |
| `tests/harness/pins.py`, `tests/harness/needs.py` | `SOURCE_PATTERNS` and `SOURCE_COMPONENTS` gain `pyyaml` (`pyyaml-[\w.]+\.tar\.gz`) and `markupsafe` (`markupsafe-[\w.]+\.tar\.gz`) |
| `tests/checks/test_v1_3_default_profile.py` | new: Decision 12's v1.3 checks |
| `tests/checks/test_v1_3_data_stack.py` | uses `jobs.run_in_guest`; 033's metadata set gains the thirty |
| `tests/checks/test_v1_3_the_zips_directory.py` | check 6's snapshot bound re-based (Decision 13) |
| `tests/checks/test_v1_4_embedding.py` | the Excel check (Decision 12) |
| `tests/checks/test_v1_1_artifact_set.py` | the tqdm notice check |
| `tests/unit/test_build_scripts.py` | `dllist` in the stand-in's unit check |
| `tests/known_gaps.toml` | two gaps (the Styler, the atlas), each naming its check, its exact finding set and spec 041 as its closer (or this specification's Decision 15 if 041 is not yet drafted when this lands) |
| `.github/workflows/release.yml` | the zero-patch job's tree count gains two (to 17 after 023's 15) |
| `README.md` | below |
| `CHANGELOG.md` | under the unreleased section: the thirty, by family; the pure builds of pyyaml and markupsafe; `ctypes.util.dllist`; the Excel, `read_html`, AES, joblib and tqdm notes; the two gaps |

**The README.** A new section, **"What the default profile carries"**, after *Running it*:
- a table by family: each distribution, its version, and one line on what an agent uses it
  for; beside it numpy, pandas and the stdlib, and matplotlib and scipy as their
  specifications land;
- **"Excel files"**: reading works everywhere; writing needs either a writable folder at `/tmp`
  (`Grant(folder, "/tmp", writable=True)`, or `root=True`) or xlsxwriter in memory, with the two
  lines of Decision 9; openpyxl always needs the folder; nothing writable stays the default
  (§4.15);
- the other edges of Decision 9, one line each: `pd.read_html(…, flavor="bs4")`; pypdf's AES;
  joblib serial; tqdm's warning and `monitor_interval = 0`; threadpoolctl's empty answer;
  networkx and scipy; the Styler and the atlas until spec 041; pytz absent; what is not carried;
- the cost: a plain start pays for every member (the measured figure), a snapshot call does
  not; each package's import is paid by the call that imports it (Decision 10).

*What you get* names the zip's families; *Scope* moves tier A to "since then"; the recipe
paragraph says the `ctypes` stand-in's `util` also answers `dllist()` with `[]`; the size of
the zip the runner copies once per process is restated as built.

## Scope

In: Decisions 1 to 14. Out:
- **seaborn and reportlab:** spec 042 (Decision 15).
- **pandas' Styler (`df.style`, `df.to_latex()`) and networkx's atlas from a zip:** spec 041.
- **Tier B** (decision 48): scikit-learn, statsmodels (with formulaic, interface-meta, wrapt),
  lxml with python-docx and python-pptx, regex. lxml changes `pd.read_html`'s default flavor
  and the `markup` golden's `ImportError` line; that specification regenerates it.
- **Reading a real `.xls`.** xlrd is imported, versioned and seen refusing an `.xlsx`; no
  pinned `.xls` exists to read, and the profile has no `.xls` writer. A fixture would be a new
  pinned input for the judge alone.
- **Trimming any package** (sympy's `testing/` and `benchmarks/`, `py.typed` files): each
  member costs about 26,700 fuel on a plain start after 035; a trim needs an import trace, as
  fontTools' does (spec 023's Scope).
- **Pre-importing any of them** (Decision 10).
- **`cryptography`, `pdfminer.six`, `pdfplumber`, plotly, altair, pydantic, rich, odfpy,
  pyxlsb, pytz** and the rest of tiers C and D.
- **The PyPI file-size limit:** question 64.

## Acceptance criteria

1. **The checks exist and were seen failing first** on the set the builder starts from (033,
   035 and 023 landed), each recorded in the landing notes:
   - the seven `test_<family>_job_matches_native`: `ModuleNotFoundError` for each family's
     first package;
   - `test_the_default_profile_runs_its_pure_python_paths`: `ModuleNotFoundError: yaml`;
   - `test_threadpoolctl_finds_no_native_pools`: `ModuleNotFoundError: threadpoolctl`; and,
     with the built zip but 033's `util.py` without `dllist`, `OSError: ctypes is unavailable
     on wasm32-wasi`;
   - `test_excel_output_needs_a_writable_folder_or_xlsxwriter_in_memory`:
     `ModuleNotFoundError: openpyxl`;
   - `test_tqdm_notice_carries_the_mpl_and_its_source`: no `LICENSES/tqdm.txt`; and against a
     copy of the built set whose notice lacks the MPL text;
   - `test_packages_carry_their_metadata` and `test_licence_notices_cover_every_component`
     with the thirty added: the thirty missing;
   - the two known-gap checks fail in exactly their named way (`TemplateNotFound`; the
     atlas's `TypeError`) and are recorded as gaps;
   - the unit check's `dllist` assertion: `AttributeError` against 033's `util.py`.
2. **The zip's names and bytes.** A full build from pins in a clean clone gives a
   `python.wasm` byte for byte the one it started from (`cmp`). With the starting set copied to
   `$OLD`:
   - `diff` of the two sorted name lists (`unzip -Z1 … | LC_ALL=C sort`) shows only added
     names, exactly the 2,014 a script computes from the pins with step 70's rules (the
     drafting computation, rerun against `downloads/`), and none removed;
   - every shared member is the same bytes (spec 033's criterion 2 command), so no existing
     member changed;
   - pyyaml's and markupsafe's `METADATA` equal their `PKG-INFO` (`cmp`), and each wheel's
     `METADATA` equals the one in its pinned wheel.
3. **The same bytes everywhere.** A manual run of the release workflow on the reviewed commit
   passes its `rebuild` and `same-bytes` jobs (spec 012) and its zero-patch job with the new
   tree count; its run number goes in the landing notes. Steps 70 to 90, re-run with a
   `.DS_Store` in `build/pure-install/yaml/` and beside each `PKG-INFO` (spec 018), give the
   same `SHA256SUMS` (`cmp`).
4. **The judge.** `uv run pytest` is green with `--accept "<reason>"`, `--accept-judge "<the
   new checks, jobs and goldens; the package, licence and source-tree lists; the moved helper;
   035's check 6 re-based, with Decision 13's reason; the two gaps>"` and `--accept-growth
   "<the account>"`, and loses no pass. The account gives the build's measured numbers for each
   row of Decision 13's table against its expectation and cap, the member count actually added,
   and the snapshot's metadata miss against both the old 20 M and the re-based bound. The
   goldens reproduce under the pinned oracle (`regen.py --check`).
5. **The numbers recorded.** The landing notes give: plain and snapshot `-c pass`; each
   family's import fuel on the snapshot (Decision 10); each job's fuel; the zip's, the
   snapshot's and the wheel's sizes.
6. **The release.** A release dry run passes every job (criterion 3's run).

## The owner's choices

None open here. The owner's decisions 43 (tier A and its licences), 45 (sympy after spec 035),
46 (Excel output documented, nothing writable kept) and 47 (no pytz) are applied as written.
One fact this specification found is beyond its scope and recorded as question 64 in
`../questions-for-the-owner.md`: the wheel nears PyPI's 100 MiB file limit as the profile grows.
Nothing here waits on it.

## Landing notes

Not built.
