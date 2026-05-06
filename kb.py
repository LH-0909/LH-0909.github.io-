import json
import os
import requests

# ─── 配置 ───
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO = os.environ.get('GITHUB_REPO', 'lh-0909/LH-0909.github.io-')

# 本地文件路径
SCHOOL_FILE = os.path.join(os.path.dirname(__file__), "knowledge_base.json")
SCORE_FILES = {
    2024: os.path.join(os.path.dirname(__file__), "hebei_2024_scores.json"),
    2025: os.path.join(os.path.dirname(__file__), "hebei_2025_scores.json"),
}

# 远程文件路径（仓库里的名字）
SCORE_REMOTE_PATHS = {
    2024: "hebei_2024_scores.json",
    2025: "hebei_2025_scores.json",
}

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
# 年份变量（新增年份只需改上面的 SCORE_FILES / SCORE_REMOTE_PATHS / YIFENYIDANG_FILES 三个字典）
SCORE_YEARS_DESC = sorted(SCORE_FILES.keys(), reverse=True)
SCORE_YEARS_ASC  = sorted(SCORE_FILES.keys())

print("📡 正在检查远程分数数据...")
for year in SCORE_YEARS_ASC:
    local_path = SCORE_FILES[year]
    remote_path = SCORE_REMOTE_PATHS.get(year, '')
    if not remote_path:
        continue
    content, sha = download_file_from_github(GITHUB_REPO, remote_path, GITHUB_TOKEN)
    if content:
        try:
            remote_data = json.loads(content)
            local_data = load_json(local_path)
            if len(remote_data) > len(local_data):
                print(f"✅ {year}年远程数据更新，正在下载...")
                save_json(local_path, remote_data)
            else:
                print(f"📂 {year}年本地数据已是最新。")
        except Exception as e:
            print(f"⚠ 处理{year}年远程数据出错: {e}")
    else:
        print(f"⚠ 无法获取{year}年远程数据，将使用本地版本（如果存在）。")

# 年份变量（新增年份只需改上面的 SCORE_FILES / SCORE_REMOTE_PATHS / YIFENYIDANG_FILES 三个字典）
SCORE_YEARS_DESC = sorted(SCORE_FILES.keys(), reverse=True)  # 搜索/检索用，新→旧
SCORE_YEARS_ASC  = sorted(SCORE_FILES.keys())               # 展示用，旧→新

# 加载数据
KB_SCHOOLS = load_json(SCHOOL_FILE)
KB_SCORES = {year: load_json(path) for year, path in SCORE_FILES.items()}
_score_summary = '  '.join(f'{y}年:{len(KB_SCORES[y])}条' for y in SCORE_YEARS_DESC)
print(f"📚 学校信息: {len(KB_SCHOOLS)} 条，录取分数: {_score_summary}")

# ─── 一分一段表 ───
import re
import zipfile
import xml.etree.ElementTree as ET

YIFENYIDANG_FILES = {
    2024: os.path.join(os.path.dirname(__file__), "2024河北一分一段.xlsx"),
    2025: os.path.join(os.path.dirname(__file__), "河北一分一段2025.xlsx"),
}
YIFENYIDANG_JSON = {y: p.replace('.xlsx', '.json') for y, p in YIFENYIDANG_FILES.items()}
YIFENYIDANG_YEARS = sorted(YIFENYIDANG_FILES.keys())

def _parse_xlsx_yifenyidang(filepath):
    """解析一分一段 xlsx，返回 {'物理': {分数: 累计人数}, '历史': {...}}。
    自动处理两种格式：2024(左右分列) / 2025(上下堆叠)。"""
    z = zipfile.ZipFile(filepath)
    # 读取共享字符串
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        tree = ET.parse(z.open('xl/sharedStrings.xml'))
        ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        for si in tree.findall('.//s:si', ns):
            texts = [t.text or '' for t in si.findall('.//s:t', ns)]
            shared.append(''.join(texts))

    tree = ET.parse(z.open('xl/worksheets/sheet1.xml'))
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    rows = tree.findall('.//s:row', ns)

    def _cell_text(row, idx):
        """获取行中第 idx 列(0-based)的文本值"""
        for c in row.findall('s:c', ns):
            ref = c.get('r', '')
            col_letter = re.match(r'[A-Z]+', ref).group() if ref else ''
            if not col_letter:
                continue
            col_idx = 0
            for ch in col_letter:
                col_idx = col_idx * 26 + (ord(ch) - ord('A') + 1)
            col_idx -= 1  # 0-based
            if col_idx == idx:
                val = c.find('s:v', ns)
                if val is not None and val.text:
                    if c.get('t', '') == 's':
                        idx_s = int(val.text)
                        return shared[idx_s] if idx_s < len(shared) else ''
                    return val.text
        return ''

    all_rows_text = []
    for row in rows:
        cells = []
        for c in row.findall('s:c', ns):
            val = c.find('s:v', ns)
            if val is not None and val.text:
                t = c.get('t', '')
                if t == 's':
                    idx_s = int(val.text)
                    cells.append(shared[idx_s] if idx_s < len(shared) else '')
                else:
                    cells.append(val.text)
            else:
                cells.append('')
        all_rows_text.append(cells)

    result = {'物理': {}, '历史': {}}

    # 检测格式：「物理」和「历史」出现在同一行的不同单元格 → 2024左右分列
    # 注意：2025标题行"物理类和历史类"在同一单元格，不能误判
    has_both = False
    for row_text in all_rows_text[:5]:
        has_phy = any('物理' in str(c) and '历史' not in str(c) for c in row_text)
        has_his = any('历史' in str(c) and '物理' not in str(c) for c in row_text)
        if has_phy and has_his:
            has_both = True
            break

    if has_both:
        # 2024 格式：左右分列 (5列: 分数, 物理人数, 物理累计, 历史人数, 历史累计)
        for cells in all_rows_text:
            if not cells or len(cells) < 5:
                continue
            score_str = str(cells[0]).strip()
            m = re.search(r'(\d+)', score_str)
            if not m:
                continue
            score = int(m.group(1))
            try:
                wl_cum = int(float(str(cells[2]))) if cells[2] and str(cells[2]).strip() else None
                ls_cum = int(float(str(cells[4]))) if cells[4] and str(cells[4]).strip() else None
            except (ValueError, TypeError):
                continue
            if wl_cum is not None and wl_cum > 0:
                result['物理'][score] = wl_cum
            if ls_cum is not None and ls_cum > 0:
                result['历史'][score] = ls_cum
    else:
        # 2025 格式：上下堆叠 (3列: 分数, 人数, 累计)
        current_group = '物理'
        for cells in all_rows_text:
            combined = ' '.join(str(c) for c in cells)
            if '历史' in combined and '物理' not in combined:
                current_group = '历史'
                continue
            if not cells or len(cells) < 3:
                continue
            score_str = str(cells[0]).strip()
            m = re.search(r'(\d+)', score_str)
            if not m:
                continue
            score = int(m.group(1))
            try:
                cum = int(float(str(cells[2]))) if cells[2] and str(cells[2]).strip() else None
            except (ValueError, TypeError):
                continue
            if cum is not None and cum > 0:
                result[current_group][score] = cum

    z.close()
    return result

# 转换 xlsx → json（首次运行自动转换）
for year, xlsx_path in YIFENYIDANG_FILES.items():
    json_path = YIFENYIDANG_JSON[year]
    if not os.path.exists(xlsx_path):
        print(f"⚠ 缺少{year}年一分一段xlsx文件: {xlsx_path}")
        continue
    if not os.path.exists(json_path) or os.path.getmtime(xlsx_path) > os.path.getmtime(json_path):
        print(f"🔄 正在解析{year}年一分一段xlsx...")
        data = _parse_xlsx_yifenyidang(xlsx_path)
        save_json(json_path, data)
        print(f"✅ {year}年一分一段已转换: 物理{len(data['物理'])}条, 历史{len(data['历史'])}条")

# 加载一分一段
YIFENYIDANG = {}
for year in YIFENYIDANG_YEARS:
    json_path = YIFENYIDANG_JSON[year]
    if os.path.exists(json_path):
        YIFENYIDANG[year] = load_json(json_path)
        # 确保键是 int
        for kelei in ['物理', '历史']:
            if kelei in YIFENYIDANG[year]:
                YIFENYIDANG[year][kelei] = {int(k): v for k, v in YIFENYIDANG[year][kelei].items()}
        print(f"📊 {year}年一分一段已加载: 物理{len(YIFENYIDANG[year].get('物理',{}))}条, 历史{len(YIFENYIDANG[year].get('历史',{}))}条")
    else:
        YIFENYIDANG[year] = {'物理': {}, '历史': {}}
        print(f"⚠ {year}年一分一段数据未加载")

# ─── 位次换算 ───
def score_to_rank(score, year, kelei):
    """分数→位次（累计人数），找不到返回最近分数的位次"""
    table = YIFENYIDANG.get(year, {}).get(kelei, {})
    if not table:
        return None
    score = int(score)
    # 精确匹配或向下找
    for s in range(score, -1, -1):
        if s in table:
            return table[s]
    return None

def rank_to_score(rank, year, kelei):
    """位次→分数，找到该位次对应的最低分"""
    table = YIFENYIDANG.get(year, {}).get(kelei, {})
    if not table:
        return None
    rank = int(rank)
    # 从高到低找第一个累计 >= rank 的分数
    for s in sorted(table.keys(), reverse=True):
        if table[s] >= rank:
            return s
    return None

def _get_score_range_for_year(user_score, user_kelei, target_year):
    """用户分数 → 用户位次 → 目标年份对应分数段(lo, hi)"""
    if not YIFENYIDANG:
        return user_score - 25, user_score + 25  # fallback
    # 使用最近年份做基准换算
    base_year = max(YIFENYIDANG.keys())  # 2025
    rank = score_to_rank(user_score, base_year, user_kelei)
    if rank is None:
        return user_score - 25, user_score + 25
    # 用位次在目标年份找对应分数
    target_score = rank_to_score(rank, target_year, user_kelei)
    if target_score is None:
        return user_score - 25, user_score + 25
    return target_score - 15, target_score + 15  # ±15分用于过滤

# 下面的 search_kb 和 format_kb_results 不动，和之前一样
def _extract_score(query: str):
    """从查询中提取分数数字，返回 (分数, None) 或 (None, None)"""
    import re
    # 匹配 "560分" "560" "500-550" 等模式
    m = re.search(r'(\d{3})(?:\s*[-–到至]\s*(\d{3}))?', query)
    if m:
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        return min(lo, hi), max(lo, hi)
    return None, None

def _detect_kelei(query: str):
    """检测查询中的科类倾向"""
    if any(w in query for w in ['物理', '理科', '物理组', '物化生', '物化地', '物生地']):
        return '物理'
    if any(w in query for w in ['历史', '文科', '历史组', '史地政', '史政生']):
        return '历史'
    return None

def _bigrams(text: str):
    """生成 2-gram 集合，用于中文匹配"""
    return {text[i:i+2] for i in range(len(text) - 1)}

def _build_search_text_score(item):
    """构建录取分数条目的搜索文本"""
    return ' '.join([
        item.get('院校名称', ''),
        item.get('专业名称', ''),
        item.get('科类', ''),
    ])

def _build_search_text_school(item):
    """构建学校信息条目的搜索文本"""
    return ' '.join([
        item.get('name', ''),
        item.get('type', ''),
        item.get('city', ''),
        item.get('belong', ''),
    ])

# ─── 专业别名映射 ───
SYNONYM_MAP = {
    # 计算机
    '编程': '计算机 软件 信息 网络工程 数据科学 人工智能 智能科学 信息安全 物联网 数字媒体',
    '码农': '计算机 软件 信息', '程序员': '计算机 软件 信息', '写代码': '计算机 软件 信息',
    'IT': '计算机 软件 信息 网络', '互联网': '计算机 软件 信息',
    # 医学
    '医生': '临床医学 口腔医学 麻醉学 儿科学 医学影像 中医学 中西医 基础医学 护理学',
    '看病': '临床医学 口腔医学', '临床': '临床医学', '护士': '护理学',
    '药': '药学 中药学 药物制剂',
    # 金融/经济
    '金融': '金融学 金融工程 经济学 保险学 会计学 财务管理 国际经济 投资学',
    '银行': '金融学 金融工程 经济学', '投资': '金融学 经济学 投资学',
    '赚钱': '金融学 经济学 会计学 财务管理', '理财': '金融学 经济学 会计学',
    # 师范/教育
    '当老师': '师范 教育学 汉语言文学 数学与应用数学 英语 物理学 化学 生物科学 历史学',
    '教师': '师范 教育学', '考编': '师范 教育学 汉语言文学',
    # 法学
    '律师': '法学 知识产权', '打官司': '法学',
    # 考公/体制
    '公务员': '法学 汉语言文学 行政管理 会计学 计算机 经济学',
    '体制内': '法学 汉语言文学 行政管理 会计学',
    # 电子/半导体
    '芯片': '电子信息 集成电路 微电子 电子科学 通信 光电信息',
    '5G': '电子信息 通信', '半导体': '电子信息 集成电路 微电子',
    # 建筑/土木
    '盖房子': '土木 建筑学 城乡规划', '建筑': '建筑学 土木 城乡规划',
    # 设计/艺术
    '画画': '美术学 设计 数字媒体 动画',
    # 传媒
    '播音': '播音与主持 广播电视', '新闻': '新闻学 广播电视 传播学',
}

def _expand_query(query: str):
    """用同义词映射扩展查询词"""
    parts = [query]
    for key, aliases in SYNONYM_MAP.items():
        if key in query:
            parts.append(aliases)
    return ' '.join(parts)

def _score_item(item, q_bigrams):
    """计算单条记录的 bigram 匹配分"""
    search_text = _build_search_text_score(item)
    overlap = len(q_bigrams & _bigrams(search_text))
    if overlap == 0:
        return 0
    school_name = item.get('院校名称', '')
    school_overlap = len(q_bigrams & _bigrams(school_name))
    return overlap + school_overlap * 2

def search_kb(query: str, top_n: int = 10):
    # 提取过滤条件
    score_lo, score_hi = _extract_score(query)
    kelei = _detect_kelei(query)

    # 扩展查询 + bigram
    expanded = _expand_query(query)
    q_bigrams = _bigrams(expanded)

    # ─── 分别搜两年数据，按 (院校, 专业, 科类) 合并 ───
    merged = {}  # key: (院校名称, 专业名称, 科类) -> {2024: {item, score}, 2025: {...}}
    key_order = []

    for year in SCORE_YEARS_DESC:  # 最新年份优先
        # 位次校准：用户分数用一分一段换算为目标年份的等价分数段
        if score_lo is not None and kelei:
            yr_lo, yr_hi = _get_score_range_for_year(score_lo, kelei, year)
        else:
            yr_lo, yr_hi = (score_lo - 25) if score_lo else None, (score_hi + 25) if score_hi else None

        for item in KB_SCORES.get(year, []):
            # 科类过滤
            if kelei and item.get('科类', '') != kelei:
                continue
            # 分数段过滤（位次校准后）
            if yr_lo is not None:
                try:
                    item_score = float(item.get('最低分', 0))
                except (ValueError, TypeError):
                    item_score = 0
                if item_score < yr_lo or item_score > yr_hi:
                    continue

            match = _score_item(item, q_bigrams)
            if match == 0:
                continue

            school = item.get('院校名称', '')
            major = item.get('专业名称', '')
            cat = item.get('科类', '')
            key = (school, major, cat)

            if key not in merged:
                merged[key] = {}
                key_order.append(key)
            merged[key][year] = {'item': item, 'score': match}

    # ─── 计算综合分 ───
    scored = []
    for key in key_order:
        entry = merged[key]
        s25 = entry.get(2025, {}).get('score', 0)
        s24 = entry.get(2024, {}).get('score', 0)
        total = s25 * 1.5 + s24
        scored.append((total, key, entry))

    scored.sort(key=lambda x: x[0], reverse=True)

    # ─── 构建结果（附位次） ───
    results = []
    for _, key, entry in scored[:top_n]:
        school, major, cat = key
        result = {'类型': '录取分数', '院校名称': school, '专业名称': major, '科类': cat}
        for year in SCORE_YEARS_ASC:
            if year in entry:
                score_val = entry[year]['item'].get('最低分', '')
                result[f'最低分_{year}'] = score_val
                # 附上位次
                try:
                    rank_val = score_to_rank(int(float(score_val)), year, cat)
                    if rank_val:
                        result[f'位次_{year}'] = rank_val
                except (ValueError, TypeError):
                    pass
        results.append(result)

    # ─── 学校信息 ───
    school_results = []
    for item in KB_SCHOOLS:
        overlap = len(q_bigrams & _bigrams(_build_search_text_school(item)))
        if overlap > 0:
            school_results.append((overlap, item))
    school_results.sort(key=lambda x: x[0], reverse=True)
    for _, item in school_results[:3]:
        results.append({'类型': '学校信息', **item})

    return results

def format_kb_results(results):
    if not results:
        return ''

    score_items = [r for r in results if r.get('类型') == '录取分数']
    school_items = [r for r in results if r.get('类型') == '学校信息']

    # 用户位次参考（取最高分年）
    user_rank_hint = ''
    if score_items:
        for item in score_items:
            for year in SCORE_YEARS_DESC:
                rk = item.get(f'位次_{year}', '')
                if rk:
                    user_rank_hint = f'（位次=全省排名，位次越小数越稳）'
                    break
            if user_rank_hint:
                break

    parts = []
    if score_items:
        parts.append(f'【河北省录取数据 2024→2025对比 {user_rank_hint}】')
        for i, item in enumerate(score_items, 1):
            school = item.get('院校名称', '?')
            major = item.get('专业名称', '?')
            cat = item.get('科类', '')
            s24 = item.get('最低分_2024', '')
            s25 = item.get('最低分_2025', '')
            rk24 = item.get('位次_2024', '')
            rk25 = item.get('位次_2025', '')

            line = f'{i}. {school} · {major}（{cat}）'
            if s24 and s25:
                try:
                    diff = int(float(s25)) - int(float(s24))
                    arrow = '↑' + str(diff) if diff > 0 else ('↓' + str(abs(diff)) if diff < 0 else '→')
                except (ValueError, TypeError):
                    arrow = ''
                line += f' 2024:{s24}分(位{rk24}) → 2025:{s25}分(位{rk25}) {arrow}'
            elif s25:
                line += f' 2025:{s25}分(位{rk25})（新增）'
            else:
                line += f' 2024:{s24}分(位{rk24})'
            parts.append(line)

    if school_items:
        parts.append('')
        parts.append('【相关院校背景】')
        for i, item in enumerate(school_items, 1):
            parts.append(f'{i}. {item.get("name", "")} | {item.get("type", "")} | {item.get("city", "")} | {item.get("level", "")}')

    return '\n'.join(parts)