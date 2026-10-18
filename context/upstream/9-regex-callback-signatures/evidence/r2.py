import regex, pickle, hashlib
b = pickle.dumps(regex.compile(r"(?P<a>\w)+", regex.I), protocol=5)
print(len(b), hashlib.sha256(b).hexdigest()[:16], regex._regex.__name__, regex._regex.compile.__module__)
