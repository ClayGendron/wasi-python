// numpy's float_status.hpp pattern (C++): constexpr masks from FE_*, unqualified feraiseexcept,
// then a later <cfenv> and a std:: call, to show both spellings compile and reach one word.
#include <fenv.h>
#include <cfenv>

namespace np {
struct FloatStatus {
#ifdef FE_OVERFLOW
    static constexpr int kOverflow = FE_OVERFLOW;
#else
    static constexpr int kOverflow = 0;
#endif
    static void RaiseOverflow() {
        if constexpr (kOverflow != 0) {
            feraiseexcept(kOverflow);
        }
    }
};
}  // namespace np

extern "C" void raise_overflow_cpp(void) { np::FloatStatus::RaiseOverflow(); }
#ifdef FE_OVERFLOW
extern "C" int test_overflow_std(void) { return std::fetestexcept(FE_OVERFLOW) != 0; }
#else
extern "C" int test_overflow_std(void) { return -1; }  // wasi-libc defines no FE_OVERFLOW
#endif
