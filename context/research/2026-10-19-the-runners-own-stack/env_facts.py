"""The host's thread stacks: the main thread's, a default Python thread's, and the soft limit."""
import json, resource, sys, threading, platform
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from stackrun import thread_stack_bytes
out = {"platform": sys.platform, "machine": platform.machine(), "libc": platform.libc_ver(),
       "python": sys.version.split()[0], "main_thread_stack": thread_stack_bytes(),
       "rlimit_stack_soft": resource.getrlimit(resource.RLIMIT_STACK)[0],
       "threading_stack_size_default": threading.stack_size()}
box = {}
t = threading.Thread(target=lambda: box.update(s=thread_stack_bytes())); t.start(); t.join()
out["default_thread_stack"] = box["s"]
print(json.dumps(out))
