import json
import sys

with open('bootstrap/hsharp_bundle.hbc', 'r') as f:
    data = json.load(f)
hwdui = data['modules']['hwdui']
consts = hwdui['consts']

# Extract all class fields
classes = {}
for c in consts:
    if isinstance(c, dict) and 'name' in c and 'methods' in c:
        name = c['name']
        fields = c.get('fields', {})
        base = c.get('base', None)
        classes[name] = {
            'fields': fields,
            'base': base,
            'methods': {}
        }
        for mname, mdata in c['methods'].items():
            if isinstance(mdata, dict):
                classes[name]['methods'][mname] = {
                    'args': mdata.get('args', []),
                    'bytecode': mdata.get('bytecode', [])
                }

# Print class structure
for name, info in classes.items():
    print(f"Class: {name}")
    if info['base']:
        print(f"  extends: {info['base']}")
    print(f"  Fields:")
    for fname, fval in info['fields'].items():
        if isinstance(fval, str):
            print(f"    let {fname} = \"{fval}\";")
        elif fval is None:
            print(f"    let {fname} = nullptr;")
        elif isinstance(fval, bool):
            print(f"    let {fname} = {'true' if fval else 'false'};")
        elif isinstance(fval, list):
            print(f"    let {fname} = [];")
        elif isinstance(fval, dict):
            print(f"    let {fname} = {{}};")
        else:
            print(f"    let {fname} = {fval};")
    print(f"  Methods:")
    for mname, minfo in info['methods'].items():
        print(f"    fn {mname}({minfo['args']})")
    print()