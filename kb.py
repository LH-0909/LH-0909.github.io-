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

# 加载学科评估
SUBJECT_EVAL_FILE = os.path.join(os.path.dirname(__file__), "subject_evaluation.json")
SUBJECT_EVALUATIONS = load_json(SUBJECT_EVAL_FILE) if os.path.exists(SUBJECT_EVAL_FILE) else {}

# 构建学校名称查找索引（normalize后→原始key）
def _normalize_school_name(name):
    import re
    return re.sub(r'[（(][^)）]*[)）]|[\s\-]', '', name)

_SCHOOL_EVAL_INDEX = {}
for sname in SUBJECT_EVALUATIONS:
    _SCHOOL_EVAL_INDEX[_normalize_school_name(sname)] = sname

def _lookup_eval(school_name):
    """查找某所学校的学科评估数据，带缓存"""
    n = _normalize_school_name(school_name)
    if n in _EVAL_CACHE:
        return _EVAL_CACHE[n]
    if n in _SCHOOL_EVAL_INDEX:
        result = SUBJECT_EVALUATIONS[_SCHOOL_EVAL_INDEX[n]]
        _EVAL_CACHE[n] = result
        return result
    for key, val in _SCHOOL_EVAL_INDEX.items():
        if key in n or n in key:
            result = SUBJECT_EVALUATIONS[val]
            _EVAL_CACHE[n] = result
            return result
    _EVAL_CACHE[n] = {}
    return {}

def _match_subject_grade(school_name, major_name):
    """匹配专业名到学科评估等级，返回如 '计算机科学与技术 A+' 或 ''"""
    evals = _lookup_eval(school_name)
    if not evals:
        return ''
    # 专业名→学科关键词映射
    MAJOR_TO_SUBJECT = {
        '计算机': '计算机科学与技术', '软件': '软件工程', '人工智能': '计算机科学与技术',
        '电子信息': '电子科学与技术', '通信': '信息与通信工程', '电子': '电子科学与技术',
        '电气': '电气工程', '自动化': '控制科学与工程',
        '机械': '机械工程', '车辆': '机械工程',
        '土木': '土木工程', '建筑': '建筑学',
        '数学': '数学', '物理': '物理学', '化学': '化学', '生物': '生物学',
        '临床医学': '临床医学', '口腔': '口腔医学', '护理': '护理学', '药学': '药学',
        '法学': '法学', '经济': '应用经济学', '金融': '应用经济学', '会计': '工商管理',
        '工商管理': '工商管理', '管理科学': '管理科学与工程',
        '中文': '中国语言文学', '汉语言': '中国语言文学', '英语': '外国语言文学',
        '新闻': '新闻传播学', '传播': '新闻传播学',
        '材料': '材料科学与工程', '化工': '化学工程与技术',
        '环境': '环境科学与工程', '食品': '食品科学与工程',
        '力学': '力学', '航空': '航空宇航科学与技术', '航天': '航空宇航科学与技术',
        '交通运输': '交通运输工程', '船舶': '船舶与海洋工程',
        '水利': '水利工程', '测绘': '测绘科学与技术',
        '地质': '地质资源与地质工程', '矿业': '矿业工程',
        '农学': '作物学', '植物': '植物保护', '动物': '畜牧学', '兽医': '兽医学',
        '设计': '设计学', '美术': '美术学',
    }
    for mkey, subj in MAJOR_TO_SUBJECT.items():
        if mkey in major_name:
            grade = evals.get(subj, '')
            if grade:
                return f'{subj} {grade}'
    return ''

print(f"📊 学科评估: {len(SUBJECT_EVALUATIONS)} 所学校")

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

# ─── 省份列表（用于检测用户查询中的省份） ───
# 当前知识库仅有河北省录取数据，检测到其他省份需要明确提示
KNOWN_PROVINCES = {
    '河北', '河南', '山东', '山西', '陕西', '江苏', '浙江', '广东', '湖北', '湖南',
    '四川', '安徽', '福建', '江西', '辽宁', '吉林', '黑龙江', '云南', '贵州',
    '甘肃', '青海', '海南', '内蒙古', '西藏', '宁夏', '新疆', '广西',
    '北京', '上海', '天津', '重庆',
}
# 当前已有录取数据的省份（后续扩展只需加到这里）
AVAILABLE_PROVINCES = {'河北'}

def _extract_province(query: str):
    """从查询中提取用户提到的省份，返回 (省份名称, 是否有数据) 或 (None, True)"""
    for p in KNOWN_PROVINCES:
        if p in query:
            return p, p in AVAILABLE_PROVINCES
    return None, True  # 未提省份，不触发警告

def _extract_score(query: str):
    """从查询中提取分数数字，返回 (分数, None) 或 (None, None)"""
    import re
    m = re.search(r'(\d{3})(?:\s*[-–到至]\s*(\d{3}))?', query)
    if m:
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        return min(lo, hi), max(lo, hi)
    return None, None

def _detect_kelei(query: str):
    """检测查询中的科类倾向"""
    if any(w in query for w in ['物理', '理科', '理科生', '物理组', '物化生', '物化地', '物生地', '物化', '选物理']):
        return '物理'
    if any(w in query for w in ['历史', '文科', '文科生', '历史组', '史地政', '史政生', '选历史']):
        return '历史'
    return None

# ─── 学校档次索引 ───
_SCHOOL_TIER = {}  # normalized_name -> {tier_score, is_985, is_211, is_df, tags, rank}

for _ti in KB_SCHOOLS:
    _tn = _normalize_school_name(_ti.get('name', ''))
    if not _tn:
        continue
    _tags = _ti.get('tags', '')
    _is_985 = '985' in _tags
    _is_211 = '211' in _tags
    _is_df = '双一流' in _tags
    _ts = 15 if _is_985 else (8 if _is_211 else (5 if _is_df else 0))
    _SCHOOL_TIER[_tn] = {
        'tier_score': _ts, 'is_985': _is_985, 'is_211': _is_211, 'is_df': _is_df,
        'tags': _tags, 'rank_软科': _ti.get('rank_软科', 999),
        'subjects': _ti.get('双一流学科', []),
    }

_TIER_CACHE = {}
_EVAL_CACHE = {}

def _get_tier_score(school_name):
    """查学校档次加分（0-15），带缓存"""
    n = _normalize_school_name(school_name)
    if n in _TIER_CACHE:
        return _TIER_CACHE[n]
    if n in _SCHOOL_TIER:
        _TIER_CACHE[n] = _SCHOOL_TIER[n]['tier_score']
        return _TIER_CACHE[n]
    for key, val in _SCHOOL_TIER.items():
        if key in n or n in key:
            _TIER_CACHE[n] = val['tier_score']
            return val['tier_score']
    _TIER_CACHE[n] = 0
    return 0

def _get_tier_info(school_name):
    """查学校完整档次信息，带缓存"""
    n = _normalize_school_name(school_name)
    cache_key = '__info__' + n
    if cache_key in _TIER_CACHE:
        return _TIER_CACHE[cache_key]
    if n in _SCHOOL_TIER:
        _TIER_CACHE[cache_key] = _SCHOOL_TIER[n]
        return _SCHOOL_TIER[n]
    for key, val in _SCHOOL_TIER.items():
        if key in n or n in key:
            _TIER_CACHE[cache_key] = val
            return val
    default = {'tier_score': 0, 'is_985': False, 'is_211': False, 'is_df': False, 'tags': '', 'rank_软科': 999, 'subjects': []}
    _TIER_CACHE[cache_key] = default
    return default

# ═══════════════════════════════════════════════════════════════
# 高性能检索加速：倒排索引 + LRU缓存 + 预计算
# ═══════════════════════════════════════════════════════════════

# ─── bi/trigram 函数（必须提前定义，索引构建依赖它们）───
def _bigrams(text: str):
    return {text[i:i+2] for i in range(len(text) - 1)}

def _trigrams(text: str):
    return {text[i:i+3] for i in range(len(text) - 2)}

# ─── 预分区（物理/历史分开，避免每次查询都过滤科类）───
_SCORES_BY_KELEI = {'物理': {y: [] for y in SCORE_YEARS_ASC}, '历史': {y: [] for y in SCORE_YEARS_ASC}}
_SCORES_INDEX = {y: {} for y in SCORE_YEARS_ASC}  # year -> {global_idx: item}

for year in SCORE_YEARS_ASC:
    for i, item in enumerate(KB_SCORES.get(year, [])):
        _SCORES_INDEX[year][i] = item
        kelei = item.get('科类', '')
        if kelei in _SCORES_BY_KELEI:
            _SCORES_BY_KELEI[kelei][year].append(i)
        else:
            _SCORES_BY_KELEI['物理'][year].append(i)

# ─── 倒排索引：关键词 → 记录ID集合 ───
def _tokenize(text: str):
    """将文本拆分为有意义的索引词（≥2字）"""
    import re
    tokens = set()
    parts = re.split(r'[，,、\s\-/（）()（]+', text)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) >= 2:
            for i in range(len(part) - 1):
                tokens.add(part[i:i+2])
            tokens.add(part)
    return tokens

_MAJOR_INDEX = {}   # token -> set of (year, global_idx)
_SCHOOL_INDEX = {}  # token -> set of (year, global_idx)
_RECORD_BIGRAMS = {y: {} for y in SCORE_YEARS_ASC}
_RECORD_TRIGRAMS = {y: {} for y in SCORE_YEARS_ASC}

print("🔧 正在构建检索索引...")
_indexed = 0
for year in SCORE_YEARS_ASC:
    for i, item in enumerate(KB_SCORES.get(year, [])):
        school = item.get('院校名称', '')
        major = item.get('专业名称', '')
        # 预计算 bi/trigram
        _RECORD_BIGRAMS[year][i] = _bigrams(school) | _bigrams(major)
        _RECORD_TRIGRAMS[year][i] = _trigrams(school) | _trigrams(major)
        # 建立倒排索引
        for token in _tokenize(school):
            _SCHOOL_INDEX.setdefault(token, set()).add((year, i))
        for token in _tokenize(major):
            _MAJOR_INDEX.setdefault(token, set()).add((year, i))
        _indexed += 1
        if _indexed % 10000 == 0:
            print(f"  ... 已索引 {_indexed} 条")
_str = '  '.join(f'{y}:物{len(_SCORES_BY_KELEI["物理"][y])}/历{len(_SCORES_BY_KELEI["历史"][y])}' for y in SCORE_YEARS_ASC)
print(f"✅ 倒排索引完成: 专业词{len(_MAJOR_INDEX)}个, 学校词{len(_SCHOOL_INDEX)}个, 分区 {_str}")

# ─── LRU 查询缓存 ───
from collections import OrderedDict
_QUERY_CACHE = OrderedDict()
_QUERY_CACHE_MAX = 256

def _cache_key(query: str, score_lo, kelei):
    return (query.strip(), score_lo, kelei or '')

def _cache_get(query: str, score_lo, kelei):
    key = _cache_key(query, score_lo, kelei)
    if key in _QUERY_CACHE:
        _QUERY_CACHE.move_to_end(key)
        return _QUERY_CACHE[key]
    return None

def _cache_set(query: str, score_lo, kelei, result, meta):
    key = _cache_key(query, score_lo, kelei)
    if key in _QUERY_CACHE:
        _QUERY_CACHE.move_to_end(key)
    else:
        _QUERY_CACHE[key] = (result, meta)
        while len(_QUERY_CACHE) > _QUERY_CACHE_MAX:
            _QUERY_CACHE.popitem(last=False)

# ─── 专业别名映射 ───
SYNONYM_MAP = {
    '编程': '计算机 软件 信息 网络工程 数据科学 人工智能 智能科学 信息安全 物联网 数字媒体',
    '码农': '计算机 软件 信息', '程序员': '计算机 软件 信息', '写代码': '计算机 软件 信息',
    'IT': '计算机 软件 信息 网络', '互联网': '计算机 软件 信息',
    '医生': '临床医学 口腔医学 麻醉学 儿科学 医学影像 中医学 中西医 基础医学 护理学',
    '看病': '临床医学 口腔医学', '临床': '临床医学', '护士': '护理学',
    '药': '药学 中药学 药物制剂',
    '金融': '金融学 金融工程 经济学 保险学 会计学 财务管理 国际经济 投资学',
    '银行': '金融学 金融工程 经济学', '投资': '金融学 经济学 投资学',
    '赚钱': '金融学 经济学 会计学 财务管理', '理财': '金融学 经济学 会计学',
    '当老师': '师范 教育学 汉语言文学 数学与应用数学 英语 物理学 化学 生物科学 历史学',
    '教师': '师范 教育学', '考编': '师范 教育学 汉语言文学',
    '律师': '法学 知识产权', '打官司': '法学',
    '公务员': '法学 汉语言文学 行政管理 会计学 计算机 经济学',
    '体制内': '法学 汉语言文学 行政管理 会计学',
    '芯片': '电子信息 集成电路 微电子 电子科学 通信 光电信息',
    '5G': '电子信息 通信', '半导体': '电子信息 集成电路 微电子',
    '盖房子': '土木 建筑学 城乡规划', '建筑': '建筑学 土木 城乡规划',
    '画画': '美术学 设计 数字媒体 动画',
    '播音': '播音与主持 广播电视', '新闻': '新闻学 广播电视 传播学',
}

def _expand_query(query: str):
    parts = [query]
    for key, aliases in SYNONYM_MAP.items():
        if key in query:
            parts.append(aliases)
    return ' '.join(parts)

def _score_item_v2(item, query, expanded_query, pre_bigrams=None, pre_trigrams=None):
    """多因子综合评分：子串命中(0-30) + 字符重叠(0-5) + bigram(0-5) + trigram(0-8) + 学校档次(0-6) + 学科评估(0-5)
    最低阈值 = 5，低于此分直接丢弃。
    支持预计算的 bi/trigram 集合加速（避免每次查询重复计算）。"""
    school = item.get('院校名称', '')
    major = item.get('专业名称', '')
    q_chars = set(query)

    # 1. 子串命中 — 最关键维度（0-30），大幅提权
    sub_score = 0
    q_words = expanded_query.replace(',', ' ').replace('，', ' ').split()
    for word in q_words:
        w = word.strip()
        if len(w) < 2:
            continue
        if w in school:
            sub_score += 3
        if w in major:
            sub_score += 5  # 专业名命中权重更高
    sub_score = min(sub_score, 30)

    # 1.5 精确专业名匹配加权 — 查询关键词完整命中专业名 +5
    exact_bonus = 0
    for word in q_words:
        w = word.strip()
        if len(w) >= 2 and w in major:
            exact_bonus = 5
            break

    # 2. 字符集重叠（0-5），降低以抑制噪音
    char_score = 0
    if q_chars:
        char_score = (len(q_chars & set(school)) / len(q_chars)) * 3 + (len(q_chars & set(major)) / len(q_chars)) * 2
    char_score = min(char_score, 5)

    # 3. Bigram 模糊匹配（0-5），优先使用预计算
    q_bigrams = _bigrams(expanded_query)
    if pre_bigrams is not None:
        bg_score = len(q_bigrams & pre_bigrams) * 0.3
    else:
        bg_score = len(q_bigrams & _bigrams(school)) * 0.2 + len(q_bigrams & _bigrams(major)) * 0.4
    bg_score = min(bg_score, 5)

    # 3.5 Trigram 模糊匹配（0-8），优先使用预计算
    q_trigrams = _trigrams(expanded_query)
    if pre_trigrams is not None:
        tg_score = len(q_trigrams & pre_trigrams) * 0.4
    else:
        tg_score = len(q_trigrams & _trigrams(school)) * 0.3 + len(q_trigrams & _trigrams(major)) * 0.5
    tg_score = min(tg_score, 8)

    # 4. 学校档次（0-6），大幅降低以避免档次淹没相关性
    tier = _get_tier_score(school)
    # 原始 tier_score: 985=15, 211=8, 双一流=5, 其他=0
    # 映射到 0-6 区间: 985→6, 211→3, 双一流→2, 其他→0
    tier = 6 if tier >= 15 else (3 if tier >= 8 else (2 if tier >= 5 else 0))

    total = sub_score + exact_bonus + char_score + bg_score + tg_score + tier
    if total == 0:
        return 0

    # 5. 学科评估加分（0-5）— 只在有相关性时
    eval_bonus = 0
    grade = _match_subject_grade(school, major)
    if grade:
        if 'A+' in grade:
            eval_bonus = 5
        elif 'A' in grade and 'A-' not in grade:
            eval_bonus = 4
        elif 'A-' in grade:
            eval_bonus = 3
        elif 'B+' in grade:
            eval_bonus = 2

    return total + eval_bonus

MIN_RELEVANCE_THRESHOLD = 5  # 最低相关性阈值，低于此分丢弃

def search_kb(query: str, top_n: int = 21):
    score_lo, score_hi = _extract_score(query)
    kelei = _detect_kelei(query)
    province, province_available = _extract_province(query)

    # ─── LRU 缓存命中直接返回 ───
    cached = _cache_get(query, score_lo, kelei)
    if cached is not None:
        return cached

    expanded = _expand_query(query)

    # 标签过滤
    tag_filter = None
    for tag in ['985', '211', '双一流']:
        if tag in query:
            tag_filter = tag
            break

    SEARCH_MARGIN = 30
    all_matches = []

    # ─── 使用倒排索引快速定位候选记录 ───
    # 从查询中提取索引词，查找倒排索引获取候选记录 ID 集合
    q_tokens = _tokenize(expanded)
    candidate_ids = None  # None = 全量扫描（fallback）

    if q_tokens:
        # 收集所有匹配的 (year, idx) 对
        matched = set()
        for token in q_tokens:
            if token in _MAJOR_INDEX:
                matched |= _MAJOR_INDEX[token]
            if token in _SCHOOL_INDEX:
                matched |= _SCHOOL_INDEX[token]
        if matched:
            candidate_ids = matched

    # 预计算查询 bi/trigram（所有候选记录共用）
    q_bigrams = _bigrams(expanded)
    q_trigrams = _trigrams(expanded)

    for year in SCORE_YEARS_DESC:
        # 分数范围换算
        if score_lo is not None and kelei:
            yr_lo, yr_hi = _get_score_range_for_year(score_lo, kelei, year)
            yr_lo = (yr_lo or score_lo) - SEARCH_MARGIN
            yr_hi = (yr_hi or score_lo) + SEARCH_MARGIN
        elif score_lo is not None:
            yr_lo, yr_hi = score_lo - SEARCH_MARGIN, score_lo + SEARCH_MARGIN
        else:
            yr_lo, yr_hi = None, None

        # ─── 优先使用预分区 + 倒排索引候选 ───
        if kelei and kelei in _SCORES_BY_KELEI:
            year_indices = _SCORES_BY_KELEI[kelei][year]
        elif kelei:
            year_indices = range(len(KB_SCORES.get(year, [])))
        else:
            year_indices = range(len(KB_SCORES.get(year, [])))

        for i in year_indices:
            # 倒排索引过滤：如果 candidate_ids 非空且当前记录不在其中，跳过
            if candidate_ids is not None and (year, i) not in candidate_ids:
                continue

            # 统一从预建索引取记录
            item = _SCORES_INDEX[year].get(i)
            if item is None:
                continue

            if kelei and item.get('科类', '') != kelei:
                continue

            try:
                item_score = float(item.get('最低分', 0))
            except (ValueError, TypeError):
                item_score = 0

            if yr_lo is not None and (item_score < yr_lo or item_score > yr_hi):
                continue

            if tag_filter:
                tier_info = _get_tier_info(item.get('院校名称', ''))
                if tag_filter == '985' and not tier_info['is_985']:
                    continue
                if tag_filter == '211' and not tier_info['is_211']:
                    continue
                if tag_filter == '双一流' and not tier_info['is_df']:
                    continue

            # 使用预计算的 bi/trigram 加速评分
            pre_bg = _RECORD_BIGRAMS.get(year, {}).get(i)
            pre_tg = _RECORD_TRIGRAMS.get(year, {}).get(i)
            sc = _score_item_v2(item, query, expanded, pre_bg, pre_tg)
            if sc < MIN_RELEVANCE_THRESHOLD:
                continue

            all_matches.append((sc, year, item))

    # ─── 按 (院校, 专业, 科类) 合并两年数据 ───
    merged = {}
    for sc, year, item in all_matches:
        key = (item.get('院校名称', ''), item.get('专业名称', ''), item.get('科类', ''))
        if key not in merged:
            merged[key] = {}
        if year not in merged[key] or sc > merged[key][year]['score']:
            merged[key][year] = {'item': item, 'score': sc}

    # 综合分 = 2025*1.5 + 2024*1.0 + 学校档次*0.3
    scored = []
    for key, entry in merged.items():
        s25 = entry.get(2025, {}).get('score', 0)
        s24 = entry.get(2024, {}).get('score', 0)
        tier = _get_tier_score(key[0])
        total = s25 * 1.5 + s24 + tier * 0.3
        scored.append((total, key, entry))

    scored.sort(key=lambda x: x[0], reverse=True)

    # ─── 冲稳保分层 ───
    if score_lo is not None and scored:
        冲, 稳, 保 = [], [], []
        for item_tuple in scored:
            _, key, entry = item_tuple
            item_2025 = entry.get(2025, {}).get('item')
            item_2024 = entry.get(2024, {}).get('item')
            ref = item_2025 or item_2024
            if not ref:
                continue
            try:
                ref_score = float(ref.get('最低分', 0))
            except (ValueError, TypeError):
                continue

            if ref_score > score_lo + 5:
                冲.append(item_tuple)
            elif ref_score >= score_lo - 10:
                稳.append(item_tuple)
            else:
                保.append(item_tuple)

        results = []
        for stratum, items in [('冲', 冲), ('稳', 稳), ('保', 保)]:
            for total, key, entry in items[:7]:
                results.append((total, key, entry, stratum))
    else:
        results = [(total, key, entry, '') for total, key, entry in scored[:top_n]]

    # ─── 构建输出 ───
    output = []
    for _, key, entry, stratum in results:
        school, major, cat = key
        result = {'类型': '录取分数', '院校名称': school, '专业名称': major, '科类': cat, '档次': stratum}
        for year in SCORE_YEARS_ASC:
            if year in entry:
                score_val = entry[year]['item'].get('最低分', '')
                result[f'最低分_{year}'] = score_val
                try:
                    rank_val = score_to_rank(int(float(score_val)), year, cat)
                    if rank_val:
                        result[f'位次_{year}'] = rank_val
                except (ValueError, TypeError):
                    pass
        output.append(result)

    # ─── 学校信息 ───
    school_results = []
    q_bigrams = _bigrams(expanded)
    for item in KB_SCHOOLS:
        search_text = ' '.join([item.get('name', ''), item.get('type', ''), item.get('city', ''), item.get('tags', '')])
        overlap = len(q_bigrams & _bigrams(search_text))
        if overlap <= 0:
            continue
        boost = 2.0 if (tag_filter and tag_filter in item.get('tags', '')) else 1.0
        school_results.append((overlap * boost + _get_tier_score(item.get('name', '')) * 0.3, item))
    school_results.sort(key=lambda x: x[0], reverse=True)
    for _, item in school_results[:5]:
        output.append({'类型': '学校信息', **item})

    result = output
    meta = {
        'province': province,
        'province_available': province_available,
        'kelei': kelei,
        'score': score_lo,
    }
    # 存入 LRU 缓存
    _cache_set(query, score_lo, kelei, result, meta)
    return result, meta

def _rank_trend_desc(rk24, rk25):
    """描述位次变化趋势，返回说明文字"""
    try:
        r24, r25 = int(rk24), int(rk25)
        diff = r24 - r25  # 正值=位次进步(排名数字变小), 负值=位次退步
        if abs(diff) <= 300:
            return f'位次稳(两年差{abs(diff)}名)'
        elif diff > 0:
            return f'位次进步{diff}名(变热门)'
        else:
            return f'位次退步{abs(diff)}名(变冷)'
    except (ValueError, TypeError):
        return ''

def user_score_context(query: str):
    """从查询中提取分数/科类，换算为位次，返回上下文文字"""
    score_lo, _ = _extract_score(query)
    kelei = _detect_kelei(query)
    if score_lo is None:
        return ''
    if not YIFENYIDANG:
        return f'用户提到{score_lo}分，但一分一段表未加载，无法换算位次。'

    # 用最近年份换算
    base_year = max(YIFENYIDANG.keys())
    for k in [kelei, '物理', '历史']:
        if not k:
            continue
        rank = score_to_rank(score_lo, base_year, k)
        if rank:
            return f'用户分数{score_lo}({k}) ≈ {base_year}年全省位次约{rank}名。注意：2024=前年, 2025=去年, 2026=今年（当前高考季），用前年去年位次走势推断今年。'
    return f'用户提到{score_lo}分（科类不明，无法精确换算位次）。'

def format_kb_results(results, query='', meta=None):
    if not results:
        return ''

    score_items = [r for r in results if r.get('类型') == '录取分数']
    school_items = [r for r in results if r.get('类型') == '学校信息']

    parts = []

    # ─── 省份不匹配警告 ───
    province_warning = ''
    if meta:
        province = meta.get('province')
        province_available = meta.get('province_available', True)
        if province and not province_available:
            province_warning = (
                f'⚠️ 用户问的是【{province}】省的数据，但当前数据库仅有【河北】省的录取数据。'
                f'以下所有分数线都是河北省的，对{province}考生仅供参考位次趋势，绝对不能用河北分数直接套{province}志愿！'
                f'你必须明确告诉用户：这是河北数据，{province}的分数线请自行查阅本省教育考试院。'
            )
            parts.append(province_warning)
            parts.append('')

    # 用户分数→位次上下文
    user_ctx = user_score_context(query) if query else ''
    if user_ctx:
        parts.append(f'【用户位次参考】{user_ctx}')
        parts.append('')

    if score_items:
        parts.append('【河北省录取数据 前年(2024)→去年(2025)对比 · 推断今年(2026)趋势】')
        parts.append('铁律：前年=2024, 去年=2025, 今年=2026。提到分数必须带年份，推测今年必须说"预估"。')
        parts.append('')

        # 按档次分组输出
        strata_order = [('冲', '🔴 冲一冲（高于你分数，需要够一够）'),
                        ('稳', '🟡 稳一稳（分数接近，大概率能上）'),
                        ('保', '🟢 保一保（低于你分数，稳稳能上）'),
                        ('', '📋 匹配结果')]
        idx = 0
        for stratum_tag, stratum_label in strata_order:
            group = [it for it in score_items if it.get('档次', '') == stratum_tag]
            if not group:
                continue
            parts.append(stratum_label)
            for item in group:
                idx += 1
                school = item.get('院校名称', '?')
                major = item.get('专业名称', '?')
                cat = item.get('科类', '')
                s24 = item.get('最低分_2024', '')
                s25 = item.get('最低分_2025', '')
                rk24 = item.get('位次_2024', '')
                rk25 = item.get('位次_2025', '')

                # 学校档次标签
                tier_info = _get_tier_info(school)
                tier_tags = tier_info.get('tags', '')
                tier_badges = []
                if tier_info.get('is_985'):
                    tier_badges.append('985')
                if tier_info.get('is_211'):
                    tier_badges.append('211')
                elif tier_info.get('is_df'):
                    tier_badges.append('双一流')
                badgestr = (' [' + '·'.join(tier_badges) + ']') if tier_badges else ''

                line = f'{idx}. {school}{badgestr} · {major}（{cat}）'
                if s24 and s25:
                    try:
                        diff_score = int(float(s25)) - int(float(s24))
                        arrow = '↑' + str(diff_score) if diff_score > 0 else ('↓' + str(abs(diff_score)) if diff_score < 0 else '→')
                    except (ValueError, TypeError):
                        arrow = ''
                    trend = _rank_trend_desc(rk24, rk25)
                    line += f' 前年2024:{s24}分(位{rk24}) → 去年2025:{s25}分(位{rk25}) {arrow}分'
                    if trend:
                        line += f' | {trend}'
                elif s25:
                    line += f' 去年2025:{s25}分(位{rk25})（仅去年有数据，注意无前年对比）'
                else:
                    line += f' 前年2024:{s24}分(位{rk24})（仅前年有数据，注意无去年对比）'

            # 附学科评估等级
            grade = _match_subject_grade(school, major)
            if grade:
                line += f' [学科评估: {grade}]'
            parts.append(line)

    if school_items:
        parts.append('')
        parts.append('【相关院校背景】')
        for i, item in enumerate(school_items, 1):
            name = item.get('name', '')
            tags = item.get('tags', '')
            rank = item.get('rank_软科', 999)
            subjects = item.get('双一流学科', [])
            # 查学科评估顶尖学科
            evals = _lookup_eval(name)
            top_subjects = [f'{s} {g}' for s, g in sorted(evals.items(), key=lambda x: (
                0 if x[1].startswith('A+') else 1 if x[1].startswith('A') else 2 if x[1].startswith('A-') else 3
            ))[:3] if g.startswith('A')]

            line_parts = [name]
            if tags:
                line_parts.append(f'[{tags}]')
            line_parts.append(item.get('type', ''))
            line_parts.append(item.get('city', ''))
            if rank < 999:
                line_parts.append(f'软科#{rank}')
            line = ' | '.join(line_parts)

            if subjects:
                line += f'\n  双一流学科: {", ".join(subjects[:5])}'
            if top_subjects:
                line += f'\n  顶尖学科: {", ".join(top_subjects)}'
            parts.append(line)

    return '\n'.join(parts)