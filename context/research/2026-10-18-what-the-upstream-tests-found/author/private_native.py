import pickle, numpy as np
m = np._core._multiarray_umath
SF = m._get_sfloat_dtype()
np._ScaledFloatTestDType = SF  # pickle finds the type by its repr, as numpy's own test does
d = pickle.loads(pickle.dumps(SF(2.0)))
print("sfloat", type(d).__name__, d.get_scaling())
c = m._get_castingimpl(np.dtypes.Float64DType, np.dtypes.Int64DType)
print("castingimpl", type(c).__name__, c._supports_unaligned)
print("scalar_input", m._array_converter(1, [2]).scalar_input)
