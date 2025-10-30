import requests
import threading
import time

# Module 2 service endpoint (ClusterIP service)
SERVICE_URL = "http://module-2-sample-app-service:8000/"
REQUESTS_PER_THREAD = 50
THREAD_COUNT = 5
DELAY_BETWEEN_REQUESTS = 0.1  # seconds

def send_requests(thread_id):
    success = 0
    for i in range(REQUESTS_PER_THREAD):
        try:
            response = requests.get(SERVICE_URL, timeout=5)
            if response.status_code == 200:
                success += 1
        except Exception as e:
            print(f"[Thread {thread_id}] Request failed: {e}")
        time.sleep(DELAY_BETWEEN_REQUESTS)
    print(f"[Thread {thread_id}] Completed {REQUESTS_PER_THREAD} requests, Success: {success}")

def main():
    threads = []
    start_time = time.time()
    print("Starting stress test on Module 2 app...")

    for i in range(THREAD_COUNT):
        t = threading.Thread(target=send_requests, args=(i+1,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    end_time = time.time()
    total_requests = REQUESTS_PER_THREAD * THREAD_COUNT
    print(f"Stress test completed. Total requests: {total_requests}")
    print(f"Total time: {end_time - start_time:.2f} seconds")
    print(f"Approx. requests per second: {total_requests / (end_time - start_time):.2f}")

if __name__ == "__main__":
    main()
