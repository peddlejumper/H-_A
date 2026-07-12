#!/usr/bin/env python3
"""Wrap raw {instructions,consts} .hbc into {version,modules,built_at} for Kotlin HVM."""
import json, sys, os, time

def wrap(raw_path, out_path):
    with open(raw_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    wrapped = {
        "version": "v0.4",
        "modules": {"main": {"instructions": raw["instructions"], "consts": raw["consts"]}},
        "built_at": int(time.time()),
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(wrapped, f)
    return out_path

if __name__ == "__main__":
    wrap(sys.argv[1], sys.argv[2])
    print(f"Wrapped {sys.argv[1]} -> {sys.argv[2]}")
