import pytest
import subprocess
import time
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.constants import Config

@pytest.fixture(scope="session", autouse=True)
def start_test_server():
    """Starts the FastAPI server in a subprocess for testing"""
    # Set up test database path
    test_db_path = os.path.join(os.path.dirname(__file__), 'test_focusguard.db')
    env = os.environ.copy()
    env["FOCUSGUARD_DB_PATH"] = test_db_path
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        
    # Start server
    server_process = subprocess.Popen(
        [sys.executable, "run_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env
    )
    
    # Wait for server to be ready
    base_url = f"http://localhost:{Config.SERVER_PORT}"
    max_retries = 60
    ready = False
    
    for _ in range(max_retries):
        try:
            response = requests.get(f"{base_url}/", timeout=1)
            if response.status_code == 200:
                ready = True
                break
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)
            
    if not ready:
        server_process.terminate()
        stdout, stderr = server_process.communicate()
        print(f"Server stdout:\n{stdout.decode()}")
        print(f"Server stderr:\n{stderr.decode()}")
        raise RuntimeError(f"Test server failed to start.\nSTDOUT:\n{stdout.decode()}\nSTDERR:\n{stderr.decode()}")
        
    yield
    
    # Teardown
    server_process.terminate()
    server_process.wait(timeout=5)
    
    # Cleanup test database
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
