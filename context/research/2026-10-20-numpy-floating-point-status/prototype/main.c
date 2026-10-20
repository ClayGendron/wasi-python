#include <stdio.h>

int get_status(void);
int clear_status(void);
void set_invalid(void);
void set_divbyzero(void);
void raise_overflow_cpp(void);
int test_overflow_std(void);

int main(void) {
    volatile double zero = 0.0, one = 1.0;
    volatile double x = one / zero; /* hardware division by zero: wasm sets no flag */
    (void)x;
    printf("after 1.0/0.0: status %d\n", get_status());
    set_invalid();
    printf("after set_invalid: status %d\n", get_status());
    set_divbyzero();
    printf("after set_divbyzero: status %d\n", get_status());
    printf("clear returns %d, then status %d\n", clear_status(), get_status());
    raise_overflow_cpp();
    printf("after C++ RaiseOverflow: status %d, std::fetestexcept(FE_OVERFLOW) %d\n", get_status(),
           test_overflow_std());
    clear_status();
    printf("after clear: status %d\n", get_status());
    return 0;
}
