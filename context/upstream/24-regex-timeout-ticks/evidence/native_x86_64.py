import platform, time, regex
print(platform.machine(), regex.__version__)
for t in (1.0, 1e12, 1e13, 1e30, float("inf")):
    t0 = time.monotonic()
    try:
        r = regex.search(r"(a|aa)+$", "a" * 22 + "!", timeout=t)
        print("timeout", t, "-> completed", r, round(time.monotonic() - t0, 3))
    except TimeoutError as e:
        print("timeout", t, "-> TimeoutError", round(time.monotonic() - t0, 3))
