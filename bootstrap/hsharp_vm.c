/* H# Bytecode VM - C Implementation (Python-free)
 *
 * This is the C-based bytecode virtual machine for H#.
 * It loads bytecode (JSON format) and executes it natively.
 * No Python dependency required.
 *
 * Compile: gcc -O2 -o hsharp-vm hsharp_vm.c
 * Run:     ./hsharp-vm bootstrap_bytecode.json
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <ctype.h>

#include "dzzw.h"

/* ===== Value Types ===== */
typedef enum {
    VAL_NULL,
    VAL_INT,
    VAL_FLOAT,
    VAL_BOOL,
    VAL_STRING,
    VAL_LIST,
    VAL_DICT,
    VAL_FUNC,
    VAL_CLASS,
    VAL_INSTANCE,
    VAL_NATIVE
} ValType;

typedef struct Value Value;
typedef struct List List;
typedef struct Dict Dict;
typedef struct DictEntry DictEntry;
typedef struct Func Func;
typedef struct Class Class;
typedef struct Instance Instance;

struct List {
    Value **items;
    size_t len;
    size_t cap;
};

struct DictEntry {
    char *key;
    Value *val;
};

struct Dict {
    DictEntry *entries;
    size_t len;
    size_t cap;
};

struct Func {
    char **arg_names;
    size_t nargs;
    Value **bytecode;  /* [op, arg] pairs as Value list */
    size_t n_instrs;
    Value **consts;
    size_t n_consts;
    char *name;
};

struct Class {
    char *name;
    char *base_name;
    Func **methods;  /* list of [name, func] */
    size_t n_methods;
    char **method_names;
    DictEntry *fields;  /* name -> default value */
    size_t n_fields;
};

struct Instance {
    Class *cls;
    Dict *attrs;
};

struct Value {
    ValType type;
    union {
        int64_t int_val;
        double float_val;
        int bool_val;
        char *str_val;
        List *list_val;
        Dict *dict_val;
        Func *func_val;
        Class *class_val;
        Instance *instance_val;
    } data;
};

/* ===== VM State ===== */
#define MAX_STACK 4096
#define MAX_FRAMES 256
#define MAX_ITER_STACK 64

typedef struct {
    Value *stack[MAX_STACK];
    int sp;

    struct {
        Func *func;
        Value **instrs;
        size_t n_instrs;
        Value **consts;
        size_t n_consts;
        int pc;
        Dict *env;
        int saved_sp;
    } frames[MAX_FRAMES];
    int frame_sp;

    /* iteration state */
    Value *iter_stack[MAX_ITER_STACK];
    int iter_sp;

    /* global env */
    Dict *global_env;

    /* captured return value (for worker threads) */
    Value *ret_val;
} VM;

/* DZZW builtin dispatcher — forward declaration */
static int dzzw_run_builtin(VM *vm, const char *fname, Value **args, int nargs, Value **result);

/* forward declarations */
static void free_value(Value *v);
static void list_append(List *l, Value *v);
static void dict_remove(Dict *d, const char *key);
static int values_equal(Value *a, Value *b);

/* ===== JSON Parser (minimal) ===== */
typedef struct {
    const char *s;
    int pos;
} JParser;

static void j_skip_ws(JParser *j) {
    while (j->s[j->pos] == ' ' || j->s[j->pos] == '\n' ||
           j->s[j->pos] == '\r' || j->s[j->pos] == '\t')
        j->pos++;
}

static Value *j_parse_value(JParser *j, int pc);
static Value *j_parse_list(JParser *j, int pc);
static Value *j_parse_dict(JParser *j, int pc);
static char *j_parse_string(JParser *j);

static char *j_parse_string(JParser *j) {
    if (j->s[j->pos] != '"') return NULL;
    j->pos++;
    char buf[65536];
    int bi = 0;
    while (j->s[j->pos] && j->s[j->pos] != '"') {
        if (j->s[j->pos] == '\\') {
            j->pos++;
            switch (j->s[j->pos]) {
                case 'n': buf[bi++] = '\n'; break;
                case '"': buf[bi++] = '"'; break;
                case '\\': buf[bi++] = '\\'; break;
                case 't': buf[bi++] = '\t'; break;
                default: buf[bi++] = j->s[j->pos]; break;
            }
        } else {
            buf[bi++] = j->s[j->pos];
        }
        j->pos++;
    }
    buf[bi] = '\0';
    if (j->s[j->pos] == '"') j->pos++;
    return strdup(buf);
}

static Value *j_parse_value(JParser *j, int pc) {
    j_skip_ws(j);
    char c = j->s[j->pos];

    if (c == '"') {
        Value *v = malloc(sizeof(Value));
        v->type = VAL_STRING;
        v->data.str_val = j_parse_string(j);
        return v;
    }

    if (c == 'n' && strncmp(j->s + j->pos, "null", 4) == 0) {
        j->pos += 4;
        Value *v = malloc(sizeof(Value));
        v->type = VAL_NULL;
        return v;
    }

    if (c == 't' && strncmp(j->s + j->pos, "true", 4) == 0) {
        j->pos += 4;
        Value *v = malloc(sizeof(Value));
        v->type = VAL_BOOL;
        v->data.bool_val = 1;
        return v;
    }

    if (c == 'f' && strncmp(j->s + j->pos, "false", 5) == 0) {
        j->pos += 5;
        Value *v = malloc(sizeof(Value));
        v->type = VAL_BOOL;
        v->data.bool_val = 0;
        return v;
    }

    if (c == '-' || (c >= '0' && c <= '9')) {
        int is_float = 0;
        char buf[256]; int bi = 0;
        while (j->s[j->pos] && (isdigit(j->s[j->pos]) ||
               j->s[j->pos] == '-' || j->s[j->pos] == '.' ||
               j->s[j->pos] == 'e' || j->s[j->pos] == 'E')) {
            if (j->s[j->pos] == '.' || j->s[j->pos] == 'e' || j->s[j->pos] == 'E')
                is_float = 1;
            buf[bi++] = j->s[j->pos++];
        }
        buf[bi] = '\0';
        Value *v = malloc(sizeof(Value));
        if (pc) {
            v->type = VAL_INT;
            v->data.int_val = (int64_t)atof(buf);
        } else if (is_float) {
            v->type = VAL_FLOAT;
            v->data.float_val = atof(buf);
        } else {
            v->type = VAL_INT;
            v->data.int_val = (int64_t)atof(buf);
        }
        return v;
    }

    if (c == '[') {
        return j_parse_list(j, pc);
    }

    if (c == '{') {
        return j_parse_dict(j, pc);
    }

    return NULL;
}

static Value *j_parse_list(JParser *j, int pc) {
    j->pos++; /* skip [ */
    Value *v = malloc(sizeof(Value));
    v->type = VAL_LIST;
    v->data.list_val = malloc(sizeof(List));
    v->data.list_val->cap = 16;
    v->data.list_val->len = 0;
    v->data.list_val->items = malloc(sizeof(Value*) * 16);

    j_skip_ws(j);
    if (j->s[j->pos] != ']') {
        while (1) {
            Value *elem = j_parse_value(j, pc);
            if (!elem) break;
            if (v->data.list_val->len >= v->data.list_val->cap) {
                v->data.list_val->cap *= 2;
                v->data.list_val->items = realloc(v->data.list_val->items, sizeof(Value*) * v->data.list_val->cap);
            }
            v->data.list_val->items[v->data.list_val->len++] = elem;
            j_skip_ws(j);
            if (j->s[j->pos] == ',') { j->pos++; j_skip_ws(j); continue; }
            break;
        }
    }
    j->pos++; /* skip ] */
    return v;
}

static Value *j_parse_dict(JParser *j, int pc) {
    j->pos++; /* skip { */
    Value *v = malloc(sizeof(Value));
    v->type = VAL_DICT;
    v->data.dict_val = malloc(sizeof(Dict));
    v->data.dict_val->cap = 16;
    v->data.dict_val->len = 0;
    v->data.dict_val->entries = malloc(sizeof(DictEntry) * 16);

    j_skip_ws(j);
    if (j->s[j->pos] != '}') {
        while (1) {
            j_skip_ws(j);
            char *key = j_parse_string(j);
            if (!key) break;
            j_skip_ws(j);
            if (j->s[j->pos] == ':') j->pos++;
            j_skip_ws(j);
            Value *val = j_parse_value(j, pc);
            if (!val) { free(key); break; }

            if (v->data.dict_val->len >= v->data.dict_val->cap) {
                v->data.dict_val->cap *= 2;
                v->data.dict_val->entries = realloc(v->data.dict_val->entries, sizeof(DictEntry) * v->data.dict_val->cap);
            }
            Dict *d = v->data.dict_val;
            d->entries[d->len].key = key;
            d->entries[d->len].val = val;
            d->len++;

            j_skip_ws(j);
            if (j->s[j->pos] == ',') { j->pos++; continue; }
            break;
        }
    }
    j->pos++; /* skip } */
    return v;
}

/* ===== Bytecode Loader ===== */

/* The bytecode json format is: {"instructions": [[op, arg], ...], "consts": [...]}
 * Instructions from Python compiler use [op_name, arg_index] format.
 * Constants include function objects like: {"args": [...], "bytecode": [...], "consts": [...]}
 */

typedef struct {
    Value **instrs;
    size_t n_instrs;
    Value **consts;
    size_t n_consts;
    int pc_addr;
} Bytecode;

/* ===== VM Operations ===== */

static VM *vm_create(void) {
    VM *vm = calloc(1, sizeof(VM));
    vm->global_env = malloc(sizeof(Dict));
    vm->global_env->cap = 64;
    vm->global_env->len = 0;
    vm->global_env->entries = malloc(sizeof(DictEntry) * 64);
    return vm;
}

static Dict *vm_dict_get(Dict *d, const char *key) {
    return NULL; /* unused directly */
}

static Value *dict_get(Dict *d, const char *key) {
    for (size_t i = 0; i < d->len; i++) {
        if (strcmp(d->entries[i].key, key) == 0)
            return d->entries[i].val;
    }
    return NULL;
}

static void dict_set(Dict *d, const char *key, Value *val) {
    for (size_t i = 0; i < d->len; i++) {
        if (strcmp(d->entries[i].key, key) == 0) {
            d->entries[i].val = val;
            return;
        }
    }
    if (d->len >= d->cap) {
        d->cap *= 2;
        d->entries = realloc(d->entries, sizeof(DictEntry) * d->cap);
    }
    d->entries[d->len].key = strdup(key);
    d->entries[d->len].val = val;
    d->len++;
}

static void list_append(List *l, Value *v) {
    if (l->len >= l->cap) {
        l->cap = l->cap == 0 ? 4 : l->cap * 2;
        l->items = realloc(l->items, sizeof(Value*) * l->cap);
    }
    l->items[l->len++] = v;
}

static void dict_remove(Dict *d, const char *key) {
    for (size_t i = 0; i < d->len; i++) {
        if (strcmp(d->entries[i].key, key) == 0) {
            free(d->entries[i].key);
            free_value(d->entries[i].val);
            for (size_t j = i; j < d->len - 1; j++) {
                d->entries[j] = d->entries[j + 1];
            }
            d->len--;
            return;
        }
    }
}

static int values_equal(Value *a, Value *b) {
    if (!a && !b) return 1;
    if (!a || !b) return 0;
    if (a->type != b->type) return 0;
    if (a->type == VAL_NULL) return 1;
    if (a->type == VAL_BOOL) return a->data.bool_val == b->data.bool_val;
    if (a->type == VAL_INT) return a->data.int_val == b->data.int_val;
    if (a->type == VAL_FLOAT) return a->data.float_val == b->data.float_val;
    if (a->type == VAL_STRING) return strcmp(a->data.str_val, b->data.str_val) == 0;
    return 0;
}

static Value *vm_get_var(VM *vm, const char *name) {
    /* search frames bottom-up */
    for (int i = vm->frame_sp - 1; i >= 0; i--) {
        Value *v = dict_get(vm->frames[i].env, name);
        if (v) return v;
    }
    /* search global */
    return dict_get(vm->global_env, name);
}

static void vm_set_var(VM *vm, const char *name, Value *val) {
    /* search frames bottom-up for existing binding, update if found */
    for (int i = vm->frame_sp - 1; i >= 0; i--) {
        Value *old = dict_get(vm->frames[i].env, name);
        if (old) {
            dict_set(vm->frames[i].env, name, val);
            return;
        }
    }
    /* check global */
    if (dict_get(vm->global_env, name)) {
        dict_set(vm->global_env, name, val);
        return;
    }
    /* not found - create in current frame */
    if (vm->frame_sp > 0) {
        dict_set(vm->frames[vm->frame_sp - 1].env, name, val);
    } else {
        dict_set(vm->global_env, name, val);
    }
}

static void vm_push(VM *vm, Value *v) {
    if (vm->sp < MAX_STACK) vm->stack[vm->sp++] = v;
}

static Value *vm_pop(VM *vm) {
    if (vm->sp <= 0) {
        Value *v = malloc(sizeof(Value));
        v->type = VAL_NULL;
        return v;
    }
    return vm->stack[--vm->sp];
}

static Value *vm_peek(VM *vm) {
    if (vm->sp <= 0) return NULL;
    return vm->stack[vm->sp - 1];
}

static int to_bool(Value *v) {
    if (!v) return 0;
    switch (v->type) {
        case VAL_NULL: return 0;
        case VAL_BOOL: return v->data.bool_val;
        case VAL_INT: return v->data.int_val != 0;
        case VAL_FLOAT: return v->data.float_val != 0.0;
        default: return 1;
    }
}

static double to_number(Value *v) {
    if (!v) return 0;
    switch (v->type) {
        case VAL_INT: return (double)v->data.int_val;
        case VAL_FLOAT: return v->data.float_val;
        case VAL_BOOL: return v->data.bool_val ? 1.0 : 0.0;
        default: return 0;
    }
}

static Value *num_to_val(double d) {
    Value *v = malloc(sizeof(Value));
    if (d == (int64_t)d) {
        v->type = VAL_INT;
        v->data.int_val = (int64_t)d;
    } else {
        v->type = VAL_FLOAT;
        v->data.float_val = d;
    }
    return v;
}

static void vm_print_val(Value *v) {
    if (!v) { printf("null\n"); fflush(stdout); return; }
    switch (v->type) {
        case VAL_NULL: printf("null\n"); break;
        case VAL_INT: printf("%lld\n", (long long)v->data.int_val); break;
        case VAL_FLOAT: printf("%g\n", v->data.float_val); break;
        case VAL_BOOL: printf("%s\n", v->data.bool_val ? "true" : "false"); break;
        case VAL_STRING: printf("%s\n", v->data.str_val); break;
        case VAL_LIST: printf("[list:%zu]\n", v->data.list_val->len); break;
        case VAL_DICT: printf("{dict:%zu}\n", v->data.dict_val->len); break;
        case VAL_FUNC: printf("<func:%s>\n", v->data.func_val->name ? v->data.func_val->name : "anon"); break;
        case VAL_CLASS: printf("<class>\n"); break;
        case VAL_INSTANCE: printf("<instance>\n"); break;
        default: printf("<unknown>\n"); break;
    }
    fflush(stdout);
}

static Value *val_clone(Value *v) {
    if (!v) return NULL;
    Value *n = malloc(sizeof(Value));
    memcpy(n, v, sizeof(Value));
    if (v->type == VAL_STRING && v->data.str_val)
        n->data.str_val = strdup(v->data.str_val);
    return n;
}

/* Convert Python-compiled bytecode format from JSON into VM format */
static int vm_execute(VM *vm);

static void load_bytecode_from_json(VM *vm, Value *json_bc) {
    /* json_bc is a dict - could be single-module or multi-module format */
    if (!json_bc || json_bc->type != VAL_DICT) return;

    /* Check for multi-module bundle format: {"modules": {"name": {instrs, consts}, ...}} */
    Value *modules = dict_get(json_bc->data.dict_val, "modules");

    if (modules && modules->type == VAL_DICT) {
        /* Multi-module bundle: execute each module, merge envs */
        Dict *mod_dict = modules->data.dict_val;
        for (size_t mi = 0; mi < mod_dict->len; mi++) {
            const char *mod_name = mod_dict->entries[mi].key;
            Value *mod = mod_dict->entries[mi].val;

            if (!mod || mod->type != VAL_DICT) continue;

            Value *instrs_val = dict_get(mod->data.dict_val, "instructions");
            Value *consts_val = dict_get(mod->data.dict_val, "consts");

            /* Set up a program frame for this module */
            Func *program = calloc(1, sizeof(Func));
            program->name = strdup(mod_name);

            if (instrs_val && instrs_val->type == VAL_LIST) {
                program->n_instrs = instrs_val->data.list_val->len;
                program->bytecode = instrs_val->data.list_val->items;
            }

            if (consts_val && consts_val->type == VAL_LIST) {
                program->n_consts = consts_val->data.list_val->len;
                program->consts = consts_val->data.list_val->items;
            }

            vm->frame_sp = 1;
            vm->frames[0].func = program;
            vm->frames[0].instrs = program->bytecode;
            vm->frames[0].n_instrs = program->n_instrs;
            vm->frames[0].consts = program->consts;
            vm->frames[0].n_consts = program->n_consts;
            vm->frames[0].pc = 0;
            vm->frames[0].env = malloc(sizeof(Dict));
            vm->frames[0].env->cap = 64;
            vm->frames[0].env->len = 0;
            vm->frames[0].env->entries = malloc(sizeof(DictEntry) * 64);

            /* Execute this module */
            vm_execute(vm);
            vm->sp = 0;
            /* Merge module env into global env */
            Dict *mod_env = vm->frames[0].env;
            for (size_t j = 0; j < mod_env->len; j++) {
                dict_set(vm->global_env, mod_env->entries[j].key,
                         val_clone(mod_env->entries[j].val));
            }

            /* Clean up module frame env entries (but NOT the values, they're shared with global) */
            for (size_t j = 0; j < mod_env->len; j++) {
                free(mod_env->entries[j].key);
            }
            free(mod_env->entries);
            free(mod_env);
            free(program->name);
            free(program);
        }
        /* Reset frame_sp - global env has all definitions now */
        vm->frame_sp = 0;
    } else {
        /* Single-module format: {"instructions": [...], "consts": [...]} */
        Value *instrs_val = dict_get(json_bc->data.dict_val, "instructions");
        Value *consts_val = dict_get(json_bc->data.dict_val, "consts");

        vm->frame_sp = 1;
        Func *program = calloc(1, sizeof(Func));
        program->name = strdup("__main__");

        if (instrs_val && instrs_val->type == VAL_LIST) {
            program->n_instrs = instrs_val->data.list_val->len;
            program->bytecode = instrs_val->data.list_val->items;
        }

        if (consts_val && consts_val->type == VAL_LIST) {
            program->n_consts = consts_val->data.list_val->len;
            program->consts = consts_val->data.list_val->items;
        }

        vm->frames[0].func = program;
        vm->frames[0].instrs = program->bytecode;
        vm->frames[0].n_instrs = program->n_instrs;
        vm->frames[0].consts = program->consts;
        vm->frames[0].n_consts = program->n_consts;
        vm->frames[0].pc = 0;
        vm->frames[0].env = malloc(sizeof(Dict));
        vm->frames[0].env->cap = 64;
        vm->frames[0].env->len = 0;
        vm->frames[0].env->entries = malloc(sizeof(DictEntry) * 64);
    }
}

static Value *mk_list_val(List *list) {
    Value *v = malloc(sizeof(Value));
    v->type = VAL_LIST;
    v->data.list_val = list;
    return v;
}

static Value *mk_dict_val(Dict *d) {
    Value *v = malloc(sizeof(Value));
    v->type = VAL_DICT;
    v->data.dict_val = d;
    return v;
}

static Value *mk_bool_val(int b) {
    Value *v = malloc(sizeof(Value));
    v->type = VAL_BOOL;
    v->data.bool_val = b;
    return v;
}

static Value *mk_null_val(void) {
    Value *v = malloc(sizeof(Value));
    v->type = VAL_NULL;
    return v;
}

/* In the JSON bytecode, instructions are [[op_name, arg], ...]
 * Constants are [val1, val2, ...]
 * Function objects in constants: {"args": [...], "bytecode": [...], "consts": [...]}
 */

static Func *load_func_from_json(Value *fobj) {
    if (!fobj || fobj->type != VAL_DICT) return NULL;

    Func *f = calloc(1, sizeof(Func));

    Value *args_v = dict_get(fobj->data.dict_val, "args");
    Value *bc_v = dict_get(fobj->data.dict_val, "bytecode");
    Value *consts_v = dict_get(fobj->data.dict_val, "consts");

    if (args_v && args_v->type == VAL_LIST) {
        f->nargs = args_v->data.list_val->len;
        f->arg_names = malloc(sizeof(char*) * f->nargs);
        for (size_t i = 0; i < f->nargs; i++) {
            Value *av = args_v->data.list_val->items[i];
            f->arg_names[i] = (av && av->type == VAL_STRING) ? strdup(av->data.str_val) : strdup("_");
        }
    }

    if (bc_v && bc_v->type == VAL_LIST) {
        f->n_instrs = bc_v->data.list_val->len;
        f->bytecode = bc_v->data.list_val->items;
    }

    if (consts_v && consts_v->type == VAL_LIST) {
        f->n_consts = consts_v->data.list_val->len;
        f->consts = consts_v->data.list_val->items;
    }

    return f;
}

static int vm_execute(VM *vm);

static int vm_call_func(VM *vm, Func *f, Value **args, size_t nargs) {
    if (vm->frame_sp >= MAX_FRAMES) { fprintf(stderr, "VM: frame overflow\n"); return -1; }

    int fi = vm->frame_sp++;

    vm->frames[fi].func = f;
    vm->frames[fi].instrs = f->bytecode;
    vm->frames[fi].n_instrs = f->n_instrs;
    vm->frames[fi].consts = f->consts;
    vm->frames[fi].n_consts = f->n_consts;
    vm->frames[fi].pc = 0;
    vm->frames[fi].env = malloc(sizeof(Dict));
    vm->frames[fi].env->cap = 32;
    vm->frames[fi].env->len = 0;
    vm->frames[fi].env->entries = malloc(sizeof(DictEntry) * 32);

    vm->frames[fi].saved_sp = vm->sp;

    /* bind args */
    for (size_t i = 0; i < nargs && i < f->nargs; i++) {
        dict_set(vm->frames[fi].env, f->arg_names[i], args[i]);
    }

    return 0;
}

static int vm_execute(VM *vm) {
    while (vm->frame_sp > 0) {
        int fi = vm->frame_sp - 1;
        if (vm->frames[fi].pc >= (int)vm->frames[fi].n_instrs) {
            /* frame done, implicit return null */
            if (vm->frame_sp == 1) vm->ret_val = mk_null_val();
            vm->frame_sp--;
            continue;
        }

        Value *instr_pair = vm->frames[fi].instrs[vm->frames[fi].pc];
        vm->frames[fi].pc++;

        if (!instr_pair || instr_pair->type != VAL_LIST) continue;
        List *pair = instr_pair->data.list_val;
        if (pair->len < 2) continue;

        Value *opv = pair->items[0];
        Value *argv = pair->items[1];

        if (!opv || opv->type != VAL_STRING) continue;
        const char *op = opv->data.str_val;

        if (strcmp(op, "HALT") == 0) {
            vm->frame_sp = 0;
            break;
        }

        if (strcmp(op, "LOAD_CONST") == 0) {
            int idx = argv ? (int)argv->data.int_val : 0;
            if (idx >= 0 && (size_t)idx < vm->frames[fi].n_consts) {
                vm_push(vm, val_clone(vm->frames[fi].consts[idx]));
            }
            continue;
        }

        if (strcmp(op, "LOAD_NAME") == 0) {
            const char *name = argv ? argv->data.str_val : NULL;
            if (!name) { vm_push(vm, mk_null_val()); continue; }
            Value *v = vm_get_var(vm, name);
            if (v) { vm_push(vm, val_clone(v)); }
            else { vm_push(vm, mk_null_val()); }
            continue;
        }

        if (strcmp(op, "STORE_NAME") == 0) {
            Value *val = vm_pop(vm);
            vm_set_var(vm, argv->data.str_val, val);
            continue;
        }

        if (strcmp(op, "POP_TOP") == 0) {
            vm_pop(vm);
            continue;
        }

        if (strcmp(op, "PRINT") == 0) {
            Value *v = vm_pop(vm);
            vm_print_val(v);
            continue;
        }

        if (strcmp(op, "BINARY_ADD") == 0) {
            Value *r = vm_pop(vm), *l = vm_pop(vm);
            if (l && l->type == VAL_STRING) {
                char buf[4096];
                if (r && r->type == VAL_STRING)
                    snprintf(buf, sizeof(buf), "%s%s", l->data.str_val, r->data.str_val);
                else if (r && r->type == VAL_INT)
                    snprintf(buf, sizeof(buf), "%s%lld", l->data.str_val, (long long)r->data.int_val);
                else if (r && r->type == VAL_FLOAT)
                    snprintf(buf, sizeof(buf), "%s%g", l->data.str_val, r->data.float_val);
                else if (r && r->type == VAL_BOOL)
                    snprintf(buf, sizeof(buf), "%s%s", l->data.str_val, r->data.bool_val ? "true" : "false");
                else if (r && r->type == VAL_NULL)
                    snprintf(buf, sizeof(buf), "%snull", l->data.str_val);
                else
                    snprintf(buf, sizeof(buf), "%s", l->data.str_val);
                Value *v = malloc(sizeof(Value)); v->type = VAL_STRING; v->data.str_val = strdup(buf);
                vm_push(vm, v);
            } else if (r && r->type == VAL_STRING) {
                char buf[4096];
                if (l && l->type == VAL_INT)
                    snprintf(buf, sizeof(buf), "%lld%s", (long long)l->data.int_val, r->data.str_val);
                else if (l && l->type == VAL_FLOAT)
                    snprintf(buf, sizeof(buf), "%g%s", l->data.float_val, r->data.str_val);
                else if (l && l->type == VAL_BOOL)
                    snprintf(buf, sizeof(buf), "%s%s", l->data.bool_val ? "true" : "false", r->data.str_val);
                else if (!l || l->type == VAL_NULL)
                    snprintf(buf, sizeof(buf), "null%s", r->data.str_val);
                else
                    snprintf(buf, sizeof(buf), "%s", r->data.str_val);
                Value *v = malloc(sizeof(Value)); v->type = VAL_STRING; v->data.str_val = strdup(buf);
                vm_push(vm, v);
            } else {
                vm_push(vm, num_to_val(to_number(l) + to_number(r)));
            }
            continue;
        }

        if (strcmp(op, "BINARY_SUB") == 0) {
            Value *r = vm_pop(vm), *l = vm_pop(vm);
            vm_push(vm, num_to_val(to_number(l) - to_number(r)));
            continue;
        }

        if (strcmp(op, "BINARY_MUL") == 0) {
            Value *r = vm_pop(vm), *l = vm_pop(vm);
            vm_push(vm, num_to_val(to_number(l) * to_number(r)));
            continue;
        }

        if (strcmp(op, "BINARY_DIV") == 0) {
            Value *r = vm_pop(vm), *l = vm_pop(vm);
            double rv = to_number(r);
            vm_push(vm, num_to_val(rv != 0 ? to_number(l) / rv : 0));
            continue;
        }

        if (strcmp(op, "BINARY_BITAND") == 0) {
            Value *r = vm_pop(vm), *l = vm_pop(vm);
            vm_push(vm, num_to_val((int64_t)to_number(l) & (int64_t)to_number(r)));
            continue;
        }

        if (strcmp(op, "BINARY_BITOR") == 0) {
            Value *r = vm_pop(vm), *l = vm_pop(vm);
            vm_push(vm, num_to_val((int64_t)to_number(l) | (int64_t)to_number(r)));
            continue;
        }

        if (strcmp(op, "BINARY_BITXOR") == 0) {
            Value *r = vm_pop(vm), *l = vm_pop(vm);
            vm_push(vm, num_to_val((int64_t)to_number(l) ^ (int64_t)to_number(r)));
            continue;
        }

        if (strcmp(op, "BINARY_LSHIFT") == 0) {
            Value *r = vm_pop(vm), *l = vm_pop(vm);
            vm_push(vm, num_to_val((int64_t)to_number(l) << (int64_t)to_number(r)));
            continue;
        }

        if (strcmp(op, "BINARY_RSHIFT") == 0) {
            Value *r = vm_pop(vm), *l = vm_pop(vm);
            vm_push(vm, num_to_val((int64_t)to_number(l) >> (int64_t)to_number(r)));
            continue;
        }

        if (strcmp(op, "COMPARE_OP") == 0) {
            Value *r = vm_pop(vm), *l = vm_pop(vm);
            const char *cop = argv ? argv->data.str_val : "==";
            int res = 0;
            int is_eq = (strcmp(cop, "EQEQ") == 0 || strcmp(cop, "BANGEQ") == 0);
            if (is_eq) {
                if (!l && !r) res = 1;
                else if (!l || !r) res = 0;
                else if (l->type == VAL_NULL && r->type == VAL_NULL) res = 1;
                else if (l->type == VAL_NULL || r->type == VAL_NULL) res = 0;
                else if (l->type == VAL_BOOL && r->type == VAL_BOOL)
                    res = (l->data.bool_val == r->data.bool_val);
                else if ((l->type == VAL_INT || l->type == VAL_FLOAT) &&
                         (r->type == VAL_INT || r->type == VAL_FLOAT))
                    res = (to_number(l) == to_number(r));
                else if (l->type == VAL_STRING && r->type == VAL_STRING)
                    res = (strcmp(l->data.str_val, r->data.str_val) == 0);
                else
                    res = 0;
                if (strcmp(cop, "BANGEQ") == 0) res = !res;
            } else if (l && r && l->type == VAL_STRING && r->type == VAL_STRING) {
                int cmp = strcmp(l->data.str_val, r->data.str_val);
                if (strcmp(cop, "GT") == 0) res = (cmp > 0);
                else if (strcmp(cop, "LT") == 0) res = (cmp < 0);
                else if (strcmp(cop, "GTE") == 0) res = (cmp >= 0);
                else if (strcmp(cop, "LTE") == 0) res = (cmp <= 0);
            } else {
                double lv = to_number(l), rv = to_number(r);
                if (strcmp(cop, "GT") == 0) res = (lv > rv);
                else if (strcmp(cop, "LT") == 0) res = (lv < rv);
                else if (strcmp(cop, "GTE") == 0) res = (lv >= rv);
                else if (strcmp(cop, "LTE") == 0) res = (lv <= rv);
            }
            vm_push(vm, mk_bool_val(res));
            continue;
        }

        if (strcmp(op, "UNARY_NOT") == 0) {
            Value *v = vm_pop(vm);
            vm_push(vm, mk_bool_val(!to_bool(v)));
            continue;
        }

        if (strcmp(op, "UNARY_NEG") == 0) {
            Value *v = vm_pop(vm);
            vm_push(vm, num_to_val(-to_number(v)));
            continue;
        }

        if (strcmp(op, "JUMP") == 0) {
            vm->frames[fi].pc = (int)argv->data.int_val;
            continue;
        }

        if (strcmp(op, "JUMP_IF_FALSE") == 0) {
            Value *cond = vm_pop(vm);
            if (!to_bool(cond))
                vm->frames[fi].pc = (int)argv->data.int_val;
            continue;
        }

        if (strcmp(op, "CONTINUE") == 0 || strcmp(op, "BREAK") == 0) {
            /* Simple handling - these are complex with nested loops */
            /* For now, treat as nop */
            continue;
        }

        if (strcmp(op, "CALL_FUNCTION") == 0) {
            if (!argv || argv->type != VAL_LIST || argv->data.list_val->len < 2) continue;
            const char *fname = argv->data.list_val->items[0]->data.str_val;
            int nargs = (int)argv->data.list_val->items[1]->data.int_val;

            Value *args[64] = {0};
            for (int i = nargs - 1; i >= 0; i--) args[i] = vm_pop(vm);

            /* Built-ins */
            if (strcmp(fname, "len") == 0) {
                Value *v = args[0];
                int ln = 0;
                if (v && v->type == VAL_LIST) ln = (int)v->data.list_val->len;
                else if (v && v->type == VAL_STRING) ln = (int)strlen(v->data.str_val);
                else if (v && v->type == VAL_DICT) ln = (int)v->data.dict_val->len;
                vm_push(vm, num_to_val(ln));
                continue;
            }
            if (strcmp(fname, "push") == 0) {
                if (args[0] && args[0]->type == VAL_LIST) {
                    List *l = args[0]->data.list_val;
                    if (l->len >= l->cap) { l->cap *= 2; l->items = realloc(l->items, sizeof(Value*) * l->cap); }
                    l->items[l->len++] = args[1];
                }
                vm_push(vm, mk_null_val());
                continue;
            }
            if (strcmp(fname, "print") == 0) {
                vm_print_val(args[0]);
                vm_push(vm, mk_null_val());
                continue;
            }
            if (strcmp(fname, "type") == 0) {
                const char *t = "object";
                if (!args[0] || args[0]->type == VAL_NULL) t = "null";
                else if (args[0]->type == VAL_BOOL) t = "bool";
                else if (args[0]->type == VAL_STRING) t = "string";
                else if (args[0]->type == VAL_INT || args[0]->type == VAL_FLOAT) t = "number";
                Value *v = malloc(sizeof(Value)); v->type = VAL_STRING; v->data.str_val = strdup(t);
                vm_push(vm, v);
                continue;
            }
            if (strcmp(fname, "str") == 0) {
                char buf[256];
                Value *av = args[0];
                if (!av || av->type == VAL_NULL) snprintf(buf, sizeof(buf), "null");
                else if (av->type == VAL_BOOL) snprintf(buf, sizeof(buf), "%s", av->data.bool_val ? "true" : "false");
                else if (av->type == VAL_INT) snprintf(buf, sizeof(buf), "%lld", (long long)av->data.int_val);
                else if (av->type == VAL_FLOAT) snprintf(buf, sizeof(buf), "%g", av->data.float_val);
                else if (av->type == VAL_STRING) snprintf(buf, sizeof(buf), "%s", av->data.str_val);
                else snprintf(buf, sizeof(buf), "<%s>", av->type == VAL_LIST ? "list" : av->type == VAL_DICT ? "dict" : "object");
                Value *v = malloc(sizeof(Value)); v->type = VAL_STRING; v->data.str_val = strdup(buf);
                vm_push(vm, v);
                continue;
            }
            if (strcmp(fname, "int") == 0) {
                vm_push(vm, num_to_val((int64_t)to_number(args[0])));
                continue;
            }
            if (strcmp(fname, "typeof") == 0) {
                const char *t = "object";
                if (!args[0] || args[0]->type == VAL_NULL) t = "nil";
                else if (args[0]->type == VAL_BOOL) t = "bool";
                else if (args[0]->type == VAL_STRING) t = "str";
                else if (args[0]->type == VAL_INT) t = "int";
                else if (args[0]->type == VAL_FLOAT) t = "float";
                else if (args[0]->type == VAL_LIST) t = "list";
                else if (args[0]->type == VAL_DICT) t = "dict";
                else if (args[0]->type == VAL_FUNC) t = "function";
                else if (args[0]->type == VAL_CLASS) t = "class";
                else if (args[0]->type == VAL_INSTANCE) t = "instance";
                Value *v = malloc(sizeof(Value)); v->type = VAL_STRING; v->data.str_val = strdup(t);
                vm_push(vm, v);
                continue;
            }

            /* ── Math Builtins (libm) ── */
            if (strcmp(fname, "math_sin") == 0) {
                vm_push(vm, num_to_val(sin(to_number(args[0]))));
                continue;
            }
            if (strcmp(fname, "math_cos") == 0) {
                vm_push(vm, num_to_val(cos(to_number(args[0]))));
                continue;
            }
            if (strcmp(fname, "math_tan") == 0) {
                vm_push(vm, num_to_val(tan(to_number(args[0]))));
                continue;
            }
            if (strcmp(fname, "math_asin") == 0) {
                double x = to_number(args[0]);
                if (x < -1.0 || x > 1.0) { vm_push(vm, mk_null_val()); continue; }
                vm_push(vm, num_to_val(asin(x)));
                continue;
            }
            if (strcmp(fname, "math_acos") == 0) {
                double x = to_number(args[0]);
                if (x < -1.0 || x > 1.0) { vm_push(vm, mk_null_val()); continue; }
                vm_push(vm, num_to_val(acos(x)));
                continue;
            }
            if (strcmp(fname, "math_atan") == 0) {
                vm_push(vm, num_to_val(atan(to_number(args[0]))));
                continue;
            }
            if (strcmp(fname, "math_atan2") == 0) {
                vm_push(vm, num_to_val(atan2(to_number(args[0]), to_number(args[1]))));
                continue;
            }
            if (strcmp(fname, "math_sinh") == 0) {
                vm_push(vm, num_to_val(sinh(to_number(args[0]))));
                continue;
            }
            if (strcmp(fname, "math_cosh") == 0) {
                vm_push(vm, num_to_val(cosh(to_number(args[0]))));
                continue;
            }
            if (strcmp(fname, "math_tanh") == 0) {
                vm_push(vm, num_to_val(tanh(to_number(args[0]))));
                continue;
            }
            if (strcmp(fname, "math_exp") == 0) {
                vm_push(vm, num_to_val(exp(to_number(args[0]))));
                continue;
            }
            if (strcmp(fname, "math_log") == 0) {
                double x = to_number(args[0]);
                if (x <= 0.0) { vm_push(vm, mk_null_val()); continue; }
                vm_push(vm, num_to_val(log(x)));
                continue;
            }
            if (strcmp(fname, "math_log10") == 0) {
                double x = to_number(args[0]);
                if (x <= 0.0) { vm_push(vm, mk_null_val()); continue; }
                vm_push(vm, num_to_val(log10(x)));
                continue;
            }
            if (strcmp(fname, "math_log2") == 0) {
                double x = to_number(args[0]);
                if (x <= 0.0) { vm_push(vm, mk_null_val()); continue; }
                vm_push(vm, num_to_val(log2(x)));
                continue;
            }
            if (strcmp(fname, "math_sqrt") == 0) {
                double x = to_number(args[0]);
                if (x < 0.0) { vm_push(vm, mk_null_val()); continue; }
                vm_push(vm, num_to_val(sqrt(x)));
                continue;
            }
            if (strcmp(fname, "math_pow") == 0) {
                vm_push(vm, num_to_val(pow(to_number(args[0]), to_number(args[1]))));
                continue;
            }
            if (strcmp(fname, "math_floor") == 0) {
                vm_push(vm, num_to_val(floor(to_number(args[0]))));
                continue;
            }
            if (strcmp(fname, "math_ceil") == 0) {
                vm_push(vm, num_to_val(ceil(to_number(args[0]))));
                continue;
            }
            if (strcmp(fname, "math_fabs") == 0) {
                vm_push(vm, num_to_val(fabs(to_number(args[0]))));
                continue;
            }
            if (strcmp(fname, "math_fmod") == 0) {
                double y = to_number(args[1]);
                if (y == 0.0) { vm_push(vm, mk_null_val()); continue; }
                vm_push(vm, num_to_val(fmod(to_number(args[0]), y)));
                continue;
            }
            if (strcmp(fname, "math_cbrt") == 0) {
                vm_push(vm, num_to_val(cbrt(to_number(args[0]))));
                continue;
            }
            if (strcmp(fname, "math_hypot") == 0) {
                vm_push(vm, num_to_val(hypot(to_number(args[0]), to_number(args[1]))));
                continue;
            }
            if (strcmp(fname, "math_erf") == 0) {
                vm_push(vm, num_to_val(erf(to_number(args[0]))));
                continue;
            }
            if (strcmp(fname, "math_erfc") == 0) {
                vm_push(vm, num_to_val(erfc(to_number(args[0]))));
                continue;
            }
            if (strcmp(fname, "math_tgamma") == 0) {
                vm_push(vm, num_to_val(tgamma(to_number(args[0]))));
                continue;
            }
            if (strcmp(fname, "math_lgamma") == 0) {
                vm_push(vm, num_to_val(lgamma(to_number(args[0]))));
                continue;
            }

            /* ── Dict Builtins ── */
            if (strcmp(fname, "dict_keys") == 0) {
                if (nargs != 1 || !args[0] || args[0]->type != VAL_DICT) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                List *l = calloc(1, sizeof(List));
                l->cap = args[0]->data.dict_val->len;
                l->items = calloc(l->cap, sizeof(Value*));
                for (size_t i = 0; i < args[0]->data.dict_val->len; i++) {
                    Value *v = malloc(sizeof(Value));
                    v->type = VAL_STRING;
                    v->data.str_val = strdup(args[0]->data.dict_val->entries[i].key);
                    l->items[l->len++] = v;
                }
                vm_push(vm, mk_list_val(l));
                continue;
            }
            if (strcmp(fname, "dict_values") == 0) {
                if (nargs != 1 || !args[0] || args[0]->type != VAL_DICT) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                List *l = calloc(1, sizeof(List));
                l->cap = args[0]->data.dict_val->len;
                l->items = calloc(l->cap, sizeof(Value*));
                for (size_t i = 0; i < args[0]->data.dict_val->len; i++) {
                    l->items[l->len++] = val_clone(args[0]->data.dict_val->entries[i].val);
                }
                vm_push(vm, mk_list_val(l));
                continue;
            }
            if (strcmp(fname, "dict_items") == 0) {
                if (nargs != 1 || !args[0] || args[0]->type != VAL_DICT) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                List *outer = calloc(1, sizeof(List));
                outer->cap = args[0]->data.dict_val->len;
                outer->items = calloc(outer->cap, sizeof(Value*));
                for (size_t i = 0; i < args[0]->data.dict_val->len; i++) {
                    List *pair = calloc(1, sizeof(List));
                    pair->cap = 2;
                    pair->items = calloc(2, sizeof(Value*));
                    Value *k = malloc(sizeof(Value));
                    k->type = VAL_STRING;
                    k->data.str_val = strdup(args[0]->data.dict_val->entries[i].key);
                    pair->items[0] = k;
                    pair->items[1] = val_clone(args[0]->data.dict_val->entries[i].val);
                    pair->len = 2;
                    outer->items[outer->len++] = mk_list_val(pair);
                }
                vm_push(vm, mk_list_val(outer));
                continue;
            }
            if (strcmp(fname, "dict_get") == 0) {
                if (nargs < 2 || !args[0] || args[0]->type != VAL_DICT) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                if (!args[1] || args[1]->type != VAL_STRING) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                Value *v = dict_get(args[0]->data.dict_val, args[1]->data.str_val);
                if (v) {
                    vm_push(vm, val_clone(v));
                } else {
                    if (nargs >= 3 && args[2]) {
                        vm_push(vm, val_clone(args[2]));
                    } else {
                        vm_push(vm, mk_null_val());
                    }
                }
                continue;
            }
            if (strcmp(fname, "dict_has") == 0) {
                if (nargs != 2 || !args[0] || args[0]->type != VAL_DICT || !args[1] || args[1]->type != VAL_STRING) {
                    vm_push(vm, num_to_val(0));
                    continue;
                }
                int has = dict_get(args[0]->data.dict_val, args[1]->data.str_val) != NULL;
                vm_push(vm, has ? num_to_val(1) : num_to_val(0));
                continue;
            }
            if (strcmp(fname, "dict_pop") == 0) {
                if (nargs < 2 || !args[0] || args[0]->type != VAL_DICT || !args[1] || args[1]->type != VAL_STRING) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                Value *v = dict_get(args[0]->data.dict_val, args[1]->data.str_val);
                if (v) {
                    dict_remove(args[0]->data.dict_val, args[1]->data.str_val);
                    vm_push(vm, val_clone(v));
                } else {
                    if (nargs >= 3 && args[2]) {
                        vm_push(vm, val_clone(args[2]));
                    } else {
                        vm_push(vm, mk_null_val());
                    }
                }
                continue;
            }
            if (strcmp(fname, "dict_clear") == 0) {
                if (nargs != 1 || !args[0] || args[0]->type != VAL_DICT) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                for (size_t i = 0; i < args[0]->data.dict_val->len; i++) {
                    if (args[0]->data.dict_val->entries[i].key)
                        free(args[0]->data.dict_val->entries[i].key);
                    if (args[0]->data.dict_val->entries[i].val)
                        free_value(args[0]->data.dict_val->entries[i].val);
                }
                args[0]->data.dict_val->len = 0;
                vm_push(vm, mk_null_val());
                continue;
            }
            if (strcmp(fname, "dict_merge") == 0) {
                if (nargs != 2 || !args[0] || args[0]->type != VAL_DICT || !args[1] || args[1]->type != VAL_DICT) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                Dict *target = args[0]->data.dict_val;
                Dict *source = args[1]->data.dict_val;
                for (size_t i = 0; i < source->len; i++) {
                    dict_set(target, source->entries[i].key, val_clone(source->entries[i].val));
                }
                vm_push(vm, args[0]);
                continue;
            }
            if (strcmp(fname, "dict_copy") == 0) {
                if (nargs != 1 || !args[0] || args[0]->type != VAL_DICT) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                Dict *src = args[0]->data.dict_val;
                Dict *dst = calloc(1, sizeof(Dict));
                dst->cap = src->len;
                dst->entries = calloc(dst->cap, sizeof(DictEntry));
                for (size_t i = 0; i < src->len; i++) {
                    dst->entries[dst->len].key = strdup(src->entries[i].key);
                    dst->entries[dst->len].val = val_clone(src->entries[i].val);
                    dst->len++;
                }
                vm_push(vm, mk_dict_val(dst));
                continue;
            }
            if (strcmp(fname, "dict_len") == 0) {
                if (nargs != 1 || !args[0] || args[0]->type != VAL_DICT) {
                    vm_push(vm, num_to_val(0));
                    continue;
                }
                vm_push(vm, num_to_val((int64_t)args[0]->data.dict_val->len));
                continue;
            }

            /* ── List Builtins ── */
            if (strcmp(fname, "list_append") == 0) {
                if (nargs != 2 || !args[0] || args[0]->type != VAL_LIST) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                list_append(args[0]->data.list_val, val_clone(args[1]));
                vm_push(vm, mk_null_val());
                continue;
            }
            if (strcmp(fname, "list_push") == 0) {
                if (nargs != 2 || !args[0] || args[0]->type != VAL_LIST) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                list_append(args[0]->data.list_val, val_clone(args[1]));
                vm_push(vm, mk_null_val());
                continue;
            }
            if (strcmp(fname, "list_pop") == 0) {
                if (nargs < 1 || !args[0] || args[0]->type != VAL_LIST) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                List *l = args[0]->data.list_val;
                if (l->len == 0) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                int idx = (int)l->len - 1;
                if (nargs >= 2) idx = (int)to_number(args[1]);
                if (idx < 0 || (size_t)idx >= l->len) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                Value *v = l->items[idx];
                for (size_t i = idx; i < l->len - 1; i++) {
                    l->items[i] = l->items[i + 1];
                }
                l->len--;
                vm_push(vm, v);
                continue;
            }
            if (strcmp(fname, "list_insert") == 0) {
                if (nargs != 3 || !args[0] || args[0]->type != VAL_LIST) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                List *l = args[0]->data.list_val;
                int idx = (int)to_number(args[1]);
                if (idx < 0) idx = (int)l->len + idx;
                if (idx < 0) idx = 0;
                if ((size_t)idx > l->len) idx = (int)l->len;
                if (l->len >= l->cap) {
                    size_t newcap = l->cap == 0 ? 4 : l->cap * 2;
                    l->items = realloc(l->items, newcap * sizeof(Value*));
                    l->cap = newcap;
                }
                for (int i = (int)l->len - 1; i >= idx; i--) {
                    l->items[i + 1] = l->items[i];
                }
                l->items[idx] = val_clone(args[2]);
                l->len++;
                vm_push(vm, mk_null_val());
                continue;
            }
            if (strcmp(fname, "list_remove") == 0) {
                if (nargs != 2 || !args[0] || args[0]->type != VAL_LIST) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                List *l = args[0]->data.list_val;
                for (size_t i = 0; i < l->len; i++) {
                    int eq = values_equal(l->items[i], args[1]);
                    if (eq) {
                        free_value(l->items[i]);
                        for (size_t j = i; j < l->len - 1; j++) {
                            l->items[j] = l->items[j + 1];
                        }
                        l->len--;
                        goto list_remove_done;
                    }
                }
                list_remove_done:
                vm_push(vm, mk_null_val());
                continue;
            }
            if (strcmp(fname, "list_index") == 0) {
                if (nargs < 2 || !args[0] || args[0]->type != VAL_LIST) {
                    vm_push(vm, num_to_val(-1));
                    continue;
                }
                List *l = args[0]->data.list_val;
                int start = 0;
                int end = (int)l->len;
                if (nargs >= 3) start = (int)to_number(args[2]);
                if (nargs >= 4) end = (int)to_number(args[3]);
                for (int i = start; i < end && i < (int)l->len; i++) {
                    if (values_equal(l->items[i], args[1])) {
                        vm_push(vm, num_to_val(i));
                        goto list_index_done;
                    }
                }
                vm_push(vm, num_to_val(-1));
                list_index_done:
                continue;
            }
            if (strcmp(fname, "list_extend") == 0) {
                if (nargs != 2 || !args[0] || args[0]->type != VAL_LIST || !args[1] || args[1]->type != VAL_LIST) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                List *target = args[0]->data.list_val;
                List *source = args[1]->data.list_val;
                size_t newlen = target->len + source->len;
                if (newlen > target->cap) {
                    target->items = realloc(target->items, newlen * sizeof(Value*));
                    target->cap = newlen;
                }
                for (size_t i = 0; i < source->len; i++) {
                    target->items[target->len++] = val_clone(source->items[i]);
                }
                vm_push(vm, mk_null_val());
                continue;
            }
            if (strcmp(fname, "list_reverse") == 0) {
                if (nargs != 1 || !args[0] || args[0]->type != VAL_LIST) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                List *l = args[0]->data.list_val;
                for (size_t i = 0; i < l->len / 2; i++) {
                    Value *tmp = l->items[i];
                    l->items[i] = l->items[l->len - 1 - i];
                    l->items[l->len - 1 - i] = tmp;
                }
                vm_push(vm, mk_null_val());
                continue;
            }
            if (strcmp(fname, "list_sort") == 0) {
                if (nargs != 1 || !args[0] || args[0]->type != VAL_LIST) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                List *l = args[0]->data.list_val;
                if (l->len > 1) {
                    /* Simple bubble sort for C VM - acceptable for small lists */
                    for (size_t i = 0; i < l->len - 1; i++) {
                        for (size_t j = 0; j < l->len - i - 1; j++) {
                            double a = to_number(l->items[j]);
                            double b = to_number(l->items[j+1]);
                            if (a > b) {
                                Value *tmp = l->items[j];
                                l->items[j] = l->items[j+1];
                                l->items[j+1] = tmp;
                            }
                        }
                    }
                }
                vm_push(vm, mk_null_val());
                continue;
            }
            if (strcmp(fname, "list_slice") == 0) {
                if (nargs < 2 || !args[0] || args[0]->type != VAL_LIST) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                List *src = args[0]->data.list_val;
                int start = (int)to_number(args[1]);
                int end = (int)src->len;
                int step = 1;
                if (nargs >= 3) end = (int)to_number(args[2]);
                if (nargs >= 4) step = (int)to_number(args[3]);
                if (start < 0) start += (int)src->len;
                if (end < 0) end += (int)src->len;
                if (start < 0) start = 0;
                if (end > (int)src->len) end = (int)src->len;
                List *dst = calloc(1, sizeof(List));
                int count = 0;
                for (int i = start; i < end && i < (int)src->len; i += step) {
                    list_append(dst, val_clone(src->items[i]));
                    count++;
                }
                vm_push(vm, mk_list_val(dst));
                continue;
            }
            if (strcmp(fname, "list_count") == 0) {
                if (nargs != 2 || !args[0] || args[0]->type != VAL_LIST) {
                    vm_push(vm, num_to_val(0));
                    continue;
                }
                List *l = args[0]->data.list_val;
                int cnt = 0;
                for (size_t i = 0; i < l->len; i++) {
                    if (values_equal(l->items[i], args[1])) cnt++;
                }
                vm_push(vm, num_to_val(cnt));
                continue;
            }
            if (strcmp(fname, "list_clear") == 0) {
                if (nargs != 1 || !args[0] || args[0]->type != VAL_LIST) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                List *l = args[0]->data.list_val;
                for (size_t i = 0; i < l->len; i++) {
                    free_value(l->items[i]);
                }
                l->len = 0;
                vm_push(vm, mk_null_val());
                continue;
            }
            if (strcmp(fname, "list_copy") == 0) {
                if (nargs != 1 || !args[0] || args[0]->type != VAL_LIST) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                List *src = args[0]->data.list_val;
                List *dst = calloc(1, sizeof(List));
                dst->cap = src->len;
                dst->items = calloc(dst->cap, sizeof(Value*));
                for (size_t i = 0; i < src->len; i++) {
                    dst->items[dst->len++] = val_clone(src->items[i]);
                }
                vm_push(vm, mk_list_val(dst));
                continue;
            }
            if (strcmp(fname, "list_fill") == 0) {
                if (nargs != 3) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                int len = (int)to_number(args[1]);
                if (len < 0) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                List *l = calloc(1, sizeof(List));
                l->cap = len;
                l->items = calloc(l->cap, sizeof(Value*));
                for (int i = 0; i < len; i++) {
                    l->items[l->len++] = val_clone(args[2]);
                }
                vm_push(vm, mk_list_val(l));
                continue;
            }
            if (strcmp(fname, "list_reserve") == 0) {
                if (nargs != 2 || !args[0] || args[0]->type != VAL_LIST) {
                    vm_push(vm, mk_null_val());
                    continue;
                }
                List *l = args[0]->data.list_val;
                int cap = (int)to_number(args[1]);
                if ((size_t)cap > l->cap) {
                    l->items = realloc(l->items, cap * sizeof(Value*));
                    l->cap = cap;
                }
                vm_push(vm, mk_null_val());
                continue;
            }

            /* DZZW builtins */
            Value *dzzw_result = NULL;
            if (dzzw_run_builtin(vm, fname, args, nargs, &dzzw_result)) {
                vm_push(vm, dzzw_result);
                continue;
            }

            /* User function */
            Value *fn = vm_get_var(vm, fname);
            if (fn && fn->type == VAL_DICT) {
                /* This is a function dict from const pool */
                Func *f = load_func_from_json(fn);
                if (f) {
                    vm_call_func(vm, f, args, nargs);
                    continue;
                }
            }
            vm_push(vm, mk_null_val());
            continue;
        }

        if (strcmp(op, "CALL_METHOD") == 0) {
            /* CALL_METHOD [name, nargs] */
            if (!argv || argv->type != VAL_LIST || argv->data.list_val->len < 2) continue;
            const char *mname = argv->data.list_val->items[0]->data.str_val;
            int nargs = (int)argv->data.list_val->items[1]->data.int_val;

            Value *args[64] = {0};
            for (int i = nargs - 1; i >= 0; i--) args[i] = vm_pop(vm);
            Value *obj = vm_pop(vm);
            vm_push(vm, mk_null_val());
            continue;
        }

        if (strcmp(op, "CALL_NEW") == 0) {
            int nargs = (int)argv->data.int_val;
            Value *args[64] = {0};
            for (int i = nargs - 1; i >= 0; i--) args[i] = vm_pop(vm);
            Value *cls_wrapper = vm_pop(vm);
            /* Create instance */
            Instance *inst = calloc(1, sizeof(Instance));
            inst->attrs = malloc(sizeof(Dict));
            inst->attrs->cap = 16; inst->attrs->len = 0;
            inst->attrs->entries = malloc(sizeof(DictEntry) * 16);
            Value *v = malloc(sizeof(Value));
            v->type = VAL_INSTANCE; v->data.instance_val = inst;
            vm_push(vm, v);
            continue;
        }

        if (strcmp(op, "MAKE_CLASS") == 0) {
            Value *cls_def = vm_pop(vm);
            Value *v = malloc(sizeof(Value));
            v->type = VAL_CLASS;
            v->data.class_val = calloc(1, sizeof(Class));
            vm_push(vm, v);
            continue;
        }

        if (strcmp(op, "MAKE_LIST") == 0) {
            int n = (int)argv->data.int_val;
            List *l = malloc(sizeof(List));
            l->cap = n > 0 ? n : 8;
            l->len = n;
            l->items = malloc(sizeof(Value*) * l->cap);
            for (int i = n - 1; i >= 0; i--) l->items[i] = vm_pop(vm);
            vm_push(vm, mk_list_val(l));
            continue;
        }

        if (strcmp(op, "MAKE_DICT") == 0) {
            int n = (int)argv->data.int_val;
            Value *vals[128] = {0};
            for (int i = n * 2 - 1; i >= 0; i--) vals[i] = vm_pop(vm);
            Dict *d = malloc(sizeof(Dict));
            d->cap = n > 0 ? n : 8;
            d->len = n;
            d->entries = malloc(sizeof(DictEntry) * d->cap);
            for (int i = 0; i < n; i++) {
                d->entries[i].key = strdup(vals[i*2]->data.str_val);
                d->entries[i].val = vals[i*2+1];
            }
            vm_push(vm, mk_dict_val(d));
            continue;
        }

        if (strcmp(op, "GET_ITEM") == 0) {
            Value *idx = vm_pop(vm);
            Value *obj = vm_pop(vm);
            if (obj && obj->type == VAL_LIST && idx && idx->type == VAL_INT) {
                int i = (int)idx->data.int_val;
                if (i >= 0 && (size_t)i < obj->data.list_val->len)
                    vm_push(vm, val_clone(obj->data.list_val->items[i]));
                else
                    vm_push(vm, mk_null_val());
            } else if (obj && obj->type == VAL_STRING && idx && idx->type == VAL_INT) {
                int i = (int)idx->data.int_val;
                if (i >= 0 && (size_t)i < strlen(obj->data.str_val)) {
                    char buf[2] = {obj->data.str_val[i], 0};
                    Value *v = malloc(sizeof(Value)); v->type = VAL_STRING; v->data.str_val = strdup(buf);
                    vm_push(vm, v);
                } else {
                    vm_push(vm, mk_null_val());
                }
            } else if (obj && obj->type == VAL_DICT && idx && idx->type == VAL_STRING) {
                Value *v = dict_get(obj->data.dict_val, idx->data.str_val);
                if (v) vm_push(vm, val_clone(v));
                else vm_push(vm, mk_null_val());
            } else {
                vm_push(vm, mk_null_val());
            }
            continue;
        }

        if (strcmp(op, "SET_ITEM") == 0) {
            Value *val = vm_pop(vm), *idx = vm_pop(vm), *obj = vm_pop(vm);
            if (obj && obj->type == VAL_DICT && idx && idx->type == VAL_STRING) {
                dict_set(obj->data.dict_val, idx->data.str_val, val);
            } else if (obj && obj->type == VAL_LIST && idx && idx->type == VAL_INT) {
                int i = (int)idx->data.int_val;
                if (i >= 0 && (size_t)i < obj->data.list_val->len)
                    obj->data.list_val->items[i] = val;
            }
            vm_push(vm, val);
            continue;
        }

        if (strcmp(op, "LOAD_ATTR") == 0) {
            Value *obj = vm_pop(vm);
            const char *attr = argv->data.str_val;
            if (obj && obj->type == VAL_INSTANCE && obj->data.instance_val->attrs) {
                Value *attrv = dict_get(obj->data.instance_val->attrs, attr);
                if (attrv) { vm_push(vm, val_clone(attrv)); continue; }
            }
            if (obj && obj->type == VAL_DICT) {
                Value *attrv = dict_get(obj->data.dict_val, attr);
                if (attrv) { vm_push(vm, val_clone(attrv)); continue; }
            }
            vm_push(vm, mk_null_val());
            continue;
        }

        if (strcmp(op, "STORE_ATTR") == 0) {
            Value *val = vm_pop(vm), *obj = vm_pop(vm);
            vm_push(vm, val);
            continue;
        }

        if (strcmp(op, "RETURN_VALUE") == 0) {
            Value *ret = vm_pop(vm);
            int saved_sp = vm->frames[fi].saved_sp;
            vm->frame_sp--;
            vm->sp = saved_sp;
            if (vm->frame_sp > 0) vm_push(vm, ret);
            else vm->ret_val = ret;
            continue;
        }

        if (strcmp(op, "CALL_VALUE") == 0) {
            int nargs = (int)argv->data.int_val;
            Value *args[64] = {0};
            for (int i = nargs - 1; i >= 0; i--) args[i] = vm_pop(vm);
            Value *fnv = vm_pop(vm);
            vm_push(vm, mk_null_val());
            continue;
        }

        if (strcmp(op, "STORE_ITER") == 0) {
            Value *iterable = vm_pop(vm);
            if (vm->iter_sp < MAX_ITER_STACK) {
                Value *state = malloc(sizeof(Value));
                state->type = VAL_LIST;
                state->data.list_val = malloc(sizeof(List));
                state->data.list_val->cap = 2;
                state->data.list_val->len = 2;
                state->data.list_val->items = malloc(sizeof(Value*) * 2);
                state->data.list_val->items[0] = iterable;
                state->data.list_val->items[1] = num_to_val(0);
                vm->iter_stack[vm->iter_sp++] = state;
            }
            continue;
        }

        if (strcmp(op, "LOAD_ITER_NEXT") == 0) {
            if (vm->iter_sp <= 0) { vm_push(vm, mk_bool_val(0)); continue; }
            Value *state = vm->iter_stack[vm->iter_sp - 1];
            Value *iterable = state->data.list_val->items[0];
            int idx = (int)state->data.list_val->items[1]->data.int_val;

            if (iterable && iterable->type == VAL_LIST) {
                if (idx >= (int)iterable->data.list_val->len) { vm_push(vm, mk_bool_val(0)); continue; }
                Value *item = iterable->data.list_val->items[idx];
                vm_set_var(vm, argv->data.str_val, val_clone(item));
                state->data.list_val->items[1]->data.int_val = idx + 1;
                vm_push(vm, mk_bool_val(1));
            } else {
                vm_push(vm, mk_bool_val(0));
            }
            continue;
        }

        if (strcmp(op, "STORE_ITER_VAL") == 0) {
            if (vm->sp > 0) vm_set_var(vm, argv->data.str_val, val_clone(vm->stack[vm->sp - 1]));
            continue;
        }

        if (strcmp(op, "POP_ITER") == 0) {
            if (vm->iter_sp > 0) vm->iter_sp--;
            continue;
        }

        if (strcmp(op, "IMPORT_FILE") == 0 || strcmp(op, "IMPORT_NAME") == 0 || strcmp(op, "CALL_SUPER") == 0) {
            vm_push(vm, mk_null_val());
            continue;
        }
    }
    return 0;
}

static void free_value(Value *v) {
    if (!v) return;
    switch (v->type) {
        case VAL_STRING: free(v->data.str_val); break;
        case VAL_LIST: {
            for (size_t i = 0; i < v->data.list_val->len; i++)
                free_value(v->data.list_val->items[i]);
            free(v->data.list_val->items);
            free(v->data.list_val);
            break;
        }
        case VAL_DICT: {
            for (size_t i = 0; i < v->data.dict_val->len; i++) {
                free(v->data.dict_val->entries[i].key);
                free_value(v->data.dict_val->entries[i].val);
            }
            free(v->data.dict_val->entries);
            free(v->data.dict_val);
            break;
        }
        default: break;
    }
    free(v);
}

/* ═══════════════════════════════════════════════════════════════
 *  DZZW HANDLE TABLE — maps integer handles to C objects
 * ═══════════════════════════════════════════════════════════════ */

#define DZZW_MAX_HANDLES 4096
static void *dzzw_handles[DZZW_MAX_HANDLES];

static int dzzw_handle_put(void *ptr) {
    for (int i = 0; i < DZZW_MAX_HANDLES; i++) {
        if (dzzw_handles[i] == NULL) {
            dzzw_handles[i] = ptr;
            return i + 1;
        }
    }
    return 0;
}

static void *dzzw_handle_get(int handle) {
    if (handle <= 0 || handle > DZZW_MAX_HANDLES) return NULL;
    return dzzw_handles[handle - 1];
}

static void *dzzw_handle_take(int handle) {
    if (handle <= 0 || handle > DZZW_MAX_HANDLES) return NULL;
    void *ptr = dzzw_handles[handle - 1];
    if (ptr) dzzw_handles[handle - 1] = NULL;
    return ptr;
}

/* ═══════════════════════════════════════════════════════════════
 *  DZZW EXECUTOR — runs H# functions in worker threads
 * ═══════════════════════════════════════════════════════════════ */

static VM *g_dzzw_main_vm = NULL;

static void dzzw_executor(Value *fn, Value **args, int argc, DZZW_Future *fut) {
    Func *f = load_func_from_json(fn);
    if (!f) {
        dzzw_future_set(fut, mk_null_val());
        return;
    }

    VM *worker = vm_create();
    worker->global_env = g_dzzw_main_vm->global_env;
    vm_call_func(worker, f, args, argc);
    worker->ret_val = NULL;
    vm_execute(worker);
    Value *result = worker->ret_val ? worker->ret_val : mk_null_val();
    dzzw_future_set(fut, result);

    free(worker);
}

/* ═══════════════════════════════════════════════════════════════
 *  DZZW BUILTINS
 * ═══════════════════════════════════════════════════════════════ */

static int dzzw_run_builtin(VM *vm, const char *fname, Value **args, int nargs, Value **result) {
    if (strcmp(fname, "dzzw_spawn") == 0) {
        if (nargs < 2 || !args[0] || args[0]->type != VAL_DICT || !args[1] || args[1]->type != VAL_LIST) {
            *result = num_to_val(0);
            return 1;
        }
        Value *fn = args[0];
        Value *arglist = args[1];
        int an = (int)arglist->data.list_val->len;
        Value **cargs = calloc(an, sizeof(Value*));
        for (int i = 0; i < an; i++) cargs[i] = val_clone(arglist->data.list_val->items[i]);
        DZZW_Future *fut = dzzw_spawn(fn, cargs, an);
        free(cargs);
        if (!fut) { *result = num_to_val(0); return 1; }
        int handle = dzzw_handle_put(fut);
        *result = num_to_val(handle);
        return 1;
    }
    if (strcmp(fname, "dzzw_await") == 0) {
        if (nargs < 1 || !args[0]) { *result = mk_null_val(); return 1; }
        int handle = (int)to_number(args[0]);
        DZZW_Future *fut = dzzw_handle_take(handle);
        if (!fut) { *result = mk_null_val(); return 1; }
        Value *r = dzzw_future_wait(fut);
        dzzw_future_free(fut);
        *result = r ? val_clone(r) : mk_null_val();
        return 1;
    }
    if (strcmp(fname, "dzzw_parallel_map") == 0) {
        if (nargs < 2 || !args[0] || args[0]->type != VAL_DICT || !args[1] || args[1]->type != VAL_LIST) {
            *result = mk_null_val();
            return 1;
        }
        Value *fn = args[0];
        Value *list = args[1];
        int n = (int)list->data.list_val->len;
        DZZW_Future **futures = calloc(n, sizeof(DZZW_Future*));
        for (int i = 0; i < n; i++) {
            Value **cargs = calloc(1, sizeof(Value*));
            cargs[0] = val_clone(list->data.list_val->items[i]);
            futures[i] = dzzw_spawn(fn, cargs, 1);
            free(cargs);
        }
        Value *results = malloc(sizeof(Value));
        results->type = VAL_LIST;
        results->data.list_val = calloc(1, sizeof(List));
        results->data.list_val->cap = n > 0 ? n : 1;
        results->data.list_val->items = calloc(results->data.list_val->cap, sizeof(Value*));
        for (int i = 0; i < n; i++) {
            if (futures[i]) {
                Value *r = dzzw_future_wait(futures[i]);
                results->data.list_val->items[results->data.list_val->len++] = r ? val_clone(r) : mk_null_val();
                dzzw_future_free(futures[i]);
            } else {
                results->data.list_val->items[results->data.list_val->len++] = mk_null_val();
            }
        }
        free(futures);
        *result = results;
        return 1;
    }
    if (strcmp(fname, "dzzw_worker_count") == 0) {
        *result = num_to_val(dzzw_worker_count());
        return 1;
    }
    if (strcmp(fname, "dzzw_pending_count") == 0) {
        *result = num_to_val(dzzw_pending_count());
        return 1;
    }
    if (strcmp(fname, "dzzw_channel_create") == 0) {
        int cap = 0;
        if (nargs >= 1) cap = (int)to_number(args[0]);
        DZZW_Channel *ch = dzzw_channel_new(cap);
        if (!ch) { *result = num_to_val(0); return 1; }
        int handle = dzzw_handle_put(ch);
        *result = num_to_val(handle);
        return 1;
    }
    if (strcmp(fname, "dzzw_channel_send") == 0) {
        if (nargs < 2 || !args[0]) { *result = mk_null_val(); return 1; }
        int handle = (int)to_number(args[0]);
        DZZW_Channel *ch = dzzw_handle_get(handle);
        if (!ch) { *result = mk_null_val(); return 1; }
        dzzw_channel_send(ch, val_clone(args[1]));
        *result = mk_null_val();
        return 1;
    }
    if (strcmp(fname, "dzzw_channel_recv") == 0) {
        if (nargs < 1 || !args[0]) { *result = mk_null_val(); return 1; }
        int handle = (int)to_number(args[0]);
        DZZW_Channel *ch = dzzw_handle_get(handle);
        if (!ch) { *result = mk_null_val(); return 1; }
        *result = dzzw_channel_recv(ch);
        return 1;
    }
    if (strcmp(fname, "dzzw_channel_free") == 0) {
        if (nargs < 1 || !args[0]) { *result = mk_null_val(); return 1; }
        int handle = (int)to_number(args[0]);
        DZZW_Channel *ch = dzzw_handle_take(handle);
        if (ch) dzzw_channel_free(ch);
        *result = mk_null_val();
        return 1;
    }
    if (strcmp(fname, "dzzw_mutex_create") == 0) {
        DZZW_Mutex *m = dzzw_mutex_new();
        if (!m) { *result = num_to_val(0); return 1; }
        int handle = dzzw_handle_put(m);
        *result = num_to_val(handle);
        return 1;
    }
    if (strcmp(fname, "dzzw_mutex_lock") == 0) {
        if (nargs < 1 || !args[0]) { *result = mk_null_val(); return 1; }
        int handle = (int)to_number(args[0]);
        DZZW_Mutex *m = dzzw_handle_get(handle);
        if (m) dzzw_mutex_lock(m);
        *result = mk_null_val();
        return 1;
    }
    if (strcmp(fname, "dzzw_mutex_unlock") == 0) {
        if (nargs < 1 || !args[0]) { *result = mk_null_val(); return 1; }
        int handle = (int)to_number(args[0]);
        DZZW_Mutex *m = dzzw_handle_get(handle);
        if (m) dzzw_mutex_unlock(m);
        *result = mk_null_val();
        return 1;
    }
    if (strcmp(fname, "dzzw_mutex_free") == 0) {
        if (nargs < 1 || !args[0]) { *result = mk_null_val(); return 1; }
        int handle = (int)to_number(args[0]);
        DZZW_Mutex *m = dzzw_handle_take(handle);
        if (m) dzzw_mutex_free(m);
        *result = mk_null_val();
        return 1;
    }
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <bytecode.json>\n", argv[0]);
        fprintf(stderr, "  H# Native Bytecode VM v0.4\n");
        return 1;
    }

    FILE *f = fopen(argv[1], "rb");
    if (!f) {
        fprintf(stderr, "Error: cannot open %s\n", argv[1]);
        return 1;
    }

    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);

    char *json = malloc(sz + 1);
    fread(json, 1, sz, f);
    json[sz] = '\0';
    fclose(f);

    /* Parse JSON bytecode */
    JParser jp; jp.s = json; jp.pos = 0;
    Value *json_bc = j_parse_value(&jp, 0);

    if (!json_bc) {
        fprintf(stderr, "Error: failed to parse bytecode JSON\n");
        free(json);
        return 1;
    }

    /* Initialize DZZW thread pool */
    dzzw_init(0);
    dzzw_set_executor(dzzw_executor);

    VM *vm = vm_create();
    g_dzzw_main_vm = vm;
    load_bytecode_from_json(vm, json_bc);
    int result = vm_execute(vm);

    dzzw_shutdown();

    free(json);
    free_value(json_bc);

    return result;
}