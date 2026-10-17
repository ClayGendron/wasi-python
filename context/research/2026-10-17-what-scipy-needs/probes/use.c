#include <stdio.h>
extern void lib_routine_(int *n);                 /* the caller's gfortran-style declaration */
typedef void (*fp)(int *);
int main(void) {
  volatile fp f = (fp)(char *)lib_routine_;       /* address taken, as f2py's FortranDataDef table does */
  int n = 41; f(&n); printf("indirect call returned, n=%d\n", n); return 0;
}
