import importlib.util, os
spec = importlib.util.spec_from_file_location("bis", os.path.join(os.path.dirname(__file__), "bis.py"))
bis = importlib.util.module_from_spec(spec); spec.loader.exec_module(bis)
CASES = {f"binop_{n}": bis.CASES["eval_binop"][0](n) for n in (300, 1000, 3000, 10000, 30000)}
CASES.update({f"parse_binop_{n}": bis.c("s = '1' + '+1' * N", "import ast; ast.parse(s)")[0](n) for n in (3000, 30000)})
