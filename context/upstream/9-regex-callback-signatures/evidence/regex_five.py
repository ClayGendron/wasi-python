import regex, pickle
p = regex.compile(r"(?P<a>\w)(?P<b>\d)+")
m = p.match("x12")
print(p.groupindex)
print(pickle.loads(pickle.dumps(p)).pattern)
print(m.capturesdict())
print(m.allcaptures())
print(m.allspans())
