import sys, os
sys.path.insert(0, '/m')
os.mkdir('/m')
open('/m/a.py', 'w').write('A = 1')
import a
open('/m/b.py', 'w').write('B = 2')
import b
print(a.A, b.B)
