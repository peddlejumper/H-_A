#!/usr/bin/env python3
"""Wrap Python compiler's flat .hbc ({instructions,consts}) into the
container format the Kotlin HbcReader expects:
  {"version":"v0.4","modules":{"main":{...}},"built_at":<epoch>}

Usage: wrap_hbc.py <in.hbc> <out.hbc> [module_name]
"""
import json, sys, time, os

def main():
    if len(sys.argv) < 3:
        sys.exit("usage: wrap_hbc.py <in.hbc> <out.hbc> [module_name]")
    inp, outp = sys.argv[1], sys.argv[2]
    mname = sys.argv[3] if len(sys.argv) > 3 else "main"
    with open(inp) as f:
        data = json.load(f)
    # Already container format?
    if isinstance(data, dict) and "modules" in data:
        wrapped = data
        if "version" not in wrapped:
            wrapped["version"] = "v0.4"
        if "built_at" not in wrapped:
            wrapped["built_at"] = int(time.time())
    else:
        wrapped = {
            "version": "v0.4",
            "modules": {mname: data},
            "built_at": int(time.time()),
        }
    with open(outp, "w") as f:
        json.dump(wrapped, f, separators=(", ", ": "))
    print(f"wrapped {inp} -> {outp} (module={mname}, "
          f"instructions={len(data.get('instructions', []))})")

if __name__ == "__main__":
    main()
