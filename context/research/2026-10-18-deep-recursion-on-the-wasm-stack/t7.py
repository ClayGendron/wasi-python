CASES = {
"interp": """
try:
    import _interpreters
    print("has _interpreters")
    from concurrent import interpreters
    i = interpreters.create()
    i.exec("class A:\\n    def __repr__(self): return repr(self)\\ntry:\\n    repr(A())\\nexcept RecursionError as e:\\n    print('sub RecursionError', e)")
    print("sub done")
except Exception as e:
    print(type(e).__name__, e)
""",
"limits": "import sys; print(sys.getrecursionlimit())",
}
