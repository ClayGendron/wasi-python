"""Probe 6: the home thread's wait. The main thread waits on a queue in 50 ms slices while another
thread works; SIGINT is sent to the main thread from a third. (a) A handler that only sets a flag
runs during the wait; (b) Python's default handler raises KeyboardInterrupt inside the wait, where
the loop catches it; (c) the same with an untimed wait. Counts slices, never time."""
import queue, signal, sys, threading, time

def scenario(handler, timed):
    q = queue.SimpleQueue(); flag = {"set": False}; caught = []
    if handler == "flag":
        old = signal.signal(signal.SIGINT, lambda s, f: flag.update(set=True))
    else:
        old = signal.signal(signal.SIGINT, signal.default_int_handler)
    stop = threading.Event()
    def worker():
        while not stop.is_set(): sum(range(1000))  # holds and drops the GIL, like a busy host thread
        q.put("done")
    def kicker():
        time.sleep(0.2); signal.pthread_kill(threading.main_thread().ident, signal.SIGINT)
    w = threading.Thread(target=worker); k = threading.Thread(target=kicker); w.start(); k.start()
    slices_after = None; slices = 0; escaped = False
    try:
      while True:
        try:
            item = q.get(timeout=0.05) if timed else q.get()
            break
        except queue.Empty:
            slices += 1
        except KeyboardInterrupt as e:
            caught.append(e); stop.set()
            continue
        if flag["set"] and slices_after is None:
            slices_after = slices; stop.set()
    except KeyboardInterrupt:
        escaped = True; stop.set()  # landed outside the loop's own try: between two bytecodes
    w.join(); k.join(); signal.signal(signal.SIGINT, old)
    return {"handler": handler, "timed": timed, "flag_seen": flag["set"], "keyboard_interrupt_caught": len(caught), "escaped_the_loop": escaped}

print(sys.version.split()[0], sys.platform)
for h, t in (("flag", True), ("default", True), ("default", False)):
    print(scenario(h, t), flush=True)
