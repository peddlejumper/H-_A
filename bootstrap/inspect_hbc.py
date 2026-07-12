import json
data = json.load(open('hsharp_bundle.hbc'))
modules = data.get('modules', {})

found = 0
def walk(obj, path='', depth=0):
    global found
    if depth > 8: return
    if isinstance(obj, dict):
        if 'instructions' in obj and isinstance(obj['instructions'], list):
            instrs = obj['instructions']
            for i, ins in enumerate(instrs):
                if ins and isinstance(ins, list) and len(ins) > 0 and ins[0] == 'FOR_ITER':
                    found += 1
                    if found <= 3:
                        print('--- FOR_ITER at', path, 'idx', i)
                        for j in range(max(0, i-3), min(len(instrs), i+3)):
                            print(f'    [{j}] {instrs[j]}')
                        if i >= 2 and instrs[i-1] and instrs[i-1][0] == 'LOAD_CONST':
                            idx = instrs[i-1][1]
                            if isinstance(idx, int) and idx < len(obj.get('consts', [])):
                                print(f'    const at idx {idx}: {obj["consts"][idx]!r}')
        for k, v in obj.items():
            walk(v, path + '/' + str(k), depth+1)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            walk(item, path + f'[{i}]', depth+1)

walk(modules)
print('Total FOR_ITER found:', found)
