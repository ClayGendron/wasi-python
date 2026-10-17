#include <thread>
#include <mutex>
#include <condition_variable>
#include <atomic>
std::mutex m; std::atomic<int> a{0};
int f() { std::lock_guard<std::mutex> g(m); std::thread t([]{ a++; }); t.join(); return a; }
int main() { return f(); }
