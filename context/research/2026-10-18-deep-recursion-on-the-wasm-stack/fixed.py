"""The depth cases of bis.py at fixed depths, each leaving with os._exit(0) (freeing excluded),
plus freeing alone at fixed depths."""
import importlib.util, os
spec = importlib.util.spec_from_file_location("bis", os.path.join(os.path.dirname(__file__), "bis.py"))
bis = importlib.util.module_from_spec(spec); spec.loader.exec_module(bis)
CASES = {}
for name, n in [("repr_list", 100000), ("json_dumps", 100000), ("json_loads", 100000), ("pickle_dumps", 100000),
                ("eq_list", 100000), ("hash_tuple", 100000), ("eval_unary", 100000), ("eval_parens", 199),
                ("eval_binop", 100000), ("map_chain", 100000), ("exc_group", 10000),
                ("list_free", 10000), ("list_free", 100000), ("dict_free", 10000), ("tuple_free", 10000)]:
    CASES[f"{name}_{n}"] = bis.CASES[name][0](n)
