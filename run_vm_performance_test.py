"""
H# Bytecode VM Performance Test Runner
Directly loads hwdui/d3system from hsharp_bundle.hbc into VM environment.
Does NOT use Python tree-walking interpreter at all.
"""

import json
import time
import copy
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lexer import Lexer
from parser import Parser
from compiler import Compiler
from bytecode import VM

def load_bundle():
    with open('bootstrap/hsharp_bundle.hbc', 'r', encoding='utf-8') as f:
        return json.load(f)

def create_test_vm_with_modules():
    """Create a VM with all bundle modules loaded into its environment."""
    bundle = load_bundle()
    env = {}
    functions = {}
    
    module_order = ['d3system', 'd3system_ops', 'hwdui', 'perf_monitor', 'math_utils']
    
    for mod_name in module_order:
        if mod_name not in bundle['modules']:
            print(f"  Skipping {mod_name} (not in bundle)")
            continue
        mod_bc = bundle['modules'][mod_name]
        vm = VM(mod_bc)
        vm.env = env.copy()
        vm.functions = functions.copy()
        try:
            vm.run()
            env.update(vm.env)
            functions.update(vm.functions)
            print(f"  Loaded {mod_name}: {len(vm.env)} names in env")
        except Exception as e:
            print(f"  WARNING: {mod_name} had error: {e}")
    
    return env, functions

def compile_test_to_bytecode(source, env, functions):
    lexer = Lexer(source)
    parser = Parser(lexer)
    program = parser.parse()
    compiler = Compiler(use_hcompiler=True)
    bytecode = compiler.compile(program)
    return bytecode

def run_test(test_name, source, base_env, base_functions):
    print(f"\n--- Running: {test_name} ---")
    bytecode = compile_test_to_bytecode(source, base_env, base_functions)
    
    vm = VM(bytecode)
    vm.env.update(base_env)
    vm.functions.update(base_functions)
    
    start = time.perf_counter()
    try:
        vm.run()
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"  [OK] {elapsed_ms:.2f} ms")
        return elapsed_ms
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"  [ERROR] {e}")
        return f"ERROR: {e}"

TEST_ZZWUI_CREATE = """
let count = 50;
let i = 0;
while (i < count) {
    let btn = new Button();
    btn.init_btn("button");
    btn.set_pos(i * 5, i * 3);
    btn.set_size(80, 30);
    i = i + 1;
}
print("Created 50 Button widgets");
"""

TEST_WIDGET_TREE = """
let win = new Window();
win.init_win("Test Window");
win.width = 800;
win.height = 600;

let panel1 = new Panel();
panel1.init_panel("main_panel");
win.add_child(panel1);

let p = 0;
while (p < 10) {
    let sub = new Panel();
    sub.init_panel("sub_panel");
    sub.set_pos(p * 50, p * 30);
    sub.set_size(200, 100);
    panel1.add_child(sub);
    
    let c = 0;
    while (c < 5) {
        let lbl = new Label();
        lbl.init_label("label");
        lbl.set_pos(c * 40, 10);
        sub.add_child(lbl);
        c = c + 1;
    }
    p = p + 1;
}
print("Built widget tree: 1 Window + 11 Panels + 50 Labels = 62 widgets");

let f = 0;
let found_count = 0;
while (f < 20) {
    let found = win.find_by_id("label");
    if (found != nullptr) { found_count = found_count + 1; }
    f = f + 1;
}
print("20 find_by_id calls: found " + str(found_count) + " times");
"""

TEST_CSS = """
let sheet = hwdui_create_stylesheet("test");
let sel = new Selector();
sel.init_sel();
sel.setType("Button");
sel.setClass("primary");
sheet.addRule(sel, [
    ["background-color", "#36454F"],
    ["border-color", "#708090"],
    ["font-size", "14"],
    ["padding", "8"]
]);

let i = 0;
while (i < 30) {
    let btn = new Button();
    btn.init_btn("css_button");
    btn.addClass("primary");
    let computed = btn.getComputedStyle();
    i = i + 1;
}
print("30 CSS style computations completed");
"""

TEST_D3_POINT = """
let i = 0;
while (i < 100) {
    let p1 = D3Point(i, i * 2, i * 3);
    let p2 = D3Point(i + 10, i + 20, i + 30);
    let dist = d3_point_dist(p1, p2);
    let mid = d3_point_mid(p1, p2);
    let added = d3_point_add(p1, p2);
    i = i + 1;
}
print("100 point operations (distance + midpoint + addition)");
"""

TEST_D3_BBOX = """
let i = 0;
while (i < 100) {
    let box1 = D3BoundingBox(i, i, i, i+50, i+50, i+50);
    let box2 = D3BoundingBox(i+25, i+25, i+25, i+75, i+75, i+75);
    let intersects = d3_bbox_intersects(box1, box2);
    let volume = d3_bbox_volume(box1);
    let center = d3_bbox_center(box1);
    i = i + 1;
}
print("100 bbox operations (intersection + volume + center)");
"""

TEST_D3_VEC = """
let i = 1;
while (i <= 100) {
    let v1 = D3Vec3(i, i*2, i*3);
    let v2 = D3Vec3(i+1, i+2, i+3);
    let dot = d3_vec3_dot(v1, v2);
    let cross = d3_vec3_cross(v1, v2);
    let length = d3_vec3_length(v1);
    i = i + 1;
}
print("100 vector operations (dot + cross + length)");
"""

TEST_D3_REGION = """
let world = {};
world.regions = [];
world.name = "TestWorld";

let r = 0;
while (r < 20) {
    let rgn = {};
    rgn.name = "Region";
    rgn.coords = [r*100, 0, 0, r*100+50, 200, 200];
    push(world.regions, rgn);
    r = r + 1;
}

let q = 0;
while (q < 50) {
    let found = d3_find_region_by_point(world, q*50+25, 100, 100);
    let by_name = d3_find_region_by_name(world, "Region");
    q = q + 1;
}
print("50 region queries on 20-region world");
"""

TEST_COMBINED = """
let i = 0;
while (i < 20) {
    let point = D3Point(i*10, i*5, i*2);
    let bbox = D3BoundingBox(
        d3_point_x(point)-25, d3_point_y(point)-25, d3_point_z(point)-25,
        d3_point_x(point)+25, d3_point_y(point)+25, d3_point_z(point)+25
    );
    let vol = d3_bbox_volume(bbox);
    
    let card = new Panel();
    card.init_panel("card");
    card.set_pos(i*30, 0);
    card.set_size(250, 80);
    
    let lbl = new Label();
    lbl.init_label("Volume");
    card.add_child(lbl);
    
    i = i + 1;
}
print("20 combined operations (D3Spatial + zzwUI widgets)");
"""

def main():
    print("=" * 60)
    print("  H# Bytecode VM Performance Tests")
    print("  Direct bytecode execution (NO tree-walking interpreter)")
    print("=" * 60)
    
    print("\nLoading modules from hsharp_bundle.hbc...")
    env, functions = create_test_vm_with_modules()
    
    tests = [
        ("zzwUI Widget Creation (50 widgets)", TEST_ZZWUI_CREATE),
        ("zzwUI Widget Tree (62 widgets, 20 find_by_id)", TEST_WIDGET_TREE),
        ("zzwUI CSS Computation (30 times)", TEST_CSS),
        ("D3System Point Operations (100 times)", TEST_D3_POINT),
        ("D3System Bounding Box (100 times)", TEST_D3_BBOX),
        ("D3System Vector Math (100 times)", TEST_D3_VEC),
        ("D3System Region Query (50 queries, 20 regions)", TEST_D3_REGION),
        ("Combined zzwUI + D3System (20 ops)", TEST_COMBINED),
    ]
    
    results = {}
    for test_name, source in tests:
        elapsed = run_test(test_name, source, env, functions)
        results[test_name] = elapsed
    
    print("\n" + "=" * 60)
    print("  PERFORMANCE SUMMARY")
    print("=" * 60)
    print()
    print(f"{'Test':<50} {'Time (ms)':<12}")
    print(f"{'-'*50} {'-'*12}")
    for test_name, elapsed in results.items():
        if isinstance(elapsed, float):
            print(f"{test_name:<50} {elapsed:<12.2f}")
        else:
            print(f"{test_name:<50} {str(elapsed):<12}")
    print()
    print(f"Execution: H# Bytecode VM (bytecode.py)")
    print(f"NO Python tree-walking interpreter used")
    
    with open('benchmark_vm_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to benchmark_vm_results.json")

if __name__ == "__main__":
    main()
