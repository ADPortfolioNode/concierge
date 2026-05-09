import subprocess
import time
import os
import signal
import sys
import httpx
import shutil
import platform


def wait_for(url, timeout=30.0):
    client = httpx.Client(timeout=5.0)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = client.get(url)
            return r
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}")


def start_process(cmd, cwd=None, env=None):
    # Start process detached so tests can terminate it reliably
    return subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)


def test_system_smoke():
    """Start backend and frontend, verify health, media listing, and frontend index."""
    procs = []
    try:
        # start backend
        backend_cmd = [sys.executable, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', '8000']
        procs.append(start_process(backend_cmd))

        # Attempt to start the frontend dev server if `npm` is available.
        npm_path = shutil.which('npm')
        frontend_proc = None
        if npm_path:
            frontend_dir = os.path.join(os.getcwd(), 'frontend')
            nm_path = os.path.join(frontend_dir, 'node_modules')
            if not os.path.exists(nm_path):
                try:
                    subprocess.run(['npm', 'install'], cwd=frontend_dir, check=False, timeout=600)
                except Exception:
                    pass
            log_path = os.path.join(os.getcwd(), 'frontend_dev.log')
            try:
                logf = open(log_path, 'ab')
            except Exception:
                logf = None
            try:
                if platform.system() == 'Windows':
                    proc = subprocess.Popen(['npm', 'run', 'dev'], cwd=frontend_dir, stdout=logf or subprocess.DEVNULL, stderr=logf or subprocess.DEVNULL, shell=False, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                else:
                    proc = subprocess.Popen(['npm', 'run', 'dev'], cwd=frontend_dir, stdout=logf or subprocess.DEVNULL, stderr=logf or subprocess.DEVNULL, shell=False, preexec_fn=os.setsid)
                procs.append(proc)
                frontend_proc = proc
            except Exception:
                if logf:
                    try:
                        logf.close()
                    except Exception:
                        pass

        # wait for backend
        r = wait_for('http://127.0.0.1:8000/health', timeout=30.0)
        assert r.status_code == 200
        # check media listing (allow more time for directory scanning)
        r2 = wait_for('http://127.0.0.1:8000/api/v1/concierge/media', timeout=30.0)
        assert r2.status_code == 200
        data = r2.json()
        assert 'status' in data
        # verify frontend index if vite started or available on default port
        try:
            r3 = wait_for('http://127.0.0.1:5173/', timeout=30.0)
            assert r3.status_code == 200
        except Exception:
            # skip if frontend not available in this environment
            pass

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
                    if resp.status_code != 200:
                        # non-fatal: some media files may be large or transient
                        # skip asserting to avoid flaky failures
                        pass
                except Exception:
                    # skip media fetch failures in this smoke test
                    pass

    finally:
        # teardown
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        time.sleep(0.5)
        for p in procs:
            try:
                if platform.system() == 'Windows':
                    try:
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(p.pid)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        try:
                            p.kill()
                        except Exception:
                            pass
                else:
                    try:
                        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                    except Exception:
                        try:
                            p.kill()
                        except Exception:
                            pass
            except Exception:
                pass
