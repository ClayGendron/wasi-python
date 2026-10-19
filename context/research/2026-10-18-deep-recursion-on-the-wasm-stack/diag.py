import os
def w(s): return f"os.write(2, b'{s}\\n')"
CASES = {
 "json_steps": "import os, json\nl = []\nfor i in range(100000): l = [l]\n" + w("built") + "\ns = json.dumps(l)\n" + w("dumped") + "\ndel s\n" + w("dels") + "\nl = None\n" + w("freed"),
 "list_free": "import os\nl = []\nfor i in range(100000): l = [l]\n" + w("built") + "\nl = None\n" + w("freed"),
 "list_free_1e4": "import os\nl = []\nfor i in range(10000): l = [l]\n" + w("built") + "\nl = None\n" + w("freed"),
 "tuple_free": "import os\nt = ()\nfor i in range(100000): t = (t,)\n" + w("built") + "\nt = None\n" + w("freed"),
 "dict_free": "import os\nd = {}\nfor i in range(100000): d = {'k': d}\n" + w("built") + "\nd = None\n" + w("freed"),
}
