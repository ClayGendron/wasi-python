long double f(long double a, long double b, int n) {
  long double x = 1, y = 0;
  while (n--) {
    long double t = x*a - y*b;
    y = x*b + y*a;
    x = t;
  }
  return x + y;
}
