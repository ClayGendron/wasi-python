# Runs inside the guest: report interpreter configuration as JSON.
import sys, os, json
r = {}
r['path'] = list(sys.path)
r['flags'] = {k: getattr(sys.flags, k) for k in dir(sys.flags) if not k.startswith('_') and k not in ('count', 'index', 'n_fields', 'n_sequence_fields', 'n_unnamed_fields')}
r['prefix'] = sys.prefix; r['exec_prefix'] = sys.exec_prefix; r['base_prefix'] = sys.base_prefix
r['executable'] = sys.executable; r['stdlib_dir'] = getattr(sys, '_stdlib_dir', None)
r['environ'] = dict(os.environ)
r['hash_info'] = {k: getattr(sys.hash_info, k) for k in ('width', 'modulus', 'algorithm', 'hash_bits', 'seed_bits', 'cutoff')}
r['hash_abc'] = hash('abc'); r['hash_bytes'] = hash(b'wasi')
r['cwd'] = os.getcwd()
try: r['listdir_root'] = sorted(os.listdir('/'))
except OSError as e: r['listdir_root'] = repr(e)
try: r['listdir_usr_local_lib'] = sorted(os.listdir('/usr/local/lib'))
except OSError as e: r['listdir_usr_local_lib'] = repr(e)
r['site_in_modules'] = 'site' in sys.modules
r['random_preimported'] = 'random' in sys.modules
import random
r['random_bits'] = random.getrandbits(64)
r['urandom'] = os.urandom(8).hex()
r['meta_path'] = [type(f).__name__ if not isinstance(f, type) else f.__name__ for f in sys.meta_path]
r['path_hooks'] = [getattr(h, '__name__', type(h).__name__) for h in sys.path_hooks]
r['n_modules'] = len(sys.modules)
r['platform'] = sys.platform
r['dont_write_bytecode'] = sys.dont_write_bytecode
r['pycache_prefix'] = sys.pycache_prefix
r['breakpointhook_env'] = os.environ.get('PYTHONBREAKPOINT')
print(json.dumps(r, sort_keys=True))
