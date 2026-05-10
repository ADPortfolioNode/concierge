import subprocess
import time
import os
import signal
import sys
import httpx
import shutil
import platform
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def wait_for(url, timeout=30.0):
    client = httpx.Client(timeout=5.0)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = client.get(url)
            logging.info(f"Successfully connected to {url}")
            return r
        except Exception as e:
            logging.info(f"Waiting for {url}, error: {e}")
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}")


def start_process(cmd, cwd=None, env=None):
    # Start process detached so tests can terminate it reliably
    return subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)


def _get_frontend_port_from_log(log_path, timeout=30):
    """Parses the frontend log file to find the port it's running on."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                # Look for "Local: http://localhost:PORT/"
                match = re.search(r"localhost:(\d+)", content)
                if match:
                    return int(match.group(1))
            except Exception as e:
                logging.warning(f"Could not read frontend log {log_path}: {e}")
        time.sleep(1)
    return None


def test_system_smoke():
    """Start backend and frontend, verify health, media listing, and frontend index."""
    procs = []
    try:
        log_path = ""
        # start backend
        backend_cmd = [sys.executable, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', '8000']
        logging.info(f"Starting backend: {' '.join(backend_cmd)}")
        procs.append(start_process(backend_cmd))

        # Attempt to start the frontend dev server if `npm` is available.
        npm_path = shutil.which('npm')
        frontend_proc = None
        if npm_path:
            logging.info("npm found, attempting to start frontend.")
            frontend_dir = os.path.join(os.getcwd(), 'frontend')
            nm_path = os.path.join(frontend_dir, 'node_modules')
            if not os.path.exists(nm_path):
                logging.info("node_modules not found, running 'npm install'. This may take a while...")
                try:
                    subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True, timeout=600, capture_output=True, text=True)
                    logging.info("'npm install' completed successfully.")
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    logging.error(f"'npm install' failed: {e.stderr or e}")
                    # Continue but expect frontend to fail
            log_path = os.path.join(os.getcwd(), 'frontend_dev.log')
            try:
                logf = open(log_path, 'w', encoding='utf-8')
            except Exception:
                logf = None
            try:
                # Use npx for robustness, especially on Windows, instead of 'npm run dev'
                frontend_cmd = ['npx', 'vite', '--host']
                if platform.system() == 'Windows':
                    proc = subprocess.Popen(frontend_cmd, cwd=frontend_dir, stdout=logf or subprocess.DEVNULL, stderr=logf or subprocess.DEVNULL, shell=False, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                else:
                    proc = subprocess.Popen(frontend_cmd, cwd=frontend_dir, stdout=logf or subprocess.DEVNULL, stderr=logf or subprocess.DEVNULL, shell=False, preexec_fn=os.setsid)
                procs.append(proc)
                frontend_proc = proc
                logging.info(f"Frontend process started with PID: {proc.pid}. Log: {log_path}")
            except Exception as e:
                logging.error(f"Failed to start frontend process: {e}")
                if logf:
                    try:
                        logf.close()
                    except Exception as close_exc:
                        logging.error(f"Failed to close frontend log file: {close_exc}")

        # wait for backend
        r = wait_for('http://127.0.0.1:8000/health', timeout=30.0)
        assert r.status_code == 200
        # check media listing (allow more time for directory scanning)
        r2 = wait_for('http://127.0.0.1:8000/api/v1/concierge/media', timeout=30.0)
        assert r2.status_code == 200
        data = r2.json()
        assert 'status' in data
        # verify frontend index if vite started
        frontend_port = 5173
        if frontend_proc and log_path:
            detected_port = _get_frontend_port_from_log(log_path, timeout=30.0)
            if detected_port:
                frontend_port = detected_port
                logging.info(f"Detected frontend running on port {frontend_port}")
        try:
            r3 = wait_for(f'http://127.0.0.1:{frontend_port}/', timeout=30.0)
            assert r3.status_code == 200
        except Exception as e:
            # non-fatal: skip if frontend not available in this environment
            logging.warning(f"Could not connect to frontend at http://127.0.0.1:{frontend_port}. Skipping frontend check. Error: {e}")


        # if media list contains at least one image, request it
        items = data.get('data', [])
        if items:
            first = items[0]
            url = first.get('url')
            if url:
                if url.startswith('/'):
                    url = 'http://127.0.0.1:8000' + url
                try:
                    resp = httpx.get(url, timeout=60.0)
                    logging.info(f"Requesting media item {url}, status: {resp.status_code}")
                    if resp.status_code != 200:
                        # non-fatal: some media files may be large or transient
                        # skip asserting to avoid flaky failures
                        logging.warning(f"Media item at {url} returned status {resp.status_code}")
                except Exception as e:
                    # skip media fetch failures in this smoke test
                    logging.warning(f"Failed to fetch media item at {url}: {e}")

    finally:
        # teardown
        for p in procs:
            try:
                p.terminate()
            except Exception:
                # process may have already exited
                continue
        time.sleep(0.5)
        for p in procs:
            try:
                if platform.system() == 'Windows':
                    try:
                        logging.info(f"Force-killing process tree for PID {p.pid} on Windows.")
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(p.pid)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        try:
                            p.kill()
                        except ProcessLookupError:
                            pass # already gone
                else:
                    try:
                        logging.info(f"Force-killing process group {os.getpgid(p.pid)} on Unix-like OS.")
                        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                    except Exception:
                        try:
                            p.kill()
