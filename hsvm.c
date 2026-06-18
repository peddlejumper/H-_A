/* ═══════════════════════════════════════════════════════════════
 *  H# Standalone Bytecode VM (hsvm)
 *  100% self-hosting: executes H# bytecode without Python
 * ═══════════════════════════════════════════════════════════════ */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include <time.h>
#include <ctype.h>
#include <errno.h>
#include <stdatomic.h>
#include <pthread.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <dirent.h>
#include <unistd.h>

#include "dzzw.h"

/* ═══════════════════════════════════════════════════════════════
 *  OPCODE SYSTEM (integer dispatch, no strcmp)
 * ═══════════════════════════════════════════════════════════════ */

enum Opcode {
    OP_HALT, OP_LOAD_CONST, OP_LOAD_NAME, OP_STORE_NAME, OP_PRINT, OP_POP_TOP,
    OP_MAKE_LIST, OP_MAKE_DICT, OP_GET_ITEM, OP_LOAD_ATTR, OP_STORE_ATTR, OP_SET_ITEM,
    OP_BINARY_ADD, OP_BINARY_SUB, OP_BINARY_MUL, OP_BINARY_DIV, OP_BINARY_MOD,
    OP_BINARY_BITAND, OP_BINARY_BITOR, OP_BINARY_BITXOR, OP_BINARY_LSHIFT, OP_BINARY_RSHIFT,
    OP_UNARY_NOT, OP_UNARY_TILDE, OP_COMPARE_OP,
    OP_JUMP_IF_FALSE, OP_JUMP, OP_SETUP_EXCEPT, OP_POP_EXCEPT, OP_RAISE,
    OP_RETURN_VALUE, OP_CALL_FUNCTION, OP_CALL_METHOD, OP_CALL_NEW, OP_CALL_VALUE, OP_CALL_SUPER,
    OP_INSTANCEOF, OP_DEREF, OP_CAST, OP_MAKE_MODULE, OP_ASM, OP_FOR_ITER,
    OP_CONTINUE, OP_BREAK, OP_IMPORT_NAME, OP_IMPORT_FILE,
    OP_UNKNOWN
};

static int opcode_from_str(const char *s) {
    if (!s) return OP_UNKNOWN;
    switch (s[0]) {
    case 'A': if (strcmp(s, "ASM") == 0) return OP_ASM; break;
    case 'B':
        if (s[1] == 'I') {
            if (strcmp(s+7, "ADD")==0) return OP_BINARY_ADD;
            if (strcmp(s+7, "SUB")==0) return OP_BINARY_SUB;
            if (strcmp(s+7, "MUL")==0) return OP_BINARY_MUL;
            if (strcmp(s+7, "DIV")==0) return OP_BINARY_DIV;
            if (strcmp(s+7, "MOD")==0) return OP_BINARY_MOD;
            if (strcmp(s+7, "BITAND")==0) return OP_BINARY_BITAND;
            if (strcmp(s+7, "BITOR")==0) return OP_BINARY_BITOR;
            if (strcmp(s+7, "BITXOR")==0) return OP_BINARY_BITXOR;
            if (strcmp(s+7, "LSHIFT")==0) return OP_BINARY_LSHIFT;
            if (strcmp(s+7, "RSHIFT")==0) return OP_BINARY_RSHIFT;
        }
        if (strcmp(s, "BREAK") == 0) return OP_BREAK;
        break;
    case 'C':
        if (s[1] == 'A') {
            if (strcmp(s+5, "FUNCTION")==0) return OP_CALL_FUNCTION;
            if (strcmp(s+5, "METHOD")==0) return OP_CALL_METHOD;
            if (strcmp(s+5, "NEW")==0) return OP_CALL_NEW;
            if (strcmp(s+5, "VALUE")==0) return OP_CALL_VALUE;
            if (strcmp(s+5, "SUPER")==0) return OP_CALL_SUPER;
        }
        if (strcmp(s, "CAST") == 0) return OP_CAST;
        if (strcmp(s, "COMPARE_OP") == 0) return OP_COMPARE_OP;
        if (strcmp(s, "CONTINUE") == 0) return OP_CONTINUE;
        break;
    case 'D': if (strcmp(s, "DEREF") == 0) return OP_DEREF; break;
    case 'F': if (strcmp(s, "FOR_ITER") == 0) return OP_FOR_ITER; break;
    case 'G': if (strcmp(s, "GET_ITEM") == 0) return OP_GET_ITEM; break;
    case 'H': if (strcmp(s, "HALT") == 0) return OP_HALT; break;
    case 'I':
        if (strcmp(s, "IMPORT_FILE") == 0) return OP_IMPORT_FILE;
        if (strcmp(s, "IMPORT_NAME") == 0) return OP_IMPORT_NAME;
        if (strcmp(s, "INSTANCEOF") == 0) return OP_INSTANCEOF;
        break;
    case 'J':
        if (strcmp(s, "JUMP_IF_FALSE") == 0) return OP_JUMP_IF_FALSE;
        if (strcmp(s, "JUMP") == 0) return OP_JUMP;
        break;
    case 'L':
        if (strcmp(s, "LOAD_CONST") == 0) return OP_LOAD_CONST;
        if (strcmp(s, "LOAD_NAME") == 0) return OP_LOAD_NAME;
        if (strcmp(s, "LOAD_ATTR") == 0) return OP_LOAD_ATTR;
        break;
    case 'M':
        if (strcmp(s+5, "LIST")==0) return OP_MAKE_LIST;
        if (strcmp(s+5, "DICT")==0) return OP_MAKE_DICT;
        if (strcmp(s+5, "MODULE")==0) return OP_MAKE_MODULE;
        break;
    case 'P':
        if (strcmp(s, "POP_TOP") == 0) return OP_POP_TOP;
        if (strcmp(s, "POP_EXCEPT") == 0) return OP_POP_EXCEPT;
        if (strcmp(s, "PRINT") == 0) return OP_PRINT;
        break;
    case 'R':
        if (strcmp(s, "RAISE") == 0) return OP_RAISE;
        if (strcmp(s, "RETURN_VALUE") == 0) return OP_RETURN_VALUE;
        break;
    case 'S':
        if (strcmp(s, "SETUP_EXCEPT") == 0) return OP_SETUP_EXCEPT;
        if (strcmp(s, "SET_ITEM") == 0) return OP_SET_ITEM;
        if (strcmp(s, "STORE_NAME") == 0) return OP_STORE_NAME;
        if (strcmp(s, "STORE_ATTR") == 0) return OP_STORE_ATTR;
        break;
    case 'U':
        if (strcmp(s+6, "NOT")==0) return OP_UNARY_NOT;
        if (strcmp(s+6, "TILDE")==0) return OP_UNARY_TILDE;
        break;
    }
    return OP_UNKNOWN;
}

/* ═══════════════════════════════════════════════════════════════
 *  VALUE SYSTEM
 * ═══════════════════════════════════════════════════════════════ */

typedef enum {
    V_NIL, V_INT, V_FLOAT, V_BOOL, V_STR,
    V_LIST, V_DICT, V_FUNC, V_CLASS, V_INST, V_BUILTIN
} ValType;

typedef struct Value Value;
typedef struct EnvNode EnvNode;

struct Value {
    ValType type;
    int _Atomic refcount;
    union {
        int64_t ival;
        double fval;
        bool bval;
        char *sval;
        struct { Value **items; int len; int cap; } list;
        struct { Value **keys; Value **vals; int len; int cap; } dict;
        struct {
            char **args; int argc;
            struct Instr { char *op; Value *arg; int opcode; } *instrs; int icount;
            Value **consts; int ccount;
            EnvNode *env;
            bool is_coro;
        } func;
        struct {
            char *name;
            EnvNode *methods;
            EnvNode *fields;
            char **privates; int pcount;
            Value *base;
        } cls;
        struct {
            Value *klass;
            EnvNode *fields;
        } instance;
        struct {
            char *name;
            Value *(*fn)(Value **args, int argc);
        } builtin;
    };
    Value *next;
};

/* ═══════════════════════════════════════════════════════════════
 *  ENVIRONMENT (linked list of name→value bindings)
 * ═══════════════════════════════════════════════════════════════ */

struct EnvNode {
    char *name;
    Value *value;
    EnvNode *next;
    EnvNode *parent;
};

static EnvNode *env_new(EnvNode *parent) {
    EnvNode *e = calloc(1, sizeof(EnvNode));
    e->parent = parent;
    return e;
}

static void env_put(EnvNode *env, const char *name, Value *val) {
    EnvNode *n = env;
    while (n->next) {
        if (strcmp(n->name, name) == 0) { n->value = val; return; }
        n = n->next;
    }
    if (n->name) {
        if (strcmp(n->name, name) == 0) { n->value = val; return; }
        n->next = calloc(1, sizeof(EnvNode));
        n = n->next;
    }
    n->name = strdup(name);
    n->value = val;
    n->parent = env->parent;
}

static Value *env_get(EnvNode *env, const char *name) {
    EnvNode *e = env;
    while (e) {
        EnvNode *n = e;
        while (n) {
            if (n->name && strcmp(n->name, name) == 0) return n->value;
            n = n->next;
        }
        e = e->parent;
    }
    return NULL;
}

static bool env_has(EnvNode *env, const char *name) {
    return env_get(env, name) != NULL;
}

/* ═══════════════════════════════════════════════════════════════
 *  VALUE CREATION / DESTRUCTION
 * ═══════════════════════════════════════════════════════════════ */

static Value *val_new(ValType type) {
    Value *v = calloc(1, sizeof(Value));
    v->type = type;
    v->refcount = 1;
    return v;
}

static Value *val_nil(void) { return val_new(V_NIL); }
static Value *val_int(int64_t i) { Value *v = val_new(V_INT); v->ival = i; return v; }
static Value *val_float(double f) { Value *v = val_new(V_FLOAT); v->fval = f; return v; }
static Value *val_bool(bool b) { Value *v = val_new(V_BOOL); v->bval = b; return v; }
static Value *val_str(const char *s) { Value *v = val_new(V_STR); v->sval = strdup(s ? s : ""); return v; }
static Value *val_strn(const char *s, size_t n) { Value *v = val_new(V_STR); v->sval = strndup(s, n); return v; }
static const char *val_type_name(ValType t) {
    switch (t) {
    case V_NIL: return "nil"; case V_INT: return "int"; case V_FLOAT: return "float";
    case V_BOOL: return "bool"; case V_STR: return "str"; case V_LIST: return "list";
    case V_DICT: return "dict"; case V_FUNC: return "func"; case V_CLASS: return "class";
    case V_INST: return "inst"; case V_BUILTIN: return "builtin"; default: return "unknown";
    }
}
static int64_t val_as_int(Value *v) {
    if (v->type == V_INT) return v->ival;
    if (v->type == V_BOOL) return v->bval ? 1 : 0;
    return 0;
}
static double val_as_double(Value *v) {
    if (v->type == V_INT) return (double)v->ival;
    if (v->type == V_FLOAT) return v->fval;
    if (v->type == V_BOOL) return v->bval ? 1.0 : 0.0;
    return 0.0;
}
static bool val_is_number(Value *v) { return v->type == V_INT || v->type == V_FLOAT || v->type == V_BOOL; }

static Value *val_list(int cap) {
    Value *v = val_new(V_LIST);
    v->list.cap = cap < 8 ? 8 : cap;
    v->list.items = calloc(v->list.cap, sizeof(Value*));
    v->list.len = 0;
    return v;
}

static Value *val_dict(int cap) {
    Value *v = val_new(V_DICT);
    v->dict.cap = cap < 8 ? 8 : cap;
    v->dict.keys = calloc(v->dict.cap, sizeof(Value*));
    v->dict.vals = calloc(v->dict.cap, sizeof(Value*));
    v->dict.len = 0;
    return v;
}

static Value *val_builtin(const char *name, Value *(*fn)(Value**, int)) {
    Value *v = val_new(V_BUILTIN);
    v->builtin.name = strdup(name);
    v->builtin.fn = fn;
    return v;
}

static void val_free(Value *v);

static Value *val_decref(Value *v) {
    if (v && atomic_fetch_sub(&v->refcount, 1) <= 1) { val_free(v); return NULL; }
    return v;
}

static Value *val_incref(Value *v) {
    if (v) atomic_fetch_add(&v->refcount, 1);
    return v;
}

static void val_free(Value *v) {
    if (!v) return;
    switch (v->type) {
    case V_STR: free(v->sval); break;
    case V_LIST:
        for (int i = 0; i < v->list.len; i++) val_decref(v->list.items[i]);
        free(v->list.items);
        break;
    case V_DICT:
        for (int i = 0; i < v->dict.len; i++) { val_decref(v->dict.keys[i]); val_decref(v->dict.vals[i]); }
        free(v->dict.keys); free(v->dict.vals);
        break;
    case V_FUNC:
        if (v->func.args) { for (int i = 0; i < v->func.argc; i++) free(v->func.args[i]); free(v->func.args); }
        if (v->func.instrs) { for (int i = 0; i < v->func.icount; i++) { free(v->func.instrs[i].op); val_decref(v->func.instrs[i].arg); } free(v->func.instrs); }
        if (v->func.consts) { for (int i = 0; i < v->func.ccount; i++) val_decref(v->func.consts[i]); free(v->func.consts); }
        break;
    case V_CLASS:
        free(v->cls.name);
        if (v->cls.privates) { for (int i = 0; i < v->cls.pcount; i++) free(v->cls.privates[i]); free(v->cls.privates); }
        val_decref(v->cls.base);
        break;
    case V_INST:
        val_decref(v->instance.klass);
        break;
    case V_BUILTIN: free(v->builtin.name); break;
    default: break;
    }
    free(v);
}

/* ═══════════════════════════════════════════════════════════════
 *  DICT/ENV OPERATIONS
 * ═══════════════════════════════════════════════════════════════ */

static int dict_find(Value *dict, Value *key) {
    for (int i = 0; i < dict->dict.len; i++) {
        Value *k = dict->dict.keys[i];
        if (k->type == V_STR && key->type == V_STR && strcmp(k->sval, key->sval) == 0) return i;
        if (k->type == V_INT && key->type == V_INT && k->ival == key->ival) return i;
        if (k->type == V_STR && key->type == V_INT) {
            char buf[32]; snprintf(buf, sizeof(buf), "%lld", (long long)key->ival);
            if (strcmp(k->sval, buf) == 0) return i;
        }
    }
    return -1;
}

static void dict_set(Value *dict, Value *key, Value *val) {
    int idx = dict_find(dict, key);
    if (idx >= 0) {
        val_decref(dict->dict.keys[idx]);
        val_decref(dict->dict.vals[idx]);
        dict->dict.keys[idx] = val_incref(key);
        dict->dict.vals[idx] = val_incref(val);
        return;
    }
    if (dict->dict.len >= dict->dict.cap) {
        int nc = dict->dict.cap * 2;
        dict->dict.keys = realloc(dict->dict.keys, nc * sizeof(Value*));
        dict->dict.vals = realloc(dict->dict.vals, nc * sizeof(Value*));
        memset(dict->dict.keys + dict->dict.cap, 0, (nc - dict->dict.cap) * sizeof(Value*));
        memset(dict->dict.vals + dict->dict.cap, 0, (nc - dict->dict.cap) * sizeof(Value*));
        dict->dict.cap = nc;
    }
    dict->dict.keys[dict->dict.len] = val_incref(key);
    dict->dict.vals[dict->dict.len] = val_incref(val);
    dict->dict.len++;
}

static Value *dict_get(Value *dict, Value *key) {
    int idx = dict_find(dict, key);
    return idx >= 0 ? dict->dict.vals[idx] : NULL;
}

static bool dict_has(Value *dict, Value *key) {
    return dict_find(dict, key) >= 0;
}

static void dict_del(Value *dict, Value *key) {
    int idx = dict_find(dict, key);
    if (idx < 0) return;
    val_decref(dict->dict.keys[idx]);
    val_decref(dict->dict.vals[idx]);
    for (int i = idx; i < dict->dict.len - 1; i++) {
        dict->dict.keys[i] = dict->dict.keys[i+1];
        dict->dict.vals[i] = dict->dict.vals[i+1];
    }
    dict->dict.len--;
}

static void dict_merge(EnvNode *env, Value *dict) {
    for (int i = 0; i < dict->dict.len; i++) {
        Value *k = dict->dict.keys[i];
        if (k->type == V_STR) env_put(env, k->sval, dict->dict.vals[i]);
    }
}

/* ═══════════════════════════════════════════════════════════════
 *  LIST OPERATIONS
 * ═══════════════════════════════════════════════════════════════ */

static void list_push(Value *list, Value *val) {
    if (list->list.len >= list->list.cap) {
        list->list.cap *= 2;
        list->list.items = realloc(list->list.items, list->list.cap * sizeof(Value*));
    }
    list->list.items[list->list.len++] = val_incref(val);
}

/* ═══════════════════════════════════════════════════════════════
 *  JSON PARSER (minimal, for bytecode bundle)
 * ═══════════════════════════════════════════════════════════════ */

typedef struct {
    char *data;
    int pos;
    int len;
} JP;

static void jp_skip(JP *jp) {
    while (jp->pos < jp->len && isspace((unsigned char)jp->data[jp->pos])) jp->pos++;
}

static char jp_peek(JP *jp) {
    jp_skip(jp);
    return jp->pos < jp->len ? jp->data[jp->pos] : 0;
}

static char jp_next(JP *jp) {
    jp_skip(jp);
    return jp->pos < jp->len ? jp->data[jp->pos++] : 0;
}

static Value *jp_parse(JP *jp);

static Value *jp_parse_str(JP *jp) {
    jp->pos++;
    int start = jp->pos;
    while (jp->pos < jp->len && jp->data[jp->pos] != '"') {
        if (jp->data[jp->pos] == '\\') jp->pos++;
        jp->pos++;
    }
    int end = jp->pos;
    jp->pos++;
    
    char *buf = calloc(end - start + 1, 1);
    int w = 0;
    for (int i = start; i < end; i++) {
        if (jp->data[i] == '\\' && i + 1 < end) {
            i++;
            switch (jp->data[i]) {
                case 'n': buf[w++] = '\n'; break;
                case 't': buf[w++] = '\t'; break;
                case 'r': buf[w++] = '\r'; break;
                case '"': buf[w++] = '"'; break;
                case '\\': buf[w++] = '\\'; break;
                default: buf[w++] = jp->data[i]; break;
            }
        } else {
            buf[w++] = jp->data[i];
        }
    }
    buf[w] = 0;
    Value *v = val_new(V_STR);
    v->sval = buf;
    return v;
}

static Value *jp_parse_num(JP *jp) {
    int start = jp->pos;
    bool is_float = false;
    while (jp->pos < jp->len && (isdigit((unsigned char)jp->data[jp->pos]) || jp->data[jp->pos] == '.' || jp->data[jp->pos] == '-')) {
        if (jp->data[jp->pos] == '.') is_float = true;
        jp->pos++;
    }
    if (jp->pos < jp->len && (jp->data[jp->pos] == 'e' || jp->data[jp->pos] == 'E')) {
        is_float = true;
        jp->pos++;
        if (jp->pos < jp->len && (jp->data[jp->pos] == '+' || jp->data[jp->pos] == '-')) jp->pos++;
        while (jp->pos < jp->len && isdigit((unsigned char)jp->data[jp->pos])) jp->pos++;
    }
    char *buf = strndup(jp->data + start, jp->pos - start);
    if (is_float) {
        double f = strtod(buf, NULL);
        free(buf);
        Value *v = val_new(V_FLOAT); v->fval = f; return v;
    } else {
        int64_t i = strtoll(buf, NULL, 10);
        free(buf);
        Value *v = val_new(V_INT); v->ival = i; return v;
    }
}

static Value *jp_parse_kw(JP *jp) {
    if (strncmp(jp->data + jp->pos, "true", 4) == 0) { jp->pos += 4; return val_bool(true); }
    if (strncmp(jp->data + jp->pos, "false", 5) == 0) { jp->pos += 5; return val_bool(false); }
    if (strncmp(jp->data + jp->pos, "null", 4) == 0) { jp->pos += 4; return val_nil(); }
    return NULL;
}

static Value *jp_parse_arr(JP *jp) {
    jp->pos++;
    Value *arr = val_list(8);
    while (1) {
        char c = jp_peek(jp);
        if (c == ']') { jp->pos++; break; }
        if (c == 0) break;
        list_push(arr, jp_parse(jp));
        if (jp_peek(jp) == ',') jp->pos++;
    }
    return arr;
}

static Value *jp_parse_obj(JP *jp) {
    jp->pos++;
    Value *dict = val_dict(8);
    while (1) {
        char c = jp_peek(jp);
        if (c == '}') { jp->pos++; break; }
        if (c == 0) break;
        Value *key = jp_parse(jp);
        jp_skip(jp);
        if (jp_peek(jp) == ':') jp->pos++;
        Value *val = jp_parse(jp);
        dict_set(dict, key, val);
        val_decref(key); val_decref(val);
        if (jp_peek(jp) == ',') jp->pos++;
    }
    return dict;
}

static Value *jp_parse(JP *jp) {
    jp_skip(jp);
    char c = jp_peek(jp);
    if (c == '"') return jp_parse_str(jp);
    if (c == '-' || isdigit((unsigned char)c)) return jp_parse_num(jp);
    if (c == 't' || c == 'f' || c == 'n') {
        Value *v = jp_parse_kw(jp);
        if (v) return v;
    }
    if (c == '[') return jp_parse_arr(jp);
    if (c == '{') return jp_parse_obj(jp);
    fprintf(stderr, "JSON parse error at pos %d: '%c' (context: %.40s)\n", jp->pos, c, jp->data + jp->pos);
    return val_nil();
}

static char *read_entire_file(const char *path, size_t *out_len) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *buf = malloc(sz + 1);
    size_t r = fread(buf, 1, sz, f);
    fclose(f);
    buf[r] = 0;
    if (out_len) *out_len = r;
    return buf;
}

/* ═══════════════════════════════════════════════════════════════
 *  BYTECODE INSTRUCTION PARSING
 * ═══════════════════════════════════════════════════════════════ */

static Value *parse_bc_instr(Value *instr_arr) {
    if (!instr_arr || instr_arr->type != V_LIST || instr_arr->list.len < 2) return NULL;
    Value *instr = val_new(V_FUNC);
    instr->func.icount = instr_arr->list.len;
    instr->func.instrs = calloc(instr->func.icount, sizeof(struct Instr));
    
    for (int i = 0; i < instr->func.icount; i++) {
        Value *entry = instr_arr->list.items[i];
        if (!entry || entry->type != V_LIST || entry->list.len < 2) continue;
        Value *op_v = entry->list.items[0];
        Value *arg_v = entry->list.items[1];
        if (op_v && op_v->type == V_STR) {
            instr->func.instrs[i].op = strdup(op_v->sval);
            instr->func.instrs[i].opcode = opcode_from_str(op_v->sval);
        }
        else {
            instr->func.instrs[i].op = strdup("NOP");
            instr->func.instrs[i].opcode = OP_UNKNOWN;
        }
        if (arg_v && arg_v->type != V_NIL) {
            instr->func.instrs[i].arg = val_incref(arg_v);
        }
    }
    return instr;
}

static Value *parse_bc_consts(Value *consts_arr) {
    if (!consts_arr || consts_arr->type != V_LIST) return NULL;
    Value *consts = val_list(consts_arr->list.len);
    for (int i = 0; i < consts_arr->list.len; i++) {
        Value *c = consts_arr->list.items[i];
        if (c && c->type == V_DICT) {
            Value *args = dict_get(c, val_str("args"));
            Value *instrs_v = dict_get(c, val_str("bytecode"));
            Value *consts_v = dict_get(c, val_str("consts"));
            Value *freevars_v = dict_get(c, val_str("freevars"));
            
            Value *func = val_new(V_FUNC);
            if (args && args->type == V_LIST) {
                func->func.argc = args->list.len;
                func->func.args = calloc(args->list.len, sizeof(char*));
                for (int j = 0; j < args->list.len; j++) {
                    Value *a = args->list.items[j];
                    func->func.args[j] = (a && a->type == V_STR) ? strdup(a->sval) : strdup("");
                }
            }
            if (instrs_v) {
                Value *parsed = parse_bc_instr(instrs_v);
                if (parsed) {
                    func->func.icount = parsed->func.icount;
                    func->func.instrs = parsed->func.instrs;
                    parsed->func.instrs = NULL; parsed->func.icount = 0;
                    val_decref(parsed);
                }
            }
            if (consts_v) {
                Value *parsed = parse_bc_consts(consts_v);
                if (parsed) {
                    func->func.ccount = parsed->list.len;
                    func->func.consts = calloc(func->func.ccount, sizeof(Value*));
                    for (int j = 0; j < func->func.ccount; j++)
                        func->func.consts[j] = val_incref(parsed->list.items[j]);
                    val_decref(parsed);
                }
            }
            
            Value *is_coro = dict_get(c, val_str("is_coro"));
            if (is_coro && is_coro->type == V_BOOL && is_coro->bval)
                func->func.is_coro = true;
            
            list_push(consts, func);
            val_decref(func);
        } else if (c) {
            list_push(consts, val_incref(c));
        } else {
            list_push(consts, val_nil());
        }
    }
    return consts;
}

/* ═══════════════════════════════════════════════════════════════
 *  CLASS CONSTRUCTION
 * ═══════════════════════════════════════════════════════════════ */

static Value *inst_get(Value *inst, const char *name) {
    if (!inst || inst->type != V_INST) return NULL;
    Value *klass = inst->instance.klass;
    EnvNode *n = inst->instance.fields;
    while (n) { if (n->name && strcmp(n->name, name) == 0) return n->value; n = n->next; }
    n = klass ? klass->cls.fields : NULL;
    while (n) { if (n->name && strcmp(n->name, name) == 0) return n->value; n = n->next; }
    return NULL;
}

static Value *inst_method(Value *inst, const char *name) {
    if (!inst || inst->type != V_INST) return NULL;
    Value *klass = inst->instance.klass;
    EnvNode *n = klass ? klass->cls.methods : NULL;
    while (n) { if (n->name && strcmp(n->name, name) == 0) return n->value; n = n->next; }
    return NULL;
}

/* ═══════════════════════════════════════════════════════════════
 *  BUILTIN FUNCTIONS
 * ═══════════════════════════════════════════════════════════════ */

static Value *builtin_len(Value **args, int argc) {
    if (argc != 1) { fprintf(stderr, "len() takes 1 arg\n"); return val_nil(); }
    Value *v = args[0];
    if (v->type == V_LIST) return val_int(v->list.len);
    if (v->type == V_STR) return val_int(strlen(v->sval));
    if (v->type == V_DICT) return val_int(v->dict.len);
    return val_int(0);
}

static Value *builtin_push(Value **args, int argc) {
    if (argc != 2 || args[0]->type != V_LIST) { fprintf(stderr, "push(arr, val)\n"); return val_nil(); }
    list_push(args[0], args[1]);
    return val_nil();
}

static Value *builtin_pop(Value **args, int argc) {
    if (argc != 1 || args[0]->type != V_LIST || args[0]->list.len == 0) { fprintf(stderr, "pop(arr)\n"); return val_nil(); }
    Value *v = args[0]->list.items[--args[0]->list.len];
    val_incref(v);
    val_decref(args[0]->list.items[args[0]->list.len]);
    args[0]->list.items[args[0]->list.len] = NULL;
    return v;
}

static Value *builtin_read_file(Value **args, int argc) {
    if (argc != 1 || args[0]->type != V_STR) { fprintf(stderr, "read_file(path)\n"); return val_nil(); }
    size_t len;
    char *content = read_entire_file(args[0]->sval, &len);
    if (!content) return val_nil();
    Value *v = val_str(content);
    free(content);
    return v;
}

static Value *builtin_write_file(Value **args, int argc) {
    if (argc != 2 || args[0]->type != V_STR || args[1]->type != V_STR) { fprintf(stderr, "write_file(path, content)\n"); return val_nil(); }
    FILE *f = fopen(args[0]->sval, "w");
    if (!f) return val_nil();
    fputs(args[1]->sval, f);
    fclose(f);
    return val_nil();
}

static Value *builtin_typeof(Value **args, int argc) {
    if (argc != 1 || !args[0]) return val_str("nil");
    return val_str(val_type_name(args[0]->type));
}

static Value *builtin_time_now(Value **args, int argc) {
    return val_float((double)time(NULL));
}

static Value *builtin_substring(Value **args, int argc) {
    if (argc < 2 || argc > 3) { fprintf(stderr, "substring(s, start, [end])\n"); return val_nil(); }
    if (args[0]->type != V_STR) return val_nil();
    char *s = args[0]->sval;
    int slen = strlen(s);
    int start = args[1]->type == V_INT ? (int)args[1]->ival : 0;
    int end = argc == 3 && args[2]->type == V_INT ? (int)args[2]->ival : slen;
    if (start < 0) start = 0;
    if (end > slen) end = slen;
    if (end < start) { start = end = 0; }
    return val_strn(s + start, end - start);
}

static Value *builtin_ord(Value **args, int argc) {
    if (argc != 1 || args[0]->type != V_STR || strlen(args[0]->sval) == 0) return val_int(0);
    return val_int((unsigned char)args[0]->sval[0]);
}

static Value *builtin_chr(Value **args, int argc) {
    if (argc != 1 || args[0]->type != V_INT) return val_str("");
    char buf[2] = {(char)args[0]->ival, 0};
    return val_str(buf);
}

static Value *builtin_int_cast(Value **args, int argc) {
    if (argc != 1) return val_int(0);
    if (args[0]->type == V_INT) return val_int(args[0]->ival);
    if (args[0]->type == V_FLOAT) return val_int((int64_t)args[0]->fval);
    if (args[0]->type == V_STR) return val_int(atoll(args[0]->sval));
    if (args[0]->type == V_BOOL) return val_int(args[0]->bval ? 1 : 0);
    return val_int(0);
}

static Value *builtin_str_cast(Value **args, int argc) {
    if (argc != 1) return val_str("");
    if (args[0]->type == V_STR) return val_incref(args[0]);
    if (args[0]->type == V_INT) { char buf[32]; snprintf(buf, sizeof(buf), "%lld", (long long)args[0]->ival); return val_str(buf); }
    if (args[0]->type == V_FLOAT) { char buf[64]; snprintf(buf, sizeof(buf), "%g", args[0]->fval); return val_str(buf); }
    if (args[0]->type == V_BOOL) return val_str(args[0]->bval ? "true" : "false");
    return val_str("null");
}

static Value *builtin_date_now(Value **args, int argc) {
    time_t t = time(NULL);
    struct tm *tm = localtime(&t);
    char buf[32];
    snprintf(buf, sizeof(buf), "%04d-%02d-%02d", tm->tm_year + 1900, tm->tm_mon + 1, tm->tm_mday);
    return val_str(buf);
}

static Value *builtin_date_timestamp(Value **args, int argc) {
    time_t t = time(NULL);
    return val_int((int64_t)t);
}

static Value *builtin_date_format(Value **args, int argc) {
    if (argc < 1 || args[0]->type != V_STR) return val_str("");
    time_t t = time(NULL);
    struct tm *tm = localtime(&t);
    char buf[128];
    strftime(buf, sizeof(buf), args[0]->sval, tm);
    return val_str(buf);
}

static Value *builtin_date_parse(Value **args, int argc) {
    if (argc < 1 || args[0]->type != V_STR) return val_int(0);
    struct tm tm = {0};
    if (sscanf(args[0]->sval, "%d-%d-%d", &tm.tm_year, &tm.tm_mon, &tm.tm_mday) == 3) {
        tm.tm_year -= 1900; tm.tm_mon -= 1;
        return val_int((int64_t)mktime(&tm));
    }
    return val_int(0);
}

/* File system builtins */
static Value *builtin_fs_exists(Value **args, int argc) {
    if (argc != 1 || args[0]->type != V_STR) return val_bool(false);
    return val_bool(access(args[0]->sval, F_OK) == 0);
}
static Value *builtin_fs_is_file(Value **args, int argc) {
    if (argc != 1 || args[0]->type != V_STR) return val_bool(false);
    struct stat st;
    return val_bool(stat(args[0]->sval, &st) == 0 && S_ISREG(st.st_mode));
}
static Value *builtin_fs_is_dir(Value **args, int argc) {
    if (argc != 1 || args[0]->type != V_STR) return val_bool(false);
    struct stat st;
    return val_bool(stat(args[0]->sval, &st) == 0 && S_ISDIR(st.st_mode));
}
static Value *builtin_fs_mkdir(Value **args, int argc) {
    if (argc != 1 || args[0]->type != V_STR) return val_nil();
    mkdir(args[0]->sval, 0755);
    return val_nil();
}
static Value *builtin_fs_remove(Value **args, int argc) {
    if (argc != 1 || args[0]->type != V_STR) return val_nil();
    remove(args[0]->sval);
    return val_nil();
}
static Value *builtin_fs_list_dir(Value **args, int argc) {
    Value *arr = val_list(16);
    const char *path = (argc >= 1 && args[0]->type == V_STR) ? args[0]->sval : ".";
    DIR *d = opendir(path);
    if (!d) return arr;
    struct dirent *ent;
    while ((ent = readdir(d))) {
        if (strcmp(ent->d_name, ".") == 0 || strcmp(ent->d_name, "..") == 0) continue;
        list_push(arr, val_str(ent->d_name));
    }
    closedir(d);
    return arr;
}
static Value *builtin_fs_get_cwd(Value **args, int argc) {
    char buf[4096];
    return val_str(getcwd(buf, sizeof(buf)) ? buf : "");
}
static Value *builtin_fs_chdir(Value **args, int argc) {
    if (argc != 1 || args[0]->type != V_STR) return val_nil();
    chdir(args[0]->sval);
    return val_nil();
}
static Value *builtin_fs_join_path(Value **args, int argc) {
    if (argc < 2 || args[0]->type != V_STR || args[1]->type != V_STR) return val_str("");
    char buf[8192];
    int len = snprintf(buf, sizeof(buf), "%s/%s", args[0]->sval, args[1]->sval);
    for (int i = 2; i < argc; i++) {
        if (args[i]->type == V_STR) len += snprintf(buf + len, sizeof(buf) - len, "/%s", args[i]->sval);
    }
    return val_str(buf);
}
static Value *builtin_fs_get_ext(Value **args, int argc) {
    if (argc != 1 || args[0]->type != V_STR) return val_str("");
    char *dot = strrchr(args[0]->sval, '.');
    return dot ? val_str(dot) : val_str("");
}
static Value *builtin_fs_get_basename(Value **args, int argc) {
    if (argc != 1 || args[0]->type != V_STR) return val_str("");
    char *slash = strrchr(args[0]->sval, '/');
    return val_str(slash ? slash + 1 : args[0]->sval);
}
static Value *builtin_fs_get_dirname(Value **args, int argc) {
    if (argc != 1 || args[0]->type != V_STR) return val_str("");
    char *slash = strrchr(args[0]->sval, '/');
    if (!slash) return val_str(".");
    return val_strn(args[0]->sval, slash - args[0]->sval);
}

/* IO builtins */
static Value *builtin_io_append_file(Value **args, int argc) {
    if (argc != 2 || args[0]->type != V_STR || args[1]->type != V_STR) return val_nil();
    FILE *f = fopen(args[0]->sval, "a");
    if (!f) return val_nil();
    fputs(args[1]->sval, f);
    fclose(f);
    return val_nil();
}
static Value *builtin_io_read_lines(Value **args, int argc) {
    if (argc != 1 || args[0]->type != V_STR) return val_list(8);
    FILE *f = fopen(args[0]->sval, "r");
    if (!f) return val_list(8);
    char line[65536];
    Value *arr = val_list(16);
    while (fgets(line, sizeof(line), f)) {
        size_t len = strlen(line);
        if (len > 0 && line[len-1] == '\n') line[len-1] = 0;
        list_push(arr, val_str(line));
    }
    fclose(f);
    return arr;
}
static Value *builtin_io_write_lines(Value **args, int argc) {
    if (argc != 2 || args[0]->type != V_STR || args[1]->type != V_LIST) return val_nil();
    FILE *f = fopen(args[0]->sval, "w");
    if (!f) return val_nil();
    for (int i = 0; i < args[1]->list.len; i++) {
        Value *v = args[1]->list.items[i];
        if (v && v->type == V_STR) fputs(v->sval, f);
    }
    fclose(f);
    return val_nil();
}

/* JSON builtins */
static void json_serialize_recur(Value *v, char **buf, int *cap, int *len);

static void json_ensure_cap(char **buf, int *cap, int *len, int need) {
    while (*len + need >= *cap) { *cap *= 2; *buf = realloc(*buf, *cap); }
}

static void json_serialize_recur(Value *v, char **buf, int *cap, int *len) {
    if (!v) { json_ensure_cap(buf, cap, len, 5); (*len) += sprintf(*buf + *len, "null"); return; }
    switch (v->type) {
    case V_NIL: json_ensure_cap(buf, cap, len, 5); (*len) += sprintf(*buf + *len, "null"); return;
    case V_BOOL: json_ensure_cap(buf, cap, len, 6); (*len) += sprintf(*buf + *len, v->bval ? "true" : "false"); return;
    case V_INT: json_ensure_cap(buf, cap, len, 32); (*len) += sprintf(*buf + *len, "%lld", (long long)v->ival); return;
    case V_FLOAT: json_ensure_cap(buf, cap, len, 64); (*len) += sprintf(*buf + *len, "%.17g", v->fval); return;
    case V_STR: {
        json_ensure_cap(buf, cap, len, strlen(v->sval) * 2 + 3);
        (*len) += sprintf(*buf + *len, "\"");
        for (char *s = v->sval; *s; s++) {
            if (*s == '"' || *s == '\\') { json_ensure_cap(buf, cap, len, 3); (*len) += sprintf(*buf + *len, "\\%c", *s); }
            else if (*s == '\n') { json_ensure_cap(buf, cap, len, 3); (*len) += sprintf(*buf + *len, "\\n"); }
            else { json_ensure_cap(buf, cap, len, 2); (*buf)[(*len)++] = *s; }
        }
        json_ensure_cap(buf, cap, len, 2); (*len) += sprintf(*buf + *len, "\"");
        return;
    }
    case V_LIST: {
        json_ensure_cap(buf, cap, len, 2); (*len) += sprintf(*buf + *len, "[");
        for (int i = 0; i < v->list.len; i++) {
            if (i > 0) { json_ensure_cap(buf, cap, len, 2); (*len) += sprintf(*buf + *len, ","); }
            json_serialize_recur(v->list.items[i], buf, cap, len);
        }
        json_ensure_cap(buf, cap, len, 2); (*len) += sprintf(*buf + *len, "]");
        return;
    }
    case V_DICT: {
        json_ensure_cap(buf, cap, len, 2); (*len) += sprintf(*buf + *len, "{");
        for (int i = 0; i < v->dict.len; i++) {
            if (i > 0) { json_ensure_cap(buf, cap, len, 2); (*len) += sprintf(*buf + *len, ","); }
            json_serialize_recur(v->dict.keys[i], buf, cap, len);
            json_ensure_cap(buf, cap, len, 2); (*len) += sprintf(*buf + *len, ":");
            json_serialize_recur(v->dict.vals[i], buf, cap, len);
        }
        json_ensure_cap(buf, cap, len, 2); (*len) += sprintf(*buf + *len, "}");
        return;
    }
    default: json_ensure_cap(buf, cap, len, 3); (*len) += sprintf(*buf + *len, "{}"); return;
    }
}

static Value *builtin_json_stringify(Value **args, int argc) {
    if (argc != 1) return val_str("null");
    int cap = 256, len = 0;
    char *buf = calloc(cap, 1);
    json_serialize_recur(args[0], &buf, &cap, &len);
    Value *v = val_str(buf);
    free(buf);
    return v;
}

static Value *builtin_json_parse(Value **args, int argc) {
    if (argc != 1 || args[0]->type != V_STR) return val_nil();
    JP jp = { .data = args[0]->sval, .pos = 0, .len = (int)strlen(args[0]->sval) };
    return jp_parse(&jp);
}

/* Hash table builtins */
static Value *builtin_htable_create(Value **args, int argc) { return val_dict(16); }
static Value *builtin_htable_set(Value **args, int argc) {
    if (argc < 3 || args[0]->type != V_DICT) return val_nil();
    dict_set(args[0], args[1], args[2]);
    return val_incref(args[0]);
}
static Value *builtin_htable_get(Value **args, int argc) {
    if (argc < 2 || args[0]->type != V_DICT) return val_nil();
    Value *v = dict_get(args[0], args[1]);
    return v ? val_incref(v) : val_nil();
}
static Value *builtin_htable_has(Value **args, int argc) {
    if (argc < 2 || args[0]->type != V_DICT) return val_bool(false);
    return val_bool(dict_has(args[0], args[1]));
}
static Value *builtin_htable_delete(Value **args, int argc) {
    if (argc < 2 || args[0]->type != V_DICT) return val_bool(false);
    bool had = dict_has(args[0], args[1]);
    if (had) dict_del(args[0], args[1]);
    return val_bool(had);
}
static Value *builtin_htable_size(Value **args, int argc) {
    if (argc < 1 || args[0]->type != V_DICT) return val_int(0);
    return val_int(args[0]->dict.len);
}
static Value *builtin_htable_keys(Value **args, int argc) {
    Value *arr = val_list(16);
    if (argc < 1 || args[0]->type != V_DICT) return arr;
    for (int i = 0; i < args[0]->dict.len; i++) list_push(arr, val_incref(args[0]->dict.keys[i]));
    return arr;
}
static Value *builtin_htable_values(Value **args, int argc) {
    Value *arr = val_list(16);
    if (argc < 1 || args[0]->type != V_DICT) return arr;
    for (int i = 0; i < args[0]->dict.len; i++) list_push(arr, val_incref(args[0]->dict.vals[i]));
    return arr;
}

/* Network/database stubs */
static Value *builtin_stub(Value **args, int argc) { return val_nil(); }
static Value *builtin_net_http_get(Value **args, int argc) {
    char cmd[65536];
    if (argc < 1 || args[0]->type != V_STR) return val_str("[]");
    snprintf(cmd, sizeof(cmd), "curl -s '%s' 2>/dev/null", args[0]->sval);
    FILE *fp = popen(cmd, "r");
    if (!fp) return val_str("[]");
    char buf[65536] = {0};
    size_t len = fread(buf, 1, sizeof(buf) - 1, fp);
    pclose(fp);
    buf[len] = 0;
    Value *arr = val_list(8);
    Value *resp = val_dict(4);
    dict_set(resp, val_str("status"), val_int(200));
    dict_set(resp, val_str("body"), val_str(buf));
    list_push(arr, resp);
    return arr;
}
static Value *builtin_net_http_post(Value **args, int argc) { return builtin_net_http_get(args, argc); }
static Value *builtin_net_url_parse(Value **args, int argc) {
    Value *d = val_dict(4);
    if (argc < 1 || args[0]->type != V_STR) return d;
    char *url = args[0]->sval;
    char *proto_end = strstr(url, "://");
    if (proto_end) { dict_set(d, val_str("protocol"), val_strn(url, proto_end - url)); url = proto_end + 3; }
    else dict_set(d, val_str("protocol"), val_str("http"));
    char *path = strchr(url, '/');
    if (path) { dict_set(d, val_str("host"), val_strn(url, path - url)); dict_set(d, val_str("path"), val_str(path)); }
    else { dict_set(d, val_str("host"), val_str(url)); dict_set(d, val_str("path"), val_str("/")); }
    return d;
}
static Value *builtin_net_url_build(Value **args, int argc) {
    if (argc < 1 || args[0]->type != V_DICT) return val_str("");
    char buf[8192] = {0};
    Value *proto = dict_get(args[0], val_str("protocol"));
    Value *host = dict_get(args[0], val_str("host"));
    Value *path = dict_get(args[0], val_str("path"));
    sprintf(buf, "%s://%s%s",
        (proto && proto->type == V_STR) ? proto->sval : "http",
        (host && host->type == V_STR) ? host->sval : "",
        (path && path->type == V_STR) ? path->sval : "/");
    return val_str(buf);
}
static Value *builtin_net_tcp_connect(Value **args, int argc) { return val_int(-1); }
static Value *builtin_net_tcp_send(Value **args, int argc) { return val_nil(); }
static Value *builtin_net_tcp_recv(Value **args, int argc) { return val_str(""); }
static Value *builtin_net_tcp_close(Value **args, int argc) { return val_nil(); }
static Value *builtin_net_udp_create(Value **args, int argc) { return val_int(-1); }
static Value *builtin_net_udp_send(Value **args, int argc) { return val_nil(); }
static Value *builtin_net_udp_recv(Value **args, int argc) { return val_str(""); }

/* Base64 */
static const char b64_table[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
static Value *builtin_net_base64_encode(Value **args, int argc) {
    if (argc < 1 || args[0]->type != V_STR) return val_str("");
    char *in = args[0]->sval;
    int len = strlen(in);
    int out_len = ((len + 2) / 3) * 4 + 1;
    char *out = calloc(out_len, 1);
    int w = 0;
    for (int i = 0; i < len; i += 3) {
        int n = (unsigned char)in[i] << 16;
        if (i + 1 < len) n |= (unsigned char)in[i+1] << 8;
        if (i + 2 < len) n |= (unsigned char)in[i+2];
        out[w++] = b64_table[(n >> 18) & 63];
        out[w++] = b64_table[(n >> 12) & 63];
        out[w++] = (i + 1 < len) ? b64_table[(n >> 6) & 63] : '=';
        out[w++] = (i + 2 < len) ? b64_table[n & 63] : '=';
    }
    Value *v = val_str(out);
    free(out);
    return v;
}
static Value *builtin_net_base64_decode(Value **args, int argc) {
    if (argc < 1 || args[0]->type != V_STR) return val_str("");
    char *in = args[0]->sval;
    int len = strlen(in);
    char *out = calloc(len + 1, 1);
    int w = 0, bits = 0, val = 0;
    for (int i = 0; i < len; i++) {
        if (in[i] == '=') break;
        char *p = strchr(b64_table, in[i]);
        if (!p) continue;
        val = (val << 6) | (p - b64_table);
        bits += 6;
        if (bits >= 8) { bits -= 8; out[w++] = (val >> bits) & 0xff; }
    }
    Value *v = val_str(out);
    free(out);
    return v;
}

/* DB stubs */
static Value *builtin_db_connect(Value **args, int argc) { return val_int(-1); }
static Value *builtin_db_close(Value **args, int argc) { return val_nil(); }
static Value *builtin_db_execute(Value **args, int argc) { return val_nil(); }
static Value *builtin_db_query(Value **args, int argc) { return val_list(8); }
static Value *builtin_db_query_one(Value **args, int argc) { return val_nil(); }
static Value *builtin_db_begin_transaction(Value **args, int argc) { return val_nil(); }
static Value *builtin_db_commit(Value **args, int argc) { return val_nil(); }
static Value *builtin_db_rollback(Value **args, int argc) { return val_nil(); }
static Value *builtin_db_create_table(Value **args, int argc) { return val_nil(); }
static Value *builtin_db_drop_table(Value **args, int argc) { return val_nil(); }
static Value *builtin_db_get_tables(Value **args, int argc) { return val_list(8); }
static Value *builtin_db_get_table_info(Value **args, int argc) { return val_list(8); }

/* ═══════════════════════════════════════════════════════════════
 *  VM REGISTRY (class names → class objects)
 * ═══════════════════════════════════════════════════════════════ */

typedef struct {
    EnvNode *functions;
    EnvNode *classes;
    EnvNode *interfaces;
} Registry;

static Registry *reg_new(void) {
    Registry *r = calloc(1, sizeof(Registry));
    r->functions = env_new(NULL);
    r->classes = env_new(NULL);
    r->interfaces = env_new(NULL);
    return r;
}

/* ═══════════════════════════════════════════════════════════════
 *  EXECUTION FRAME (for iterative call stack)
 * ═══════════════════════════════════════════════════════════════ */

enum FrameMode { FM_FUNC, FM_METHOD, FM_INIT, FM_SUPER, FM_IMPORT, FM_TOP };

typedef struct VM VM;

struct Frame {
    VM *vm;
    Value **fargs; int fargs_n;
    Value *ret_val;
    enum FrameMode mode;
    Value *extra;
    struct Frame *parent;
    bool from_pool;
};

/* ═══════════════════════════════════════════════════════════════
 *  FRAME/VM MEMORY POOL (avoids malloc per function call)
 * ═══════════════════════════════════════════════════════════════ */

#define POOL_CAP 8192
#define POOL_ITEMS 256
#define POOL_EXC   16

struct ExcHandler { int target; int stack_h; };

static struct Frame *pool_frames = NULL;
static VM *pool_vms = NULL;
static Value **pool_items = NULL;
static struct ExcHandler *pool_exc = NULL;
static EnvNode *pool_envs = NULL;
static int pool_idx = 0;

static void pool_init(void);
static struct Frame *pool_alloc_frame(VM *parent_vm, enum FrameMode mode, struct Frame *parent_frame);
static void pool_free(struct Frame *f);

static struct Frame *frame_new(VM *vm, enum FrameMode mode, struct Frame *parent) {
    struct Frame *f = calloc(1, sizeof(struct Frame));
    f->vm = vm; f->mode = mode; f->parent = parent;
    return f;
}

static void frame_free(struct Frame *f);

/* ═══════════════════════════════════════════════════════════════
 *  CORE VM EXECUTOR
 * ═══════════════════════════════════════════════════════════════ */

typedef struct VM {
    Value **items; int len; int cap;   /* value stack */
    Value **block; int blen; int bcap;  /* block stack */
    EnvNode *env;
    Registry *reg;
    
    /* for function calls */
    struct Instr *instrs; int icount;
    Value **consts; int ccount;
    int pc;
    
    /* exception handling */
    struct ExcHandler *exc_handlers;
    int exc_count;
    int exc_cap;
    
    /* parent chain */
    struct VM *parent;
    
    /* DZZW worker flag — if true, don't use global pool */
    bool is_worker;
    
    /* coroutine support */
    struct VM *current_coro;
} VM;

static VM *vm_new(VM *parent) {
    VM *vm = calloc(1, sizeof(VM));
    vm->cap = 256;
    vm->items = calloc(vm->cap, sizeof(Value*));
    vm->len = 0;
    vm->env = env_new(NULL);
    vm->reg = parent ? parent->reg : reg_new();
    vm->parent = parent;
    vm->exc_cap = 16;
    vm->exc_handlers = calloc(vm->exc_cap, sizeof(struct ExcHandler));
    return vm;
}

static Registry *vm_reg(VM *vm) {
    while (vm->parent) vm = vm->parent;
    return vm->reg;
}

static void vm_push(VM *vm, Value *v) {
    if (vm->len >= vm->cap) {
        vm->cap *= 2;
        vm->items = realloc(vm->items, vm->cap * sizeof(Value*));
    }
    vm->items[vm->len++] = v;
}

static Value *vm_pop(VM *vm) {
    if (vm->len == 0) return val_nil();
    return vm->items[--vm->len];
}

static Value *vm_peek(VM *vm, int offset) {
    int idx = vm->len - 1 - offset;
    if (idx < 0) return val_nil();
    return vm->items[idx];
}

static Value *vm_lookup(VM *vm, const char *name) {
    VM *node = vm;
    while (node) {
        Value *v = env_get(node->env, name);
        if (v) return v;
        v = env_get(node->reg->functions, name);
        if (v) return v;
        node = node->parent;
    }
    return NULL;
}

static void frame_free(struct Frame *f) {
    if (!f) return;
    if (f->fargs) {
        for (int i = 0; i < f->fargs_n; i++) val_decref(f->fargs[i]);
        free(f->fargs);
    }
    if (f->ret_val) val_decref(f->ret_val);
    if (f->vm && f->mode != FM_TOP) {
        while (f->vm->len > 0) val_decref(vm_pop(f->vm));
        free(f->vm->items);
        free(f->vm->exc_handlers);
        free(f->vm);
    }
    free(f);
}

static void pool_init(void) {
    pool_frames = calloc(POOL_CAP, sizeof(struct Frame));
    pool_vms    = calloc(POOL_CAP, sizeof(VM));
    pool_items  = calloc(POOL_CAP * POOL_ITEMS, sizeof(Value*));
    pool_exc    = calloc(POOL_CAP * POOL_EXC, sizeof(struct ExcHandler));
    pool_envs   = calloc(POOL_CAP, sizeof(EnvNode));
    pool_idx = 0;
}

static struct Frame *pool_alloc_frame(VM *parent_vm, enum FrameMode mode, struct Frame *parent_frame) {
    if (parent_vm && parent_vm->is_worker) {
        VM *fallback_vm = vm_new(parent_vm);
        fallback_vm->reg = parent_vm->reg;
        fallback_vm->is_worker = true;
        struct Frame *fallback_f = frame_new(fallback_vm, mode, parent_frame);
        fallback_f->from_pool = false;
        return fallback_f;
    }
    if (pool_idx >= POOL_CAP) {
        VM *fallback_vm = vm_new(parent_vm);
        fallback_vm->reg = parent_vm ? parent_vm->reg : reg_new();
        struct Frame *fallback_f = frame_new(fallback_vm, mode, parent_frame);
        fallback_f->from_pool = false;
        return fallback_f;
    }
    int i = pool_idx++;
    
    struct Frame *f = &pool_frames[i];
    VM *v = &pool_vms[i];
    memset(f, 0, sizeof(struct Frame));
    memset(v, 0, sizeof(VM));
    memset(&pool_envs[i], 0, sizeof(EnvNode));
    
    v->cap = POOL_ITEMS;
    v->items = &pool_items[i * POOL_ITEMS];
    v->len = 0;
    v->env = &pool_envs[i];
    v->env->parent = parent_vm ? parent_vm->env : NULL;
    v->reg = parent_vm ? parent_vm->reg : NULL;
    v->exc_cap = POOL_EXC;
    v->exc_handlers = &pool_exc[i * POOL_EXC];
    v->parent = parent_vm;
    
    f->vm = v;
    f->mode = mode;
    f->parent = parent_frame;
    f->from_pool = true;
    return f;
}

static void pool_free(struct Frame *f) {
    if (!f) return;
    if (f->fargs) {
        for (int i = 0; i < f->fargs_n; i++) val_decref(f->fargs[i]);
        free(f->fargs);
    }
    if (f->ret_val) val_decref(f->ret_val);
    if (f->vm && f->mode != FM_TOP) {
        while (f->vm->len > 0) val_decref(vm_pop(f->vm));
        if (!f->from_pool) {
            free(f->vm->items);
            free(f->vm->exc_handlers);
            free(f->vm);
        }
    }
    if (f->from_pool) pool_idx--;
    else free(f);
}

/* ═══════════════════════════════════════════════════════════════
 *  DZZW HANDLE TABLE — maps integer handles to C objects
 * ═══════════════════════════════════════════════════════════════ */

#define DZZW_MAX_HANDLES 4096
static void *dzzw_handles[DZZW_MAX_HANDLES];
static pthread_mutex_t dzzw_handle_mu = PTHREAD_MUTEX_INITIALIZER;

static int dzzw_handle_put(void *ptr) {
    pthread_mutex_lock(&dzzw_handle_mu);
    for (int i = 0; i < DZZW_MAX_HANDLES; i++) {
        if (dzzw_handles[i] == NULL) {
            dzzw_handles[i] = ptr;
            pthread_mutex_unlock(&dzzw_handle_mu);
            return i + 1;
        }
    }
    pthread_mutex_unlock(&dzzw_handle_mu);
    return 0;
}

static void *dzzw_handle_get(int handle) {
    if (handle <= 0 || handle > DZZW_MAX_HANDLES) return NULL;
    return dzzw_handles[handle - 1];
}

static void *dzzw_handle_take(int handle) {
    if (handle <= 0 || handle > DZZW_MAX_HANDLES) return NULL;
    pthread_mutex_lock(&dzzw_handle_mu);
    void *ptr = dzzw_handles[handle - 1];
    if (ptr) dzzw_handles[handle - 1] = NULL;
    pthread_mutex_unlock(&dzzw_handle_mu);
    return ptr;
}

/* ═══════════════════════════════════════════════════════════════
 *  DZZW — EXECUTOR CALLBACK
 * ═══════════════════════════════════════════════════════════════ */

static VM *g_main_vm = NULL;
static void vm_execute_func(VM *vm, Value **ret_out, bool *has_ret);

/* Worker VM cleanup — called during dzzw_shutdown */
static void dzzw_cleanup_worker_vm(DZZW_Worker *w) {
    if (w->vm) {
        VM *vm = (VM *)w->vm;
        while (vm->len > 0) val_decref(vm_pop(vm));
        /* Clear env values (the env chain is shared with parent, don't free env) */
        EnvNode *n = vm->env;
        while (n) {
            if (n->value) {
                val_decref(n->value);
                n->value = NULL;
            }
            n = n->next;
        }
        free(vm->items);
        free(vm->exc_handlers);
        free(vm);
        w->vm = NULL;
    }
}

static void dzzw_executor(Value *fn, Value **args, int argc, DZZW_Future *fut, DZZW_Worker *worker) {
    VM *vm;

    /* VM reuse: use cached VM from worker if available */
    if (worker->vm) {
        vm = worker->vm;
        /* Reset stack and PC - keep allocated buffers */
        vm->len = 0;
        vm->pc = 0;
        /* Clear environment for new task, but keep parent link */
        EnvNode *n = vm->env;
        while (n) {
            if (n->value) {
                val_decref(n->value);
                n->value = NULL;
            }
            n = n->next;
        }
    } else {
        /* First task: create a new VM with main VM as parent for env lookup */
        vm = vm_new(g_main_vm);
        vm->is_worker = true;
        vm->reg = g_main_vm ? g_main_vm->reg : NULL;
        worker->vm = vm;
    }

    vm->instrs = fn->func.instrs;
    vm->icount = fn->func.icount;
    vm->consts = fn->func.consts;
    vm->ccount = fn->func.ccount;
    vm->pc = 0;

    for (int i = 0; i < argc && i < fn->func.argc; i++) {
        env_put(vm->env, fn->func.args[i], val_incref(args[i]));
    }

    Value *ret = NULL; bool has_ret = false;
    vm_execute_func(vm, &ret, &has_ret);

    if (ret) {
        dzzw_future_set(fut, ret);
    } else {
        dzzw_future_set(fut, val_nil());
    }

    /* Clear stack for next task - keep buffers allocated */
    while (vm->len > 0) {
        val_decref(vm_pop(vm));
    }
    /* VM remains cached in worker->vm, don't free it! */
}

/* ═══════════════════════════════════════════════════════════════
 *  DZZW — BUILTIN FUNCTIONS
 * ═══════════════════════════════════════════════════════════════ */

static Value *builtin_dzzw_spawn(Value **args, int argc) {
    if (argc < 2 || !args[0] || args[0]->type != V_FUNC || !args[1] || args[1]->type != V_LIST)
        return val_int(0);

    Value *fn = args[0];
    Value *arglist = args[1];
    int nargs = arglist->list.len;

    Value **cargs = calloc(nargs, sizeof(Value*));
    for (int i = 0; i < nargs; i++) cargs[i] = val_incref(arglist->list.items[i]);

    DZZW_Future *fut = dzzw_spawn(fn, cargs, nargs);
    free(cargs);

    if (!fut) return val_int(0);

    int handle = dzzw_handle_put(fut);
    return val_int(handle);
}

static Value *builtin_dzzw_await(Value **args, int argc) {
    if (argc < 1 || !args[0] || args[0]->type != V_INT) return val_nil();

    int handle = (int)args[0]->ival;
    DZZW_Future *fut = dzzw_handle_take(handle);
    if (!fut) return val_nil();

    Value *result = dzzw_future_wait(fut);
    dzzw_future_free(fut);
    return val_incref(result);
}

static Value *builtin_dzzw_parallel_map(Value **args, int argc) {
    if (argc < 2 || !args[0] || args[0]->type != V_FUNC || !args[1] || args[1]->type != V_LIST)
        return val_nil();

    Value *fn = args[0];
    Value *list = args[1];
    int n = list->list.len;

    DZZW_Future **futures = calloc(n, sizeof(DZZW_Future*));

    for (int i = 0; i < n; i++) {
        Value **cargs = calloc(1, sizeof(Value*));
        cargs[0] = val_incref(list->list.items[i]);

        DZZW_Future *fut = dzzw_future_new();
        futures[i] = fut;

        DZZW_Task *task = calloc(1, sizeof(DZZW_Task));
        task->fn = fn;
        task->argc = 1;
        task->args = cargs;
        task->future = fut;

        dzzw_enqueue(task);
    }

    Value *results = val_list(n);
    for (int i = 0; i < n; i++) {
        Value *r = dzzw_future_wait(futures[i]);
        list_push(results, r);
        dzzw_future_free(futures[i]);
    }
    free(futures);

    return results;
}

static Value *builtin_dzzw_worker_count(Value **args, int argc) {
    (void)args; (void)argc;
    return val_int(dzzw_worker_count());
}

static Value *builtin_dzzw_pending_count(Value **args, int argc) {
    (void)args; (void)argc;
    return val_int(dzzw_pending_count());
}

static Value *builtin_dzzw_channel_create(Value **args, int argc) {
    int cap = 64;
    if (argc >= 1 && args[0] && args[0]->type == V_INT) cap = (int)args[0]->ival;
    DZZW_Channel *ch = dzzw_channel_new(cap);
    int handle = dzzw_handle_put(ch);
    return val_int(handle);
}

static Value *builtin_dzzw_channel_send(Value **args, int argc) {
    if (argc < 2 || !args[0] || args[0]->type != V_INT) return val_nil();
    int handle = (int)args[0]->ival;
    DZZW_Channel *ch = dzzw_handle_get(handle);
    if (!ch) return val_nil();

    dzzw_channel_send(ch, val_incref(args[1]));
    return val_nil();
}

static Value *builtin_dzzw_channel_recv(Value **args, int argc) {
    if (argc < 1 || !args[0] || args[0]->type != V_INT) return val_nil();
    int handle = (int)args[0]->ival;
    DZZW_Channel *ch = dzzw_handle_get(handle);
    if (!ch) return val_nil();

    Value *v = dzzw_channel_recv(ch);
    return v;
}

static Value *builtin_dzzw_channel_free(Value **args, int argc) {
    if (argc < 1 || !args[0] || args[0]->type != V_INT) return val_nil();
    int handle = (int)args[0]->ival;
    DZZW_Channel *ch = dzzw_handle_take(handle);
    if (!ch) return val_nil();
    dzzw_channel_free(ch);
    return val_nil();
}

static Value *builtin_dzzw_mutex_create(Value **args, int argc) {
    (void)args; (void)argc;
    DZZW_Mutex *m = dzzw_mutex_new();
    int handle = dzzw_handle_put(m);
    return val_int(handle);
}

static Value *builtin_dzzw_mutex_lock(Value **args, int argc) {
    if (argc < 1 || !args[0] || args[0]->type != V_INT) return val_nil();
    int handle = (int)args[0]->ival;
    DZZW_Mutex *m = dzzw_handle_get(handle);
    if (!m) return val_nil();
    dzzw_mutex_lock(m);
    return val_nil();
}

static Value *builtin_dzzw_mutex_unlock(Value **args, int argc) {
    if (argc < 1 || !args[0] || args[0]->type != V_INT) return val_nil();
    int handle = (int)args[0]->ival;
    DZZW_Mutex *m = dzzw_handle_get(handle);
    if (!m) return val_nil();
    dzzw_mutex_unlock(m);
    return val_nil();
}

static Value *builtin_dzzw_mutex_free(Value **args, int argc) {
    if (argc < 1 || !args[0] || args[0]->type != V_INT) return val_nil();
    int handle = (int)args[0]->ival;
    DZZW_Mutex *m = dzzw_handle_take(handle);
    if (!m) return val_nil();
    dzzw_mutex_free(m);
    return val_nil();
}

/* ═══════════════════════════════════════════════════════════════
 *  DZZW v2.0 — NEW BUILTINS
 * ═══════════════════════════════════════════════════════════════ */

static Value *builtin_dzzw_try_await(Value **args, int argc) {
    if (argc < 1 || !args[0] || args[0]->type != V_INT) return val_nil();
    int handle = (int)args[0]->ival;
    DZZW_Future *fut = dzzw_handle_get(handle);
    if (!fut) return val_nil();
    Value *result = dzzw_future_try_wait(fut);
    if (!result) return val_nil(); /* still pending */
    /* Take the handle and free the future on success */
    dzzw_handle_take(handle);
    dzzw_future_free(fut);
    return val_incref(result);
}

static Value *builtin_dzzw_await_any(Value **args, int argc) {
    if (argc < 1 || !args[0] || args[0]->type != V_LIST) return val_int(-1);
    Value *handle_list = args[0];
    int n = handle_list->list.len;
    if (n == 0) return val_int(-1);

    DZZW_Future **futures = calloc(n, sizeof(DZZW_Future*));
    for (int i = 0; i < n; i++) {
        if (handle_list->list.items[i] && handle_list->list.items[i]->type == V_INT) {
            int h = (int)handle_list->list.items[i]->ival;
            futures[i] = dzzw_handle_get(h);
        }
    }

    int idx = dzzw_await_any(futures, n);
    free(futures);
    return val_int(idx);
}

static Value *builtin_dzzw_await_all(Value **args, int argc) {
    if (argc < 1 || !args[0] || args[0]->type != V_LIST) return val_nil();
    Value *handle_list = args[0];
    int n = handle_list->list.len;

    DZZW_Future **futures = calloc(n, sizeof(DZZW_Future*));
    for (int i = 0; i < n; i++) {
        if (handle_list->list.items[i] && handle_list->list.items[i]->type == V_INT) {
            int h = (int)handle_list->list.items[i]->ival;
            futures[i] = dzzw_handle_get(h);
        }
    }

    dzzw_await_all(futures, n);
    free(futures);
    return val_nil();
}

static Value *builtin_dzzw_total_completed(Value **args, int argc) {
    (void)args; (void)argc;
    return val_int(dzzw_total_completed());
}

static Value *builtin_dzzw_total_submitted(Value **args, int argc) {
    (void)args; (void)argc;
    return val_int(dzzw_total_submitted());
}

static Value *builtin_dzzw_dump_stats(Value **args, int argc) {
    (void)args; (void)argc;
    dzzw_dump_stats();
    return val_int(1);
}

static void vm_register_builtins(VM *vm) {
    Registry *r = vm_reg(vm);
    #define B(name, fn) env_put(r->functions, name, val_builtin(name, fn))
    B("len", builtin_len);
    B("push", builtin_push);
    B("pop", builtin_pop);
    B("read_file", builtin_read_file);
    B("write_file", builtin_write_file);
    B("typeof", builtin_typeof);
    B("input", builtin_str_cast); /* simplified */
    B("time_now", builtin_time_now);
    B("substring", builtin_substring);
    B("ord", builtin_ord);
    B("chr", builtin_chr);
    B("int", builtin_int_cast);
    B("str", builtin_str_cast);
    B("date_now", builtin_date_now);
    B("date_timestamp", builtin_date_timestamp);
    B("date_format", builtin_date_format);
    B("date_parse", builtin_date_parse);
    B("fs_exists", builtin_fs_exists);
    B("fs_is_file", builtin_fs_is_file);
    B("fs_is_dir", builtin_fs_is_dir);
    B("fs_mkdir", builtin_fs_mkdir);
    B("fs_remove", builtin_fs_remove);
    B("fs_list_dir", builtin_fs_list_dir);
    B("fs_get_cwd", builtin_fs_get_cwd);
    B("fs_chdir", builtin_fs_chdir);
    B("fs_join_path", builtin_fs_join_path);
    B("fs_get_ext", builtin_fs_get_ext);
    B("fs_get_basename", builtin_fs_get_basename);
    B("fs_get_dirname", builtin_fs_get_dirname);
    B("io_append_file", builtin_io_append_file);
    B("io_read_lines", builtin_io_read_lines);
    B("io_write_lines", builtin_io_write_lines);
    B("http_get", builtin_net_http_get);
    B("http_post", builtin_net_http_post);
    B("url_parse", builtin_net_url_parse);
    B("url_build", builtin_net_url_build);
    B("tcp_connect", builtin_net_tcp_connect);
    B("tcp_send", builtin_net_tcp_send);
    B("tcp_recv", builtin_net_tcp_recv);
    B("tcp_close", builtin_net_tcp_close);
    B("udp_create", builtin_net_udp_create);
    B("udp_send", builtin_net_udp_send);
    B("udp_recv", builtin_net_udp_recv);
    B("base64_encode", builtin_net_base64_encode);
    B("base64_decode", builtin_net_base64_decode);
    B("json_stringify", builtin_json_stringify);
    B("json_parse", builtin_json_parse);
    B("db_connect", builtin_db_connect);
    B("db_close", builtin_db_close);
    B("db_execute", builtin_db_execute);
    B("db_query", builtin_db_query);
    B("db_query_one", builtin_db_query_one);
    B("db_begin_transaction", builtin_db_begin_transaction);
    B("db_commit", builtin_db_commit);
    B("db_rollback", builtin_db_rollback);
    B("db_create_table", builtin_db_create_table);
    B("db_drop_table", builtin_db_drop_table);
    B("db_get_tables", builtin_db_get_tables);
    B("db_get_table_info", builtin_db_get_table_info);
    B("htable_create", builtin_htable_create);
    B("htable_set", builtin_htable_set);
    B("htable_get", builtin_htable_get);
    B("htable_has", builtin_htable_has);
    B("htable_delete", builtin_htable_delete);
    B("htable_size", builtin_htable_size);
    B("htable_keys", builtin_htable_keys);
    B("htable_values", builtin_htable_values);
    B("dzzw_spawn", builtin_dzzw_spawn);
    B("dzzw_await", builtin_dzzw_await);
    B("dzzw_parallel_map", builtin_dzzw_parallel_map);
    B("dzzw_worker_count", builtin_dzzw_worker_count);
    B("dzzw_pending_count", builtin_dzzw_pending_count);
    B("dzzw_channel_create", builtin_dzzw_channel_create);
    B("dzzw_channel_send", builtin_dzzw_channel_send);
    B("dzzw_channel_recv", builtin_dzzw_channel_recv);
    B("dzzw_channel_free", builtin_dzzw_channel_free);
    B("dzzw_mutex_create", builtin_dzzw_mutex_create);
    B("dzzw_mutex_lock", builtin_dzzw_mutex_lock);
    B("dzzw_mutex_unlock", builtin_dzzw_mutex_unlock);
    B("dzzw_mutex_free", builtin_dzzw_mutex_free);
    /* DZZW v2.0 new builtins */
    B("dzzw_try_await", builtin_dzzw_try_await);
    B("dzzw_await_any", builtin_dzzw_await_any);
    B("dzzw_await_all", builtin_dzzw_await_all);
    B("dzzw_total_completed", builtin_dzzw_total_completed);
    B("dzzw_total_submitted", builtin_dzzw_total_submitted);
    B("dzzw_dump_stats", builtin_dzzw_dump_stats);
    #undef B
}

static Value *make_inst(VM *vm, Value *cls_obj) {
    Value *resolved = cls_obj;
    /* walk inheritance chain */
    while (resolved && resolved->type == V_CLASS && resolved->cls.base) {
        Value *base = resolved->cls.base;
        /* merge base fields */
        if (base && base->type == V_CLASS) {
            EnvNode *n = base->cls.fields;
            while (n) { if (!env_has(resolved->cls.fields, n->name)) env_put(resolved->cls.fields, n->name, val_incref(n->value)); n = n->next; }
        }
        resolved = base;
    }
    
    Value *inst = val_new(V_INST);
    inst->instance.klass = val_incref(cls_obj);
    inst->instance.fields = env_new(NULL);
    EnvNode *n = cls_obj->cls.fields;
    while (n) { env_put(inst->instance.fields, n->name, val_incref(n->value)); n = n->next; }
    return inst;
}

static void vm_execute_func(VM *vm, Value **ret_out, bool *has_ret) {
    struct Frame *frame = frame_new(vm, FM_TOP, NULL);
    
frame_loop:
    while (frame->vm->pc < frame->vm->icount) {
        VM *vm = frame->vm;
        
        struct Instr *in = &vm->instrs[vm->pc];
        int op = in->opcode;
        Value *arg = in->arg;
        vm->pc++;
        
        switch (op) {
        break;
        case OP_HALT: frame->ret_val = NULL; goto frame_done;
        break;
        case OP_LOAD_CONST: {
            int idx = arg ? (arg->type == V_INT ? (int)arg->ival : 0) : 0;
            if (idx >= 0 && idx < vm->ccount) vm_push(vm, val_incref(vm->consts[idx]));
            else vm_push(vm, val_nil());
        }
        break;
        case OP_LOAD_NAME: {
            if (arg && arg->type == V_STR) {
                Value *v = vm_lookup(vm, arg->sval);
                static int debug_trace = 1;
                if (debug_trace) {
                    const char *n = arg->sval;
                    int is_parser = (strcmp(n, "__pos")==0 || strcmp(n, "__n")==0 || strcmp(n, "__tokens")==0 ||
                                     strcmp(n, "cur")==0 || strcmp(n, "peek_type")==0 || strcmp(n, "peek_val")==0 ||
                                     strcmp(n, "advance")==0 || strcmp(n, "expect")==0 ||
                                     strcmp(n, "parse_program")==0 || strcmp(n, "parse_block")==0 ||
                                     strcmp(n, "parse_statement")==0);
                    if (is_parser) {
                        printf("[LOAD_NAME %s] vm=%p env=%p found=%d", n, (void*)vm, (void*)vm->env, v!=NULL);
                        if (v && v->type == V_INT) printf(" val=%lld", (long long)v->ival);
                        if (v && v->type == V_STR) printf(" val=%s", v->sval);
                        printf("\n");
                    }
                }
                if (v) vm_push(vm, val_incref(v));
                else vm_push(vm, val_nil());
            } else vm_push(vm, val_nil());
        }
        break;
        case OP_STORE_NAME: {
            if (arg && arg->type == V_STR) {
                Value *v = vm_pop(vm);
                const char *name = arg->sval;

                EnvNode *found = NULL;
                EnvNode *e = vm->env;
                while (e) {
                    EnvNode *n = e;
                    while (n && n->next) {
                        if (n->name && strcmp(n->name, name) == 0) { found = n; break; }
                        n = n->next;
                    }
                    if (found) break;
                    if (n && n->name && strcmp(n->name, name) == 0) { found = n; break; }
                    e = e->parent;
                }

                if (found) {
                    static int debug_trace2 = 1;
                    if (debug_trace2) {
                        const char *n = name;
                        int is_parser = (strcmp(n, "__pos")==0 || strcmp(n, "__n")==0 || strcmp(n, "__tokens")==0 ||
                                         strcmp(n, "cur")==0 || strcmp(n, "peek_type")==0 || strcmp(n, "peek_val")==0 ||
                                         strcmp(n, "advance")==0 || strcmp(n, "expect")==0 ||
                                         strcmp(n, "parse_program")==0 || strcmp(n, "parse_block")==0 ||
                                         strcmp(n, "parse_statement")==0);
                        if (is_parser) {
                            printf("[STORE_NAME %s] vm=%p env=%p FOUND_IN_PARENT\n", n, (void*)vm, (void*)vm->env);
                        }
                    }
                    val_decref(found->value);
                    found->value = v;
                } else {
                    static int debug_trace3 = 1;
                    if (debug_trace3) {
                        const char *n = name;
                        int is_parser = (strcmp(n, "__pos")==0 || strcmp(n, "__n")==0 || strcmp(n, "__tokens")==0 ||
                                         strcmp(n, "cur")==0 || strcmp(n, "peek_type")==0 || strcmp(n, "peek_val")==0 ||
                                         strcmp(n, "advance")==0 || strcmp(n, "expect")==0 ||
                                         strcmp(n, "parse_program")==0 || strcmp(n, "parse_block")==0 ||
                                         strcmp(n, "parse_statement")==0);
                        if (is_parser) {
                            printf("[STORE_NAME %s] vm=%p env=%p CREATING_NEW", n, (void*)vm, (void*)vm->env);
                            if (v && v->type == V_INT) printf(" val=%lld", (long long)v->ival);
                            if (v && v->type == V_STR) printf(" val=%s", v->sval);
                            printf("\n");
                        }
                    }
                    env_put(vm->env, name, v);
                }
            } else vm_pop(vm);
        }
        break;
        case OP_PRINT: {
            Value *v = vm_pop(vm);
            switch (v->type) {
            case V_NIL: printf("null\n"); break;
            case V_BOOL: printf("%s\n", v->bval ? "true" : "false"); break;
            case V_INT: printf("%lld\n", (long long)v->ival); break;
            case V_FLOAT: printf("%.17g\n", v->fval); break;
            case V_STR: printf("%s\n", v->sval); break;
            default: printf("[object]\n"); break;
            }
            fflush(stdout);
            val_decref(v);
        }
        break;
        case OP_POP_TOP: { Value *v = vm_pop(vm); val_decref(v); }
        break;
        case OP_MAKE_LIST: {
            int n = arg ? (arg->type == V_INT ? (int)arg->ival : 0) : 0;
            Value *lst = val_list(n > 0 ? n : 8);
            Value **tmp = n > 0 ? malloc(n * sizeof(Value*)) : NULL;
            for (int i = n - 1; i >= 0; i--) tmp[i] = vm_pop(vm);
            for (int i = 0; i < n; i++) list_push(lst, tmp[i]);
            if (tmp) free(tmp);
            vm_push(vm, lst);
        }
        break;
        case OP_MAKE_DICT: {
            int n = arg ? (arg->type == V_INT ? (int)arg->ival : 0) : 0;
            Value *d = val_dict(n > 0 ? n : 8);
            for (int i = 0; i < n; i++) {
                Value *val = vm_pop(vm);
                Value *key = vm_pop(vm);
                dict_set(d, key, val);
                val_decref(key); val_decref(val);
            }
            vm_push(vm, d);
        }
        break;
        case OP_GET_ITEM: {
            Value *idx = vm_pop(vm);
            Value *left = vm_pop(vm);
            if (left->type == V_LIST && idx->type == V_INT) {
                int i = (int)idx->ival;
                if (i >= 0 && i < left->list.len) vm_push(vm, val_incref(left->list.items[i]));
                else { fprintf(stderr, "Index %d out of range\n", i); vm_push(vm, val_nil()); }
            } else if (left->type == V_STR && idx->type == V_INT) {
                int i = (int)idx->ival;
                if (i >= 0 && i < (int)strlen(left->sval)) { char buf[2] = {left->sval[i], 0}; vm_push(vm, val_str(buf)); }
                else vm_push(vm, val_nil());
            } else if (left->type == V_DICT) {
                Value *v = dict_get(left, idx);
                vm_push(vm, v ? val_incref(v) : val_nil());
            } else { vm_push(vm, val_nil()); }
            val_decref(idx); val_decref(left);
        }
        break;
        case OP_LOAD_ATTR: {
            if (!arg || arg->type != V_STR) { vm_pop(vm); vm_push(vm, val_nil()); continue; }
            Value *obj = vm_pop(vm);
            char *name = arg->sval;
            if (obj->type == V_INST) {
                Value *v = inst_get(obj, name);
                if (v) vm_push(vm, val_incref(v));
                else {
                    Value *m = inst_method(obj, name);
                    if (m) {
                        Value *bound = val_new(V_DICT);
                        dict_set(bound, val_str("__method__"), val_incref(m));
                        dict_set(bound, val_str("__self__"), val_incref(obj));
                        vm_push(vm, bound);
                    } else vm_push(vm, val_nil());
                }
            } else if (obj->type == V_DICT) {
                Value *key = val_str(name);
                Value *v = dict_get(obj, key);
                if (v) vm_push(vm, val_incref(v));
                else vm_push(vm, val_nil());
                val_decref(key);
            } else if (obj->type == V_CLASS) {
                Value *v = env_get(obj->cls.methods, name);
                if (v) vm_push(vm, val_incref(v));
                else { v = env_get(obj->cls.fields, name); vm_push(vm, v ? val_incref(v) : val_nil()); }
            } else { vm_push(vm, val_nil()); }
            val_decref(obj);
        }
        break;
        case OP_STORE_ATTR: {
            if (!arg || arg->type != V_STR) { vm_pop(vm); vm_pop(vm); continue; }
            Value *val = vm_pop(vm);
            Value *obj = vm_pop(vm);
            if (obj->type == V_INST) {
                env_put(obj->instance.fields, arg->sval, val_incref(val));
            } else if (obj->type == V_DICT) {
                dict_set(obj, val_str(arg->sval), val_incref(val));
            }
            vm_push(vm, val_incref(val));
            val_decref(obj); val_decref(val);
        }
        break;
        case OP_SET_ITEM: {
            Value *val = vm_pop(vm), *idx = vm_pop(vm), *left = vm_pop(vm);
            if (left->type == V_LIST && idx->type == V_INT) {
                int i = (int)idx->ival;
                if (i >= 0 && i < left->list.len) { val_decref(left->list.items[i]); left->list.items[i] = val_incref(val); }
            } else if (left->type == V_DICT) { dict_set(left, idx, val_incref(val)); }
            vm_push(vm, val_incref(val));
            val_decref(val); val_decref(idx); val_decref(left);
        }
        break;
        case OP_BINARY_ADD: {
            Value *b = vm_pop(vm), *a = vm_pop(vm);
            if (a->type == V_STR || b->type == V_STR) {
                char *sa = a->type == V_STR ? a->sval : "";
                char *sb = b->type == V_STR ? b->sval : "";
                char *buf = malloc(strlen(sa) + strlen(sb) + 1);
                sprintf(buf, "%s%s", sa, sb);
                vm_push(vm, val_str(buf)); free(buf);
            } else if (val_is_number(a) && val_is_number(b)) {
                bool is_float = (a->type == V_FLOAT || b->type == V_FLOAT);
                if (is_float) vm_push(vm, val_float(val_as_double(a) + val_as_double(b)));
                else vm_push(vm, val_int(val_as_int(a) + val_as_int(b)));
            } else if (a->type == V_LIST && b->type == V_LIST) {
                Value *nl = val_list(a->list.len + b->list.len);
                for (int i = 0; i < a->list.len; i++) list_push(nl, a->list.items[i]);
                for (int i = 0; i < b->list.len; i++) list_push(nl, b->list.items[i]);
                vm_push(vm, nl);
            } else { vm_push(vm, val_int(0)); }
            val_decref(a); val_decref(b);
        }
        break;
        case OP_BINARY_SUB: {
            Value *b = vm_pop(vm), *a = vm_pop(vm);
            if (val_is_number(a) && val_is_number(b)) {
                bool is_float = (a->type == V_FLOAT || b->type == V_FLOAT);
                if (is_float) vm_push(vm, val_float(val_as_double(a) - val_as_double(b)));
                else vm_push(vm, val_int(val_as_int(a) - val_as_int(b)));
            } else vm_push(vm, val_int(0));
            val_decref(a); val_decref(b);
        }
        break;
        case OP_BINARY_MUL: {
            Value *b = vm_pop(vm), *a = vm_pop(vm);
            if (val_is_number(a) && val_is_number(b)) {
                if (a->type == V_STR || b->type == V_STR) {
                    char *s = a->type == V_STR ? a->sval : b->sval;
                    int n = (int)(a->type == V_STR ? val_as_int(b) : val_as_int(a));
                    Value *nl = val_list(0);
                    for (int i = 0; i < n; i++) list_push(nl, val_str(s));
                    vm_push(vm, nl);
                } else {
                    bool is_float = (a->type == V_FLOAT || b->type == V_FLOAT);
                    if (is_float) vm_push(vm, val_float(val_as_double(a) * val_as_double(b)));
                    else vm_push(vm, val_int(val_as_int(a) * val_as_int(b)));
                }
            } else vm_push(vm, val_int(0));
            val_decref(a); val_decref(b);
        }
        break;
        case OP_BINARY_DIV: {
            Value *b = vm_pop(vm), *a = vm_pop(vm);
            if (val_is_number(a) && val_is_number(b)) {
                double db = val_as_double(b);
                if (db == 0) { fprintf(stderr, "Division by zero\n"); vm_push(vm, val_int(0)); }
                else {
                    double result = val_as_double(a) / db;
                    if (a->type == V_INT && b->type == V_INT && val_as_int(a) % val_as_int(b) == 0)
                        vm_push(vm, val_int(val_as_int(a) / val_as_int(b)));
                    else vm_push(vm, val_float(result));
                }
            } else vm_push(vm, val_int(0));
            val_decref(a); val_decref(b);
        }
        break;
        case OP_BINARY_MOD: {
            Value *b = vm_pop(vm), *a = vm_pop(vm);
            if (val_is_number(a) && val_is_number(b))
                vm_push(vm, val_int(val_as_int(a) % val_as_int(b)));
            else vm_push(vm, val_int(0));
            val_decref(a); val_decref(b);
        }
        break;
        case OP_BINARY_BITAND: {
            Value *b = vm_pop(vm), *a = vm_pop(vm);
            if (val_is_number(a) && val_is_number(b))
                vm_push(vm, val_int(val_as_int(a) & val_as_int(b)));
            else vm_push(vm, val_int(0));
            val_decref(a); val_decref(b);
        }
        break;
        case OP_BINARY_BITOR: {
            Value *b = vm_pop(vm), *a = vm_pop(vm);
            if (val_is_number(a) && val_is_number(b))
                vm_push(vm, val_int(val_as_int(a) | val_as_int(b)));
            else vm_push(vm, val_int(0));
            val_decref(a); val_decref(b);
        }
        break;
        case OP_BINARY_BITXOR: {
            Value *b = vm_pop(vm), *a = vm_pop(vm);
            if (val_is_number(a) && val_is_number(b))
                vm_push(vm, val_int(val_as_int(a) ^ val_as_int(b)));
            else vm_push(vm, val_int(0));
            val_decref(a); val_decref(b);
        }
        break;
        case OP_BINARY_LSHIFT: {
            Value *b = vm_pop(vm), *a = vm_pop(vm);
            if (val_is_number(a) && val_is_number(b))
                vm_push(vm, val_int(val_as_int(a) << val_as_int(b)));
            else vm_push(vm, val_int(0));
            val_decref(a); val_decref(b);
        }
        break;
        case OP_BINARY_RSHIFT: {
            Value *b = vm_pop(vm), *a = vm_pop(vm);
            if (val_is_number(a) && val_is_number(b))
                vm_push(vm, val_int(val_as_int(a) >> val_as_int(b)));
            else vm_push(vm, val_int(0));
            val_decref(a); val_decref(b);
        }
        break;
        case OP_UNARY_NOT: {
            Value *a = vm_pop(vm);
            bool b = false;
            if (a->type == V_BOOL) b = !a->bval;
            else if (a->type == V_NIL) b = true;
            vm_push(vm, val_bool(b));
            val_decref(a);
        }
        break;
        case OP_UNARY_TILDE: {
            Value *a = vm_pop(vm);
            if (a->type == V_INT) vm_push(vm, val_int(~a->ival));
            else vm_push(vm, val_int(0));
            val_decref(a);
        }
        break;
        case OP_COMPARE_OP: {
            if (!arg || arg->type != V_STR) { vm_pop(vm); vm_pop(vm); vm_push(vm, val_bool(false)); continue; }
            Value *b = vm_pop(vm), *a = vm_pop(vm);
            char *opname = arg->sval;
            if (strcmp(opname, "EQEQ") == 0) {
                bool eq = false;
                if (a->type == b->type) {
                    switch (a->type) {
                    case V_NIL: eq = true; break;
                    case V_BOOL: eq = a->bval == b->bval; break;
                    case V_INT: eq = a->ival == b->ival; break;
                    case V_FLOAT: eq = a->fval == b->fval; break;
                    case V_STR: eq = strcmp(a->sval, b->sval) == 0; break;
                    default: eq = false; break;
                    }
                }
                vm_push(vm, val_bool(eq));
            } else if (strcmp(opname, "BANGEQ") == 0) {
                bool eq = false;
                if (a->type == b->type) {
                    switch (a->type) {
                    case V_NIL: eq = true; break;
                    case V_BOOL: eq = a->bval == b->bval; break;
                    case V_INT: eq = a->ival == b->ival; break;
                    case V_FLOAT: eq = a->fval == b->fval; break;
                    case V_STR: eq = strcmp(a->sval, b->sval) == 0; break;
                    default: eq = false; break;
                    }
                }
                vm_push(vm, val_bool(!eq));
            } else {
                if (a->type == V_STR && b->type == V_STR) {
                    int cmp = strcmp(a->sval, b->sval);
                    if (strcmp(opname, "GT") == 0) vm_push(vm, val_bool(cmp > 0));
                    else if (strcmp(opname, "LT") == 0) vm_push(vm, val_bool(cmp < 0));
                    else if (strcmp(opname, "GTE") == 0) vm_push(vm, val_bool(cmp >= 0));
                    else if (strcmp(opname, "LTE") == 0) vm_push(vm, val_bool(cmp <= 0));
                    else vm_push(vm, val_bool(false));
                } else {
                    double da = a->type == V_INT ? (double)a->ival : a->type == V_FLOAT ? a->fval : 0;
                    double db = b->type == V_INT ? (double)b->ival : b->type == V_FLOAT ? b->fval : 0;
                    if (strcmp(opname, "GT") == 0) vm_push(vm, val_bool(da > db));
                    else if (strcmp(opname, "LT") == 0) vm_push(vm, val_bool(da < db));
                    else if (strcmp(opname, "GTE") == 0) vm_push(vm, val_bool(da >= db));
                    else if (strcmp(opname, "LTE") == 0) vm_push(vm, val_bool(da <= db));
                    else vm_push(vm, val_bool(false));
                }
            }
            val_decref(a); val_decref(b);
        }
        break;
        case OP_JUMP_IF_FALSE: {
            int target = arg ? (arg->type == V_INT ? (int)arg->ival : 0) : 0;
            Value *cond = vm_pop(vm);
            bool is_false = false;
            if (cond->type == V_BOOL) is_false = !cond->bval;
            else if (cond->type == V_NIL) is_false = true;
            else if (cond->type == V_INT) is_false = (cond->ival == 0);
            val_decref(cond);
            if (is_false) vm->pc = target;
        }
        break;
        case OP_JUMP: {
            int target = arg ? (arg->type == V_INT ? (int)arg->ival : 0) : 0;
            vm->pc = target;
        }
        break;
        case OP_SETUP_EXCEPT: {
            int target = arg ? (arg->type == V_INT ? (int)arg->ival : 0) : 0;
            if (vm->exc_count >= vm->exc_cap) { vm->exc_cap *= 2; vm->exc_handlers = realloc(vm->exc_handlers, vm->exc_cap * sizeof(*vm->exc_handlers)); }
            vm->exc_handlers[vm->exc_count].target = target;
            vm->exc_handlers[vm->exc_count].stack_h = vm->len;
            vm->exc_count++;
        }
        break;
        case OP_POP_EXCEPT: {
            if (vm->exc_count > 0) vm->exc_count--;
        }
        break;
        case OP_RAISE: {
            Value *exc = vm_pop(vm);
            fprintf(stderr, "Exception: ");
            if (exc->type == V_STR) fprintf(stderr, "%s", exc->sval);
            else fprintf(stderr, "<type %d>", exc->type);
            fprintf(stderr, "\n");
            bool handled = false;
            while (vm->exc_count > 0) {
                vm->exc_count--;
                int target = vm->exc_handlers[vm->exc_count].target;
                int sh = vm->exc_handlers[vm->exc_count].stack_h;
                if (target < 0) continue;
                while (vm->len > sh) { Value *v = vm_pop(vm); val_decref(v); }
                vm_push(vm, exc);
                vm->pc = target;
                handled = true;
            }
            if (!handled) { val_decref(exc); fprintf(stderr, "Unhandled exception, aborting\n"); *has_ret = false; return; }
        }
        case OP_RETURN_VALUE: {
            frame->ret_val = vm->len > 0 ? vm_pop(vm) : val_nil();
            goto frame_done;
        }
        case OP_CALL_FUNCTION: {
            if (!arg || arg->type != V_LIST || arg->list.len < 2) continue;
            Value *name_v = arg->list.items[0];
            Value *argc_v = arg->list.items[1];
            char *fname = (name_v && name_v->type == V_STR) ? name_v->sval : "";
            int argc_c = (argc_v && argc_v->type == V_INT) ? (int)argc_v->ival : 0;
            
            Value *fargs_buf[16];
            Value **fargs;
            if (argc_c <= 16) fargs = fargs_buf;
            else fargs = malloc(argc_c * sizeof(Value*));
            for (int i = argc_c - 1; i >= 0; i--) fargs[i] = vm_pop(vm);
            
            Value *builtin = env_get(vm->reg->functions, fname);
            if (builtin && builtin->type == V_BUILTIN && builtin->builtin.fn) {
                Value *ret = builtin->builtin.fn(fargs, argc_c);
                vm_push(vm, ret);
                for (int i = 0; i < argc_c; i++) val_decref(fargs[i]);
                if (fargs != fargs_buf) free(fargs);
                continue;
            }
            
            Value *func = vm_lookup(vm, fname);
            if (func && func->type == V_FUNC) {
                if (func->func.argc != argc_c) {
                    fprintf(stderr, "Function %s expects %d args, got %d\n", fname, func->func.argc, argc_c);
                    for (int i = 0; i < argc_c; i++) val_decref(fargs[i]);
                    if (fargs != fargs_buf) free(fargs);
                    vm_push(vm, val_nil());
                    continue;
                }
                struct Frame *newf = pool_alloc_frame(vm, FM_FUNC, frame);
                newf->vm->instrs = func->func.instrs; newf->vm->icount = func->func.icount;
                newf->vm->consts = func->func.consts; newf->vm->ccount = func->func.ccount;
                newf->vm->pc = 0;
                for (int i = 0; i < func->func.argc; i++)
                    env_put(newf->vm->env, func->func.args[i], val_incref(fargs[i]));
                Value **heap_fargs = argc_c > 0 ? malloc(argc_c * sizeof(Value*)) : NULL;
                if (heap_fargs) memcpy(heap_fargs, fargs, argc_c * sizeof(Value*));
                newf->fargs = heap_fargs;
                newf->fargs_n = argc_c;
                frame = newf;
                goto frame_loop;
            }
            
            fprintf(stderr, "Unknown function: %s\n", fname);
            for (int i = 0; i < argc_c; i++) val_decref(fargs[i]);
            if (fargs != fargs_buf) free(fargs);
            vm_push(vm, val_nil());
        }
        case OP_CALL_METHOD: {
            if (!arg || arg->type != V_LIST || arg->list.len < 2) continue;
            Value *name_v = arg->list.items[0];
            Value *argc_v = arg->list.items[1];
            char *mname = (name_v && name_v->type == V_STR) ? name_v->sval : "";
            int argc_c = (argc_v && argc_v->type == V_INT) ? (int)argc_v->ival : 0;
            
            Value *fargs_buf[16];
            Value **fargs;
            if (argc_c <= 16) fargs = fargs_buf;
            else fargs = malloc(argc_c * sizeof(Value*));
            for (int i = argc_c - 1; i >= 0; i--) fargs[i] = vm_pop(vm);
            Value *inst = vm_pop(vm);
            
            Value *method = NULL;
            Value *self = inst;
            if (inst->type == V_DICT) {
                Value *m = dict_get(inst, val_str("__method__"));
                Value *s = dict_get(inst, val_str("__self__"));
                if (m) method = m;
                if (s) self = s;
            }
            if (inst->type == V_INST) {
                method = inst_method(inst, mname);
            }
            if (inst->type == V_CLASS) {
                Value *static_methods = env_get(inst->cls.methods, "__static__");
                if (static_methods && static_methods->type == V_DICT) {
                    Value *key = val_str(mname); method = dict_get(static_methods, key); val_decref(key);
                }
                if (!method) method = env_get(inst->cls.methods, mname);
            }
            
            if (method && method->type == V_FUNC) {
                if (method->func.argc != argc_c) {
                    fprintf(stderr, "Method %s expects %d args, got %d\n", mname, method->func.argc, argc_c);
                } else {
                    struct Frame *newf = pool_alloc_frame(vm, FM_METHOD, frame);
                    newf->vm->instrs = method->func.instrs; newf->vm->icount = method->func.icount;
                    newf->vm->consts = method->func.consts; newf->vm->ccount = method->func.ccount;
                    newf->vm->pc = 0;
                    env_put(newf->vm->env, "self", val_incref(self));
                    for (int i = 0; i < method->func.argc; i++)
                        env_put(newf->vm->env, method->func.args[i], val_incref(fargs[i]));
                    Value **heap_fargs = argc_c > 0 ? malloc(argc_c * sizeof(Value*)) : NULL;
                    if (heap_fargs) memcpy(heap_fargs, fargs, argc_c * sizeof(Value*));
                    newf->fargs = heap_fargs;
                    newf->fargs_n = argc_c;
                    newf->extra = inst; /* val_decref'd on frame completion */
                    frame = newf;
                    goto frame_loop;
                }
            } else {
                fprintf(stderr, "Method not found: %s\n", mname);
                vm_push(vm, val_nil());
            }
            
            for (int i = 0; i < argc_c; i++) val_decref(fargs[i]);
            if (fargs != fargs_buf) free(fargs);
            val_decref(inst);
        }
        case OP_CALL_NEW: {
            int argc_c = arg ? (arg->type == V_INT ? (int)arg->ival : 0) : 0;
            Value *fargs_buf[16];
            Value **fargs;
            if (argc_c <= 16) fargs = fargs_buf;
            else fargs = malloc(argc_c * sizeof(Value*));
            for (int i = argc_c - 1; i >= 0; i--) fargs[i] = vm_pop(vm);
            Value *cls_obj = vm_pop(vm);
            
            if (cls_obj->type == V_CLASS) {
                Value *inst = make_inst(vm, cls_obj);
                Value *init = env_get(cls_obj->cls.methods, "__init__");
                if (init && init->type == V_FUNC) {
                    struct Frame *newf = pool_alloc_frame(vm, FM_INIT, frame);
                    newf->vm->instrs = init->func.instrs; newf->vm->icount = init->func.icount;
                    newf->vm->consts = init->func.consts; newf->vm->ccount = init->func.ccount;
                    newf->vm->pc = 0;
                    env_put(newf->vm->env, "self", val_incref(inst));
                    for (int i = 0; i < init->func.argc && i < argc_c; i++)
                        env_put(newf->vm->env, init->func.args[i], val_incref(fargs[i]));
                    Value **heap_fargs = argc_c > 0 ? malloc(argc_c * sizeof(Value*)) : NULL;
                    if (heap_fargs) memcpy(heap_fargs, fargs, argc_c * sizeof(Value*));
                    newf->fargs = heap_fargs;
                    newf->fargs_n = argc_c;
                    newf->extra = inst; /* push inst on frame return */
                    val_decref(cls_obj); /* dec early; inst holds ref */
                    frame = newf;
                    goto frame_loop;
                }
                vm_push(vm, inst);
            } else {
                fprintf(stderr, "CALL_NEW on non-class\n");
                vm_push(vm, val_nil());
            }
            
            for (int i = 0; i < argc_c; i++) val_decref(fargs[i]);
            if (fargs != fargs_buf) free(fargs);
            val_decref(cls_obj);
        }
        case OP_CALL_VALUE: {
            int argc_c = arg ? (arg->type == V_INT ? (int)arg->ival : 0) : 0;
            Value *fargs_buf[16];
            Value **fargs;
            if (argc_c <= 16) fargs = fargs_buf;
            else fargs = malloc(argc_c * sizeof(Value*));
            for (int i = argc_c - 1; i >= 0; i--) fargs[i] = vm_pop(vm);
            Value *func = vm_pop(vm);
            
            if (func->type == V_FUNC) {
                struct Frame *newf = pool_alloc_frame(vm, FM_FUNC, frame);
                newf->vm->instrs = func->func.instrs; newf->vm->icount = func->func.icount;
                newf->vm->consts = func->func.consts; newf->vm->ccount = func->func.ccount;
                newf->vm->pc = 0;
                for (int i = 0; i < func->func.argc && i < argc_c; i++)
                    env_put(newf->vm->env, func->func.args[i], val_incref(fargs[i]));
                Value **heap_fargs = argc_c > 0 ? malloc(argc_c * sizeof(Value*)) : NULL;
                if (heap_fargs) memcpy(heap_fargs, fargs, argc_c * sizeof(Value*));
                newf->fargs = heap_fargs;
                newf->fargs_n = argc_c;
                val_decref(func); /* dec early; frame manages fargs */
                frame = newf;
                goto frame_loop;
            } else {
                fprintf(stderr, "CALL_VALUE on non-callable\n");
                vm_push(vm, val_nil());
            }
            
            for (int i = 0; i < argc_c; i++) val_decref(fargs[i]);
            if (fargs != fargs_buf) free(fargs);
            val_decref(func);
        }
        case OP_CALL_SUPER: {
            if (!arg || arg->type != V_LIST || arg->list.len < 2) continue;
            Value *name_v = arg->list.items[0];
            Value *argc_v = arg->list.items[1];
            char *mname = (name_v && name_v->type == V_STR) ? name_v->sval : "";
            int argc_c = (argc_v && argc_v->type == V_INT) ? (int)argc_v->ival : 0;
            
            Value *fargs_buf[16];
            Value **fargs;
            if (argc_c <= 16) fargs = fargs_buf;
            else fargs = malloc(argc_c * sizeof(Value*));
            for (int i = argc_c - 1; i >= 0; i--) fargs[i] = vm_pop(vm);
            
            Value *self = env_get(vm->env, "self");
            if (!self || self->type != V_INST) {
                fprintf(stderr, "super() only in method\n");
                for (int i = 0; i < argc_c; i++) val_decref(fargs[i]);
                if (fargs != fargs_buf) free(fargs);
                vm_push(vm, val_nil());
                continue;
            }
            Value *klass = self->instance.klass;
            Value *base = klass ? klass->cls.base : NULL;
            if (!base || base->type != V_CLASS) {
                fprintf(stderr, "No base class\n");
                for (int i = 0; i < argc_c; i++) val_decref(fargs[i]);
                if (fargs != fargs_buf) free(fargs);
                vm_push(vm, val_nil());
                continue;
            }
            Value *method = env_get(base->cls.methods, mname);
            if (method && method->type == V_FUNC) {
                struct Frame *newf = pool_alloc_frame(vm, FM_SUPER, frame);
                newf->vm->instrs = method->func.instrs; newf->vm->icount = method->func.icount;
                newf->vm->consts = method->func.consts; newf->vm->ccount = method->func.ccount;
                newf->vm->pc = 0;
                env_put(newf->vm->env, "self", val_incref(self));
                for (int i = 0; i < method->func.argc; i++)
                    env_put(newf->vm->env, method->func.args[i], val_incref(fargs[i]));
                Value **heap_fargs = argc_c > 0 ? malloc(argc_c * sizeof(Value*)) : NULL;
                if (heap_fargs) memcpy(heap_fargs, fargs, argc_c * sizeof(Value*));
                newf->fargs = heap_fargs;
                newf->fargs_n = argc_c;
                frame = newf;
                goto frame_loop;
            } else {
                fprintf(stderr, "Super method not found: %s\n", mname);
                vm_push(vm, val_nil());
            }
            for (int i = 0; i < argc_c; i++) val_decref(fargs[i]);
            if (fargs != fargs_buf) free(fargs);
        }
        case OP_INSTANCEOF: {
            if (!arg || arg->type != V_STR) { vm_pop(vm); vm_push(vm, val_bool(false)); continue; }
            Value *obj = vm_pop(vm);
            bool result = false;
            if (obj->type == V_INST) {
                Value *klass = obj->instance.klass;
                if (klass && klass->type == V_CLASS && klass->cls.name && strcmp(klass->cls.name, arg->sval) == 0)
                    result = true;
            }
            vm_push(vm, val_bool(result));
            val_decref(obj);
        }
        case OP_DEREF: { /* pointer deref: pass through */ }
        case OP_CAST: { /* cast: pass through */ }
        case OP_MAKE_MODULE: { /* module: store name */ }
        case OP_ASM: { /* asm: ignore */ }
        case OP_FOR_ITER: {
            /* FOR_ITER uses a special iterator constant; handled as no-op in simple cases */
            int target = arg ? (arg->type == V_INT ? (int)arg->ival : 0) : 0;
            vm->pc = target;
        }
        case OP_CONTINUE: { /* handled by compiler backpatching */ }
        case OP_BREAK: {
            /* BREAK: scan forward past the next backward JUMP */
            int i = vm->pc + 1;
            while (i < vm->icount) {
                int op_c = opcode_from_str(vm->instrs[i].op);
                Value *a = vm->instrs[i].arg;
                if (op_c == OP_JUMP && a && a->type == V_INT && (int)a->ival < i) {
                    vm->pc = i + 1;
                    break;
                }
                i++;
            }
            if (i >= vm->icount) vm->pc = vm->icount;
        }
        case OP_IMPORT_NAME: { }
        case OP_IMPORT_FILE: {
            if (!arg || arg->type != V_STR) continue;
            /* In bootstrap mode, modules are pre-compiled in bundle.
               .hto source files only need to be loaded if not already present. */
            char *import_path = arg->sval;
            size_t len;
            char *src = read_entire_file(import_path, &len);
            if (!src) { continue; }
            /* Check if this is .hto source (starts with '#', 'fn', etc) or .hbc bytecode (starts with '{') */
            if (len > 0 && src[0] != '{') {
                /* .hto source file — skip in bootstrap, module already loaded from bundle */
                free(src);
                continue;
            }
            /* .hbc bytecode file — parse and execute */
            JP jp = { .data = src, .pos = 0, .len = (int)len };
            Value *mod = jp_parse(&jp);
            free(src);
            if (!mod || mod->type != V_DICT) { val_decref(mod); continue; }
            Value *instrs_v = dict_get(mod, val_str("instructions"));
            Value *consts_v = dict_get(mod, val_str("consts"));
            if (instrs_v) {
                Value *parsed_instrs = parse_bc_instr(instrs_v);
                Value *parsed_consts = parse_bc_consts(consts_v);
                struct Frame *newf = pool_alloc_frame(vm, FM_IMPORT, frame);
                if (parsed_instrs) { newf->vm->instrs = parsed_instrs->func.instrs; newf->vm->icount = parsed_instrs->func.icount; parsed_instrs->func.instrs = NULL; parsed_instrs->func.icount = 0; val_decref(parsed_instrs); }
                if (parsed_consts) { newf->vm->consts = calloc(parsed_consts->list.len, sizeof(Value*)); newf->vm->ccount = parsed_consts->list.len; for (int i = 0; i < newf->vm->ccount; i++) newf->vm->consts[i] = val_incref(parsed_consts->list.items[i]); val_decref(parsed_consts); }
                newf->vm->pc = 0;
                newf->extra = mod; /* val_decref on frame completion */
                frame = newf;
                goto frame_loop;
            }
            val_decref(mod);
            break;
        }
        default:
            fprintf(stderr, "Unknown opcode: %d\n", op);
            break;
        }
    }
    
    /* End of instructions, no explicit HALT/RETURN — treat as HALT */
    frame->ret_val = NULL;
    
frame_done:;
    {
        struct Frame *old = frame;
        frame = old->parent;
    
        
        if (frame) {
            switch (old->mode) {
            case FM_FUNC: case FM_SUPER:
                vm_push(frame->vm, old->ret_val ? val_incref(old->ret_val) : val_nil());
                break;
            case FM_METHOD:
                vm_push(frame->vm, old->ret_val ? val_incref(old->ret_val) : val_nil());
                if (old->extra) val_decref(old->extra);
                break;
            case FM_INIT:
                if (old->extra) { vm_push(frame->vm, old->extra); old->extra = NULL; }
                break;
            case FM_IMPORT:
                if (old->vm->instrs) {
                    for (int i = 0; i < old->vm->icount; i++) { free(old->vm->instrs[i].op); val_decref(old->vm->instrs[i].arg); }
                    free(old->vm->instrs);
                    old->vm->instrs = NULL;
                }
                if (old->vm->consts) {
                    for (int i = 0; i < old->vm->ccount; i++) val_decref(old->vm->consts[i]);
                    free(old->vm->consts);
                    old->vm->consts = NULL;
                }
                if (old->extra) { val_decref(old->extra); old->extra = NULL; }
                break;
            case FM_TOP:
                break;
            }
            pool_free(old);
            goto frame_loop;
        } else {
            /* Top-level frame completed */
            Value *saved_ret = old->ret_val;
            if (ret_out) { *ret_out = saved_ret; old->ret_val = NULL; }
            if (has_ret) *has_ret = (saved_ret != NULL);
            frame_free(old);
            return;
        }
    }
}

/* ═══════════════════════════════════════════════════════════════
 *  TOP-LEVEL: LOAD AND EXECUTE BYTECODE BUNDLE
 * ═══════════════════════════════════════════════════════════════ */

int main(int argc, char **argv) {
    pool_init();
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <bundle.hbc> [module_name] [function_name] [args...]\n", argv[0]);
        fprintf(stderr, "       %s <bundle.hbc>            -- run all modules\n", argv[0]);
        return 1;
    }
    
    size_t len;
    char *src = read_entire_file(argv[1], &len);
    if (!src) { fprintf(stderr, "Cannot read bundle: %s\n", argv[1]); return 1; }
    
    JP jp = { .data = src, .pos = 0, .len = (int)len };
    Value *bundle = jp_parse(&jp);
    free(src);
    
    if (!bundle || bundle->type != V_DICT) {
        fprintf(stderr, "Invalid bundle format\n");
        return 1;
    }
    
    VM *vm = vm_new(NULL);
    vm_register_builtins(vm);
    g_main_vm = vm;
    dzzw_set_executor(dzzw_executor);
    dzzw_set_worker_cleanup(dzzw_cleanup_worker_vm);
    dzzw_init(0);
    
    Value *modules = dict_get(bundle, val_str("modules"));
    if (!modules || modules->type != V_DICT) {
        fprintf(stderr, "No modules in bundle\n");
        val_decref(bundle);
        return 1;
    }
    
    /* Execute each module in order */
    for (int i = 0; i < modules->dict.len; i++) {
        Value *mod_name = modules->dict.keys[i];
        Value *mod_data = modules->dict.vals[i];
        if (!mod_data || mod_data->type != V_DICT) continue;
        
        Value *instrs_v = dict_get(mod_data, val_str("instructions"));
        Value *consts_v = dict_get(mod_data, val_str("consts"));
        
        if (!instrs_v) continue;
        
        Value *parsed_instrs = parse_bc_instr(instrs_v);
        Value *parsed_consts = parse_bc_consts(consts_v);
        
        VM *mod_vm = vm_new(vm);
        if (parsed_instrs) {
            mod_vm->instrs = parsed_instrs->func.instrs;
            mod_vm->icount = parsed_instrs->func.icount;
            parsed_instrs->func.instrs = NULL;
            parsed_instrs->func.icount = 0;
            val_decref(parsed_instrs);
        }
        if (parsed_consts) {
            mod_vm->consts = calloc(parsed_consts->list.len, sizeof(Value*));
            mod_vm->ccount = parsed_consts->list.len;
            for (int i = 0; i < mod_vm->ccount; i++)
                mod_vm->consts[i] = val_incref(parsed_consts->list.items[i]);
            val_decref(parsed_consts);
        }
        mod_vm->pc = 0;
        
        Value *ret = NULL; bool has_ret = false;
        vm_execute_func(mod_vm, &ret, &has_ret);
        if (ret) val_decref(ret);
        
        /* Merge module env into parent VM so later modules can access defined functions */
        {
            EnvNode *n = mod_vm->env;
            while (n) {
                if (n->name) env_put(vm->env, n->name, val_incref(n->value));
                n = n->next;
            }
        }
        
        /* Cleanup VM but keep env bindings for later modules */
        while (mod_vm->len > 0) val_decref(vm_pop(mod_vm));
        if (mod_vm->instrs) {
            for (int j = 0; j < mod_vm->icount; j++) { free(mod_vm->instrs[j].op); val_decref(mod_vm->instrs[j].arg); }
            free(mod_vm->instrs);
        }
        if (mod_vm->consts) {
            for (int j = 0; j < mod_vm->ccount; j++) val_decref(mod_vm->consts[j]);
            free(mod_vm->consts);
        }
        free(mod_vm->items); free(mod_vm->exc_handlers); free(mod_vm);
    }
    
    /* If a specific function was requested, call it */
    if (argc >= 4) {
        char *mod_name = argv[2];
        char *func_name = argv[3];
        Value *func = vm_lookup(vm, func_name);
        if (func && func->type == V_FUNC) {
            Value **fargs = calloc(argc - 4, sizeof(Value*));
            for (int i = 4; i < argc; i++) fargs[i - 4] = val_str(argv[i]);
            
            VM *call_vm = vm_new(vm);
            call_vm->instrs = func->func.instrs;
            call_vm->icount = func->func.icount;
            call_vm->consts = func->func.consts;
            call_vm->ccount = func->func.ccount;
            call_vm->pc = 0;
            for (int i = 0; i < func->func.argc && i < argc - 4; i++)
                env_put(call_vm->env, func->func.args[i], val_incref(fargs[i]));
            
            Value *ret = NULL; bool has_ret = false;
            vm_execute_func(call_vm, &ret, &has_ret);
            if (ret) {
                if (ret->type == V_STR) printf("%s\n", ret->sval);
                else if (ret->type == V_INT) printf("%lld\n", (long long)ret->ival);
                else if (ret->type == V_FLOAT) printf("%.15g\n", ret->fval);
                else if (ret->type == V_BOOL) printf(ret->bval ? "true\n" : "false\n");
                else if (ret->type == V_NIL) printf("nil\n");
                else printf("<%s>\n", val_type_name(ret->type));
                val_decref(ret);
            }
            
            while (call_vm->len > 0) val_decref(vm_pop(call_vm));
            free(call_vm->items); free(call_vm->exc_handlers); free(call_vm);
            for (int i = 0; i < argc - 4; i++) val_decref(fargs[i]);
            free(fargs);
        } else {
            fprintf(stderr, "Function not found: %s\n", func_name);
        }
    }
    
    dzzw_shutdown();
    printf("Done.\n");
    val_decref(bundle);
    return 0;
}