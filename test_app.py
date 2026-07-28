import subprocess, time, sys, requests

proc = subprocess.Popen([sys.executable, 'app.py'], cwd='D:\\capstone\\findme')
time.sleep(4)

session = requests.Session()

try:
    r = session.post('http://localhost:5000/login', data={
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
