#include <mutex>
#include <atomic>
std::mutex m; std::atomic<int> a{0};
int main() { std::lock_guard<std::mutex> g(m); return a++; }
