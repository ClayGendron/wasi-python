#include <thread>
#include <cstdio>
#include <system_error>
int main() {
  std::printf("hardware_concurrency=%u\n", std::thread::hardware_concurrency());
  try { std::thread t([]{}); t.join(); std::puts("spawned"); }
  catch (const std::system_error& e) { std::printf("system_error: %s\n", e.what()); }
  return 0;
}
