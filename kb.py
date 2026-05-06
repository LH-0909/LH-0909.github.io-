import json
import os
import requests

# ─── 配置 ───
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO = os.environ.get('GITHUB_REPO', 'lh-0909/LH-0909.github.io-')

# 本地文件路径
SCHOOL_FILE = os.path.join(os.path.dirname(__file__), "knowledge_base.json")
SCORE_FILE = os.path.join(os.path.dirname(__file__), "hebei_2024_scores.json")

# 远程文件路径（仓库里的名字）
SCORE_REMOTE_PATH = "hebei_2024_scores.json"

def download_file_from_github(repo, path, token=''):
    """从 GitHub 下载文件内容，返回 (内容文本, sha)"""
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            import base64
            content = base64.b64decode(data['content']).decode('utf-8')
            return content, data['sha']
        else:
            print(f"⚠ GitHub 下载失败，状态码: {resp.status_code}")
    except Exception as e:
        print(f"⚠ GitHub 请求异常: {e}")
    return None, None

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── 启动时自动同步 ───
print("📡 正在检查远程分数数据...")
content, sha = download_file_from_github(GITHUB_REPO, SCORE_REMOTE_PATH, GITHUB_TOKEN)
if content:
    try:
        remote_data = json.loads(content)
        local_data = load_json(SCORE_FILE)
        if len(remote_data) > len(local_data):
            print("✅ 远程数据更新，正在下载...")
            save_json(SCORE_FILE, remote_data)
        else:
            print("📂 本地分数数据已是最新。")
    except Exception as e:
        print(f"⚠ 处理远程数据出错: {e}")
else:
    print("⚠ 无法获取远程分数数据，将使用本地版本（如果存在）。")

# 加载数据
KB_SCHOOLS = load_json(SCHOOL_FILE)
KB_SCORES = load_json(SCORE_FILE)
print(f"📚 学校信息: {len(KB_SCHOOLS)} 条，录取分数: {len(KB_SCORES)} 条")

# 下面的 search_kb 和 format_kb_results 不动，和之前一样
def search_kb(query: str, top_n: int = 5):
    results = []
    query_words = set(query)
    for item in KB_SCHOOLS:
        search_text = (
            item.get("name", "") + " " +
            item.get("type", "") + " " +
            item.get("city", "") + " " +
            item.get("belong", "")
        )
        score = sum(1 for w in query_words if w in search_text)
        if score > 0:
            results.append((score, {"类型": "学校信息", **item}))
    for item in KB_SCORES:
        search_text = (
            item.get("院校名称", "") + " " +
            item.get("专业名称", "") + " " +
            item.get("科类", "")
        )
        score = sum(1 for w in query_words if w in search_text)
        if score > 0:
            results.append((score, {"类型": "录取分数", **item}))
    results.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in results[:top_n]]

def format_kb_results(results):
    if not results:
        return "知识库中暂无相关数据。"
    parts = ["【知识库参考数据】\n"]
    for i, item in enumerate(results, 1):
        if item.get("类型") == "学校信息":
            parts.append(f"{i}. 🏫 {item.get('name', '未知学校')}")
            parts.append(f"   类型: {item.get('type', '')} | 城市: {item.get('city', '')}")
            parts.append(f"   层次: {item.get('level', '')} | 隶属: {item.get('belong', '')}\n")
        elif item.get("类型") == "录取分数":
            parts.append(f"{i}. 📊 {item.get('院校名称', '')} - {item.get('专业名称', '')}")
            parts.append(f"   科类: {item.get('科类', '')} | 最低分: {item.get('最低分', '')}")
            parts.append(f"   年份: 2024 (河北省)\n")
    return "\n".join(parts)