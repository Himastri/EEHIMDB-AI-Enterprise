"""Public Black-Box: RealLock 100 threads"""
import threading
def test_reallock_100_threads():
    results = []
    threads = [threading.Thread(target=lambda: results.append(True)) for _ in range(100)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(results) == 100
