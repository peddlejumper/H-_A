#!/usr/bin/env python3
"""多语言教学端到端验证脚本 —— API 直接返回对象(不包 data)"""
import json
import urllib.request
import urllib.error

BASE = "http://localhost:5050/api/v1"

def post(path, body, token=None):
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.getcode(), json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"raw": body}

def get(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.getcode(), json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"raw": body}

# 1. 登录 teacher1(若不存在则注册)
print("=== 1. 登录/注册 teacher1 ===")
code, login = post("/users/login", {"username": "teacher1", "password": "teacher12345"})
if code != 200:
    print("teacher1 不存在,先注册...")
    email = "teacher" + "@" + "example.com"
    code, reg = post("/users/register", {
        "username": "teacher1", "email": email,
        "password": "teacher12345", "displayName": "Teacher One"
    })
    if code != 200:
        print(f"注册失败: {code} {reg}")
        exit(1)
    token = reg["accessToken"]
    user = reg["user"]
    print(f"注册成功: {user['username']} (角色: {user['role']})")
    # 提示:需手动提权为 Admin
    print("  注意:新注册默认 Student,需手动提权为 Admin 才能创建题目")
else:
    token = login["accessToken"]
    user = login["user"]
    print(f"登录成功: {user['username']} (角色: {user['role']})")

# 2. 查询题目列表,确认 P001 存在
print("\n=== 2. 查询题目列表 ===")
code, list_resp = get("/problems?page=1&pageSize=10")
print(f"HTTP {code} | 总数: {list_resp['total']}")
pid = None
for item in list_resp["items"]:
    print(f"  {item['code']} - {item['title']} | 支持语言: {item['supportedLanguages']} | 用例数: {item['testCaseCount']}")
    if item["code"] == "P001":
        pid = item["id"]

if not pid:
    print("P001 不存在,先创建")
    code, create = post("/problems", {
        "code": "P001", "title": "A+B Problem",
        "description": "输入两个整数 a 和 b,输出它们的和。",
        "difficulty": 0, "timeLimitMs": 1000, "memoryLimitKb": 65536,
        "template": "", "tags": ["入门", "基础"],
        "supportedLanguages": [0, 1, 5]
    }, token)
    if code != 201:
        print(f"创建失败: {code} {create}")
        exit(1)
    pid = create["id"]
    print(f"创建成功,题目 ID: {pid}")
else:
    print(f"P001 已存在,ID: {pid}")

# 3. 添加测试用例(若用例数为 0)
code, detail = get(f"/problems/{pid}")
if detail.get("testCaseCount", 0) == 0:
    print("\n=== 3. 添加测试用例 ===")
    for inp, exp, sample in [("3 5", "8", True), ("10 20", "30", False), ("-1 1", "0", False)]:
        c, r = post(f"/problems/{pid}/testcases",
                    {"input": inp, "expectedOutput": exp, "isSample": sample}, token)
        print(f"  用例 [{inp} -> {exp}]: HTTP {c}")
else:
    print(f"\n=== 3. 跳过(P001 已有 {detail['testCaseCount']} 个用例) ===")

# 4. 提交 Python 正确解法
print("\n=== 4. 提交 Python 正确解法 ===")
py_code = "a, b = map(int, input().split())\nprint(a + b)"
code, submit = post("/submissions", {"problemId": pid, "code": py_code, "language": "Python"}, token)
if code == 201:
    d = submit
    print(f"  HTTP {code} | 状态: {d['status']} | 通过: {d['passedCases']}/{d['totalCases']} | 分数: {d['score']} | 耗时: {d['elapsedMs']}ms")
    if d.get("errorMessage"):
        print(f"  错误信息: {d['errorMessage'][:200]}")
else:
    print(f"  提交失败: HTTP {code} {submit}")

# 5. 提交 Python 错误解法(验证 WA)
print("\n=== 5. 提交 Python 错误解法(验证 WA) ===")
py_wrong = "a, b = map(int, input().split())\nprint(a - b)"
code, submit2 = post("/submissions", {"problemId": pid, "code": py_wrong, "language": "Python"}, token)
if code == 201:
    d = submit2
    print(f"  HTTP {code} | 状态: {d['status']} | 通过: {d['passedCases']}/{d['totalCases']} | 分数: {d['score']}")
else:
    print(f"  提交失败: HTTP {code} {submit2}")

# 6. 提交不支持的语言 Java(应被拒绝)
print("\n=== 6. 提交不支持的语言 Java(应被拒绝) ===")
code, submit3 = post("/submissions", {
    "problemId": pid,
    "code": "public class main { public static void main(String[] a) {} }",
    "language": "Java"
}, token)
if code >= 400:
    msg = submit3.get("message", submit3.get("title", ""))
    print(f"  正确拒绝: HTTP {code} | {msg[:150]}")
else:
    print(f"  未被拒绝: HTTP {code} {submit3}")

# 7. 查询提交记录
print("\n=== 7. 查询当前用户提交记录 ===")
uid = user["id"]
code, subs = get(f"/submissions/user/{uid}?page=1&pageSize=10", token)
if code == 200:
    print(f"  HTTP {code} | 总数: {subs['total']}")
    for s in subs["items"]:
        print(f"    {s['status']} | {s['language']} | 通过 {s['passedCases']}/{s['totalCases']} | {s['submittedAt']}")
else:
    print(f"  查询失败: HTTP {code} {subs}")

print("\n=== 多语言教学端到端验证完成 ===")
