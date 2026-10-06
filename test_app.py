import subprocess, time, sys, re, requests

proc = subprocess.Popen([sys.executable, 'app.py'], cwd=r'D:\New folder\findme')
time.sleep(4)

session = requests.Session()

try:
    # Fetch the login page first to obtain the CSRF token (Flask-WTF)
    r = session.get('http://localhost:5000/login', timeout=10)
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text)
    token = m.group(1) if m else ''
    print(f'GET /login: {r.status_code} (csrf token: {"found" if token else "MISSING"})')

    r = session.post('http://localhost:5000/login', data={
        'csrf_token': token,
        'email': 'admin@cavendish.ac.ug',
        'password': 'password123'
    }, allow_redirects=False)
    print(f'POST /login: {r.status_code}')

    for page in ['/dashboard', '/admin/matches', '/admin/lost-items', '/admin/found-items', '/match/1', '/item/lost/1']:
        try:
            r = session.get(f'http://localhost:5000{page}', timeout=10)
            print(f'{page}: {r.status_code}')
        except Exception as e:
            print(f'{page}: ERROR {e}')

    print('\nDone')
except Exception as e:
    print(f'Error: {e}')
finally:
    proc.terminate()
    proc.wait()
