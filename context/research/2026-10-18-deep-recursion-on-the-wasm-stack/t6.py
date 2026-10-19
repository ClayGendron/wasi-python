CASES = {
"named_check": "import sys\nsys.setrecursionlimit(10**8)\ndef f(n): return f(n + 1)\nf(0)",
"named_check_counted": "import sys, os\nsys.setrecursionlimit(10**8)\ndef f(n):\n    if n % 1000 == 0: os.write(2, b'%d\\n' % n)\n    return f(n + 1)\ntry:\n    f(0)\nexcept RecursionError as e:\n    print('RecursionError', e)",
"list_free_1e5": "l = []\nfor i in range(100000): l = [l]\nl = None\nprint('freed')",
}
