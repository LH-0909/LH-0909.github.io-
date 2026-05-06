"""
张雪峰升学顾问 - 后端服务器
部署到 AutoDL 或其他 Linux 服务器:
  pip install flask flask-cors
  export GITHUB_TOKEN=ghp_xxx
  python server.py
"""
import os, json, base64, logging, requests
from flask import Flask, request, jsonify
from kb import search_kb, format_kb_results
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# ─── Config ───
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')      # GitHub Token（必填）
GITHUB_REPO = os.environ.get('GITHUB_REPO', '')        # 仓库名，如 lh-0909/LH-0909.github.io-
USERS_PATH  = os.environ.get('USERS_PATH', 'users.json')
SESSIONS_PATH = os.environ.get('SESSIONS_PATH', 'sessions.json')
PORT = int(os.environ.get('PORT', 5000))

# ─── GitHub helpers ───
GH_API = 'https://api.github.com'

def _gh_headers():
    return {'Authorization': f'Bearer {GITHUB_TOKEN}', 'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'}

def _b64decode(s):
    try: return base64.b64decode(s).decode('utf-8')
    except: return s

def _b64encode(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8')

def _gh_get(path):
    """Fetch and decode a file from GitHub."""
    url = f'{GH_API}/repos/{GITHUB_REPO}/contents/{path}'
    resp = requests.get(url, headers=_gh_headers())
    if not resp.ok:
        return None, resp.status_code, resp.json().get('message', 'unknown error')
    data = resp.json()
    content = _b64decode(data['content'])
    try: content = json.loads(content)
    except: pass
    return {'data': content, 'sha': data['sha']}, 200, None

def _gh_put(path, content, sha=None, message='Update'):
    """Save data to GitHub. Returns (success, status_code, error_message)."""
    url = f'{GH_API}/repos/{GITHUB_REPO}/contents/{path}'
    body = {'message': message, 'content': _b64encode(json.dumps(content, ensure_ascii=False, indent=2)), 'branch': 'main'}
    if sha: body['sha'] = sha
    resp = requests.put(url, headers=_gh_headers(), json=body)
    if resp.ok:
        return True, 200, None
    return False, resp.status_code, resp.json().get('message', 'unknown error')

# ─── Login ───
@app.route('/api/login', methods=['POST'])
def login():
    """验证用户名密码，返回用户信息"""
    if not GITHUB_REPO:
        return jsonify({'ok': False, 'error': 'Server not configured (GITHUB_REPO missing)'}), 500

    body = request.json or {}
    username = body.get('username', '').strip()
    password = body.get('password', '').strip()
    if not username or not password:
        return jsonify({'ok': False, 'error': '用户名和密码不能为空'}), 400

    result, status, err = _gh_get(USERS_PATH)
    if result is None:
        return jsonify({'ok': False, 'error': f'无法读取用户数据: {err}'}), 500

    users = result['data']
    user = users.get(username)
    if not user:
        return jsonify({'ok': False, 'error': '用户名不存在'}), 401
    if user.get('password') != password:
        return jsonify({'ok': False, 'error': '密码错误'}), 401

    # Don't return all users to non-admin
    if user.get('role') == 'admin':
        return jsonify({'ok': True, 'user': {'username': username, 'role': user.get('role', 'user')}, 'users': users}), 200
    return jsonify({'ok': True, 'user': {'username': username, 'role': user.get('role', 'user')}}), 200

# ─── Users management ───
@app.route('/api/users', methods=['GET'])
def get_users():
    """获取所有用户（需要 admin 权限的后续版本可加 token 验证）"""
    if not GITHUB_REPO:
        return jsonify({'ok': False, 'error': 'Server not configured'}), 500
    result, status, err = _gh_get(USERS_PATH)
    if result is None:
        return jsonify({'ok': False, 'error': f'读取失败: {err}'}), status
    # Remove passwords from response
    users = result['data']
    safe = {}
    for k, v in users.items():
        if k == '_app_config': safe[k] = v; continue
        safe[k] = {'role': v.get('role', 'user'), 'createdAt': v.get('createdAt', '')}
    return jsonify({'ok': True, 'users': safe, '_sha': result['sha']}), 200

@app.route('/api/users', methods=['POST'])
def save_user():
    """创建/更新用户"""
    if not GITHUB_REPO:
        return jsonify({'ok': False, 'error': 'Server not configured'}), 500
    body = request.json or {}
    username = body.get('username', '').strip()
    if not username:
        return jsonify({'ok': False, 'error': '用户名不能为空'}), 400

    # Fetch current
    result, status, err = _gh_get(USERS_PATH)
    if result is None:
        return jsonify({'ok': False, 'error': f'读取失败: {err}'}), status
    users = result['data']
    sha = result['sha']

    if body.get('action') == 'delete':
        if username == 'admin':
            return jsonify({'ok': False, 'error': '不能删除 admin'}), 403
        users.pop(username, None)
    else:
        users[username] = {
            'password': body.get('password', ''),
            'role': body.get('role', 'user'),
            'createdAt': body.get('createdAt', __import__('datetime').datetime.now().isoformat())
        }

    ok, _, err2 = _gh_put(USERS_PATH, users, sha, f'Update user {username}')
    if not ok:
        return jsonify({'ok': False, 'error': f'保存失败: {err2}'}), 500
    return jsonify({'ok': True}), 200

@app.route('/api/users/batch', methods=['POST'])
def save_users_batch():
    """批量保存用户"""
    if not GITHUB_REPO:
        return jsonify({'ok': False, 'error': 'Server not configured'}), 500
    body = request.json or {}
    users = body.get('users', {})
    message = body.get('message', 'Batch update users')
    if not users:
        return jsonify({'ok': False, 'error': 'users is required'}), 400
    # Fetch current for SHA
    result, _, _ = _gh_get(USERS_PATH)
    sha = result['sha'] if result else None
    ok, _, err = _gh_put(USERS_PATH, users, sha, message)
    if not ok:
        return jsonify({'ok': False, 'error': f'保存失败: {err}'}), 500
    return jsonify({'ok': True}), 200

# ─── Sessions ───
@app.route('/api/sessions/<username>', methods=['GET'])
def get_sessions(username):
    """获取指定用户的会话"""
    if not GITHUB_REPO:
        return jsonify({'ok': False, 'sessions': []}), 200  # Graceful fallback
    result, status, err = _gh_get(SESSIONS_PATH)
    if result is None:
        return jsonify({'ok': True, 'sessions': []}), 200  # File may not exist yet
    all_sessions = result['data']
    return jsonify({'ok': True, 'sessions': all_sessions.get(username, []), '_sha': result['sha']}), 200

@app.route('/api/sessions/<username>', methods=['PUT'])
def save_sessions(username):
    """保存指定用户的会话"""
    if not GITHUB_REPO:
        return jsonify({'ok': False, 'error': 'Server not configured'}), 500
    body = request.json or {}
    sessions_data = body.get('sessions', [])

    # Fetch current
    result, status, err = _gh_get(SESSIONS_PATH)
    sha = None
    all_sessions = {}
    if result is not None:
        all_sessions = result['data']
        sha = result['sha']
    all_sessions[username] = sessions_data
    ok, _, err2 = _gh_put(SESSIONS_PATH, all_sessions, sha, f'Update sessions for {username}')
    if not ok:
        return jsonify({'ok': False, 'error': f'保存失败: {err2}'}), 500
    return jsonify({'ok': True}), 200

# ─── Sync config (用于快速配置跨设备) ───
@app.route('/api/config', methods=['GET'])
def get_config():
    """返回 _app_config 用于快速配置"""
    result, _, _ = _gh_get(USERS_PATH)
    if result and '_app_config' in result['data']:
        return jsonify({'ok': True, 'config': result['data']['_app_config']}), 200
    return jsonify({'ok': False}), 404

# ─── Health check ───
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'ok': True, 'configured': bool(GITHUB_TOKEN and GITHUB_REPO)}), 200


# ─── Knowledge Base Search ───
@app.route('/api/kb-search', methods=['POST'])
def kb_search():
    body = request.json or {}
    query = body.get('query', '')
    if not query:
        return jsonify({'ok': False, 'error': 'query 不能为空'}), 400
    results = search_kb(query)
    formatted = format_kb_results(results)
    return jsonify({
        'ok': True,
        'results': results,
        'formatted': formatted,
        'count': len(results)
    })
# ─── Auto-sync ngrok URL on startup ───
def sync_ngrok_url():
    """Detect current ngrok public URL and update GitHub _app_config so all devices can discover it."""
    import urllib.request
    try:
        ngrok_resp = urllib.request.urlopen('http://127.0.0.1:4040/api/tunnels', timeout=3)
        tunnels = json.loads(ngrok_resp.read()).get('tunnels', [])
        ngrok_url = ''
        for t in tunnels:
            if t.get('config', {}).get('addr', '').endswith(str(PORT)):
                ngrok_url = t.get('public_url', '')
                break
        if not ngrok_url and tunnels:
            ngrok_url = tunnels[0].get('public_url', '')

        if not ngrok_url:
            logging.warning('ngrok URL not detected (ngrok not running or API unavailable)')
            return

        logging.info(f'Detected ngrok URL: {ngrok_url}')

        # Fetch current users.json
        result, _, _ = _gh_get(USERS_PATH)
        if not result:
            logging.warning('Cannot fetch users.json, skip ngrok URL sync')
            return

        users = result['data']
        sha = result['sha']
        old_url = users.get('_app_config', {}).get('serverUrl', '')
        if old_url == ngrok_url:
            logging.info('ngrok URL unchanged, skip update')
            return

        if '_app_config' not in users:
            users['_app_config'] = {}
        users['_app_config']['serverUrl'] = ngrok_url
        ok, _, err = _gh_put(USERS_PATH, users, sha, 'Auto-update ngrok URL')
        if ok:
            logging.info(f'Updated _app_config.serverUrl → {ngrok_url}')
        else:
            logging.warning(f'Failed to update _app_config: {err}')
    except Exception as e:
        logging.warning(f'sync_ngrok_url failed: {e}')

if __name__ == '__main__':
    print(f'''\n{'='*50}
  张雪峰升学顾问 - 后端服务
  Port: {PORT}
  Repo: {GITHUB_REPO or '(未配置)'}
  Token: {'已设置' if GITHUB_TOKEN else '(未设置！)'}
{'='*50}\n''')
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print('⚠ 警告：请设置环境变量 GITHUB_TOKEN 和 GITHUB_REPO\n')
    sync_ngrok_url()
    app.run(host='0.0.0.0', port=PORT, debug=False)
