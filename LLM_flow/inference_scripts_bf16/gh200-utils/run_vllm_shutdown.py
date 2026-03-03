# ################################ Example usage #####################################
# ------------------------------------------------------------------------------------
# python3 -u run_vllm_shutdown.py
# ------------------------------------------------------------------------------------

# REF: https://gist.github.com/mdonkers/63e115cc0c79b4f6b8b3a6b797e485c7

import subprocess, time, signal


def get_vllm_serve_pid_strs():
    resp = subprocess.run(["ps aux | grep 'vllm serve'"], shell=True, stdout=subprocess.PIPE).stdout.decode("utf-8")
    resp_list = [[c for c in l.split(' ') if len(c) > 0] for l in resp.split("\n")]
    pid_strs = [l[1] for l in resp_list if len(l) >= 2]
    return pid_strs


if __name__ == "__main__":
    vllm_serve_pid_strs = get_vllm_serve_pid_strs()
    while len(vllm_serve_pid_strs) > 0:
        for pid_str in vllm_serve_pid_strs:
            subprocess.run(['kill -15 '+pid_str], shell=True)
        time.sleep(5)
        vllm_serve_pid_strs = get_vllm_serve_pid_strs()
    signal.raise_signal(signal.SIGTERM)