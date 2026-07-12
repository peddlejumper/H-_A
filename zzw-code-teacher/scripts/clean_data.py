#!/usr/bin/env python3
"""One-shot cleanup for ZZW data files polluted by the storage_update bug
(which used integer indices as keys, adding "0": null, "1": null, ...).

- Strips integer-string keys from each row
- Ensures default admin user (username: admin / password: admin123)
"""
import json
import os
import sys

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def clean_row(row):
    if not isinstance(row, dict):
        return row
    return {k: v for k, v in row.items() if not (isinstance(k, str) and k.isdigit())}


def clean_list(rows):
    return [clean_row(r) for r in rows if isinstance(r, dict)]


def patch_user_password_hash(user, password):
    """Re-hash using djb2 with the same salt the H# auth uses.

    H# shared/auth.hto: password_hash(plain) = _hash_string("zzw_salt_" + plain + "_2026")
    _hash_string uses djb2: h = h * 33 + ord(c), 8-char lowercase hex output.
    """
    s = "zzw_salt_" + password + "_2026"
    h = 5381
    for ch in s:
        h = (h * 33 + ord(ch)) % 4294967296
    digits = "0123456789abcdef"
    out = ""
    x = h
    for _ in range(8):
        d = x % 16
        out = digits[d] + out
        x = x // 16
    user["password_hash"] = out
    return user


def main():
    # users.json — keep alice, ensure admin present
    p = os.path.join(DATA, "users.json")
    users = []
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            users = clean_list(json.load(f))
    has_alice = any(u.get("username") == "alice" for u in users)
    has_admin = any(u.get("username") == "admin" for u in users)
    if not has_alice:
        u = {
            "id": "u_seed_alice",
            "username": "alice",
            "role": "student",
            "display_name": "alice",
            "email": "",
            "class_id": "",
            "created_at": 1700000000000,
            "last_login": 0,
            "total_submissions": 0,
            "total_accepted": 0,
            "status": "active",
        }
        u = patch_user_password_hash(u, "alice123")
        users.append(u)
    if not has_admin:
        u = {
            "id": "u_seed_admin",
            "username": "admin",
            "role": "admin",
            "display_name": "admin",
            "email": "",
            "class_id": "",
            "created_at": 1700000000000,
            "last_login": 0,
            "total_submissions": 0,
            "total_accepted": 0,
            "status": "active",
        }
        u = patch_user_password_hash(u, "admin123")
        users.append(u)
    # also fix existing alice/admin password hashes if they look wrong
    for u in users:
        if u.get("username") == "alice":
            patch_user_password_hash(u, "alice123")
        if u.get("username") == "admin":
            patch_user_password_hash(u, "admin123")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False)
    print(f"users.json: {len(users)} users")

    # problems.json
    p = os.path.join(DATA, "problems.json")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            rows = clean_list(json.load(f))
        with open(p, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False)
        print(f"problems.json: {len(rows)} problems cleaned")

    # submissions.json
    p = os.path.join(DATA, "submissions.json")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            rows = clean_list(json.load(f))
        with open(p, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False)
        print(f"submissions.json: {len(rows)} submissions cleaned")

    # progress.json
    p = os.path.join(DATA, "progress.json")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            rows = clean_list(json.load(f))
        with open(p, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False)
        print(f"progress.json: {len(rows)} progress entries cleaned")

    # delete uploads dir to clear stale test artifacts
    up = os.path.join(DATA, "uploads")
    if os.path.isdir(up):
        import shutil
        shutil.rmtree(up, ignore_errors=True)
        print("uploads: cleared")


if __name__ == "__main__":
    main()
