      subroutine daxpy1(n, a, x, y)
      integer n, i
      double precision a, x(n), y(n)
      do 10 i = 1, n
         y(i) = y(i) + a*x(i)
   10 continue
      end
