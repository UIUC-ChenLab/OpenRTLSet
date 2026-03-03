# ################################ Example usage #####################################
# ------------------------------------------------------------------------------------
# python3 -u wait_for_vllm.py --vllm_host 127.0.0.1 --vllm_port 8000
# ------------------------------------------------------------------------------------

import requests, time, argparse

PRINT_INFO = True
QUERY_INTERVAL_SECONDS = 1

def check_vllm_health(host, port):
    url = f"http://{host}:{port}/health"
    try:
        return requests.get(url, timeout=5).status_code == 200
    except Exception as e:
        # print(e)
        return False

if __name__ == "__main__":
    # parse vLLM info
    parser = argparse.ArgumentParser()
    parser.add_argument("--vllm_host", type=str, help="vLLM hostname, e.g., 127.0.0.1")
    parser.add_argument("--vllm_port", type=int, help="vLLM port, e.g., 8000")
    args = parser.parse_args()
    # wait for vLLM to be online
    vllm_online = False
    if PRINT_INFO:
        print("Waiting for vLLM startup at:", f"http://{args.vllm_host}:{args.vllm_port}", end=' ')
    while not vllm_online:
        vllm_online = check_vllm_health(host=args.vllm_host, port=args.vllm_port)
        if vllm_online:
            break
        if PRINT_INFO:
            print(".", end='')
        time.sleep(QUERY_INTERVAL_SECONDS)
    if PRINT_INFO:
        print("\nvLLM startup completed at:", f"http://{args.vllm_host}:{args.vllm_port}")
