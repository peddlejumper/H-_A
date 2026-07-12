/* ═══════════════════════════════════════════════════════════════
 *  DZZW — Parallel Multi-Tasking Runtime for H# (implementation)
 *  Thread pool, futures, channels, mutex, work-stealing queue
 * ═══════════════════════════════════════════════════════════════ */

#include "dzzw.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <unistd.h>

/* ═══════════════════════════════════════════════════════════════
 *  GLOBAL POOL STATE
 * ═══════════════════════════════════════════════════════════════ */

static DZZW_Pool *g_pool = NULL;

/* Executor callback — set by hsvm.c to execute H# functions */
static DZZW_ExecutorFn g_executor = NULL;

void dzzw_set_executor(DZZW_ExecutorFn exec) {
    g_executor = exec;
}

/* ═══════════════════════════════════════════════════════════════
 *  FUTURE
 * ═══════════════════════════════════════════════════════════════ */

DZZW_Future *dzzw_future_new(void) {
    DZZW_Future *f = calloc(1, sizeof(DZZW_Future));
    f->state = DZZW_PENDING;
    f->refcount = 1;
    pthread_mutex_init(&f->mu, NULL);
    pthread_cond_init(&f->cv, NULL);
    return f;
}

void dzzw_future_set(DZZW_Future *f, Value *v) {
    pthread_mutex_lock(&f->mu);
    f->result = v;
    f->state = DZZW_DONE;
    pthread_cond_broadcast(&f->cv);
    pthread_mutex_unlock(&f->mu);
}

void dzzw_future_set_error(DZZW_Future *f, Value *v) {
    pthread_mutex_lock(&f->mu);
    f->result = v;
    f->state = DZZW_ERROR;
    pthread_cond_broadcast(&f->cv);
    pthread_mutex_unlock(&f->mu);
}

Value *dzzw_future_wait(DZZW_Future *f) {
    pthread_mutex_lock(&f->mu);
    while (f->state == DZZW_PENDING || f->state == DZZW_RUNNING) {
        pthread_cond_wait(&f->cv, &f->mu);
    }
    Value *result = f->result;
    pthread_mutex_unlock(&f->mu);
    return result;
}

void dzzw_future_free(DZZW_Future *f) {
    if (!f) return;
    pthread_mutex_destroy(&f->mu);
    pthread_cond_destroy(&f->cv);
    free(f);
}

/* ═══════════════════════════════════════════════════════════════
 *  CHANNEL
 * ═══════════════════════════════════════════════════════════════ */

DZZW_Channel *dzzw_channel_new(int capacity) {
    DZZW_Channel *ch = calloc(1, sizeof(DZZW_Channel));
    ch->cap = capacity > 0 ? capacity : 64;
    ch->buf = calloc(ch->cap, sizeof(Value*));
    ch->head = 0;
    ch->tail = 0;
    ch->count = 0;
    pthread_mutex_init(&ch->mu, NULL);
    pthread_cond_init(&ch->not_empty, NULL);
    pthread_cond_init(&ch->not_full, NULL);
    return ch;
}

void dzzw_channel_send(DZZW_Channel *ch, Value *v) {
    pthread_mutex_lock(&ch->mu);
    while (ch->count >= ch->cap) {
        pthread_cond_wait(&ch->not_full, &ch->mu);
    }
    ch->buf[ch->tail] = v;
    ch->tail = (ch->tail + 1) % ch->cap;
    ch->count++;
    pthread_cond_signal(&ch->not_empty);
    pthread_mutex_unlock(&ch->mu);
}

Value *dzzw_channel_recv(DZZW_Channel *ch) {
    pthread_mutex_lock(&ch->mu);
    while (ch->count <= 0) {
        pthread_cond_wait(&ch->not_empty, &ch->mu);
    }
    Value *v = ch->buf[ch->head];
    ch->head = (ch->head + 1) % ch->cap;
    ch->count--;
    pthread_cond_signal(&ch->not_full);
    pthread_mutex_unlock(&ch->mu);
    return v;
}

void dzzw_channel_free(DZZW_Channel *ch) {
    if (!ch) return;
    pthread_mutex_destroy(&ch->mu);
    pthread_cond_destroy(&ch->not_empty);
    pthread_cond_destroy(&ch->not_full);
    free(ch->buf);
    free(ch);
}

/* ═══════════════════════════════════════════════════════════════
 *  MUTEX
 * ═══════════════════════════════════════════════════════════════ */

DZZW_Mutex *dzzw_mutex_new(void) {
    DZZW_Mutex *m = calloc(1, sizeof(DZZW_Mutex));
    pthread_mutex_init(&m->mu, NULL);
    return m;
}

void dzzw_mutex_lock(DZZW_Mutex *m) {
    pthread_mutex_lock(&m->mu);
}

void dzzw_mutex_unlock(DZZW_Mutex *m) {
    pthread_mutex_unlock(&m->mu);
}

void dzzw_mutex_free(DZZW_Mutex *m) {
    if (!m) return;
    pthread_mutex_destroy(&m->mu);
    free(m);
}

/* ═══════════════════════════════════════════════════════════════
 *  THREAD POOL — WORKER LOOP
 * ═══════════════════════════════════════════════════════════════ */

void dzzw_enqueue(DZZW_Task *task) {
    pthread_mutex_lock(&g_pool->queue_mu);
    task->next = NULL;
    if (g_pool->queue_tail) {
        g_pool->queue_tail->next = task;
    } else {
        g_pool->queue_head = task;
    }
    g_pool->queue_tail = task;
    g_pool->queue_len++;
    atomic_fetch_add(&g_pool->pending_count, 1);
    pthread_cond_signal(&g_pool->queue_cv);
    pthread_mutex_unlock(&g_pool->queue_mu);
}

static DZZW_Task *dzzw_dequeue_task(void) {
    pthread_mutex_lock(&g_pool->queue_mu);
    while (g_pool->queue_len == 0 && g_pool->running) {
        pthread_cond_wait(&g_pool->queue_cv, &g_pool->queue_mu);
    }
    if (!g_pool->running && g_pool->queue_len == 0) {
        pthread_mutex_unlock(&g_pool->queue_mu);
        return NULL;
    }
    DZZW_Task *task = g_pool->queue_head;
    g_pool->queue_head = task->next;
    if (!g_pool->queue_head) g_pool->queue_tail = NULL;
    g_pool->queue_len--;
    pthread_mutex_unlock(&g_pool->queue_mu);
    return task;
}

static void *dzzw_worker_loop(void *arg) {
    (void)arg;
    
    while (1) {
        DZZW_Task *task = dzzw_dequeue_task();
        if (!task) break;
        
        if (task->future) {
            task->future->state = DZZW_RUNNING;
        }
        
        if (g_executor && task->fn) {
            g_executor(task->fn, task->args, task->argc, task->future);
        } else if (task->future) {
            dzzw_future_set_error(task->future, (Value*)1);
        }
        
        atomic_fetch_sub(&g_pool->pending_count, 1);
        
        free(task->args);
        free(task);
    }
    
    return NULL;
}

/* ═══════════════════════════════════════════════════════════════
 *  PUBLIC API
 * ═══════════════════════════════════════════════════════════════ */

void dzzw_init(int num_workers) {
    if (g_pool) return;
    if (num_workers <= 0) {
        num_workers = (int)sysconf(_SC_NPROCESSORS_ONLN);
        if (num_workers <= 0) num_workers = 4;
    }
    
    g_pool = calloc(1, sizeof(DZZW_Pool));
    g_pool->num_workers = num_workers;
    g_pool->running = true;
    g_pool->pending_count = 0;
    g_pool->queue_head = NULL;
    g_pool->queue_tail = NULL;
    g_pool->queue_len = 0;
    pthread_mutex_init(&g_pool->queue_mu, NULL);
    pthread_cond_init(&g_pool->queue_cv, NULL);
    
    g_pool->workers = calloc(num_workers, sizeof(pthread_t));
    
    for (int i = 0; i < num_workers; i++) {
        pthread_create(&g_pool->workers[i], NULL, dzzw_worker_loop, NULL);
    }
    
    fprintf(stderr, "[DZZW] Thread pool started: %d workers\n", num_workers);
}

void dzzw_shutdown(void) {
    if (!g_pool) return;
    
    /* Wait for all pending tasks to complete */
    while (atomic_load(&g_pool->pending_count) > 0) {
        usleep(1000);
    }
    
    /* Signal workers to stop */
    g_pool->running = false;
    pthread_mutex_lock(&g_pool->queue_mu);
    pthread_cond_broadcast(&g_pool->queue_cv);
    pthread_mutex_unlock(&g_pool->queue_mu);
    
    /* Join workers */
    for (int i = 0; i < g_pool->num_workers; i++) {
        pthread_join(g_pool->workers[i], NULL);
    }
    
    fprintf(stderr, "[DZZW] Thread pool shut down\n");
    
    pthread_mutex_destroy(&g_pool->queue_mu);
    pthread_cond_destroy(&g_pool->queue_cv);
    free(g_pool->workers);
    free(g_pool);
    g_pool = NULL;
}

DZZW_Future *dzzw_spawn(Value *fn, Value **args, int argc) {
    if (!g_pool || !g_pool->running) return NULL;
    
    DZZW_Future *fut = dzzw_future_new();
    
    DZZW_Task *task = calloc(1, sizeof(DZZW_Task));
    task->fn = fn;
    task->argc = argc;
    task->args = calloc(argc, sizeof(Value*));
    for (int i = 0; i < argc; i++) task->args[i] = args[i];
    task->future = fut;
    
    dzzw_enqueue(task);
    return fut;
}

Value *dzzw_await(DZZW_Future *f) {
    if (!f) return NULL;
    return dzzw_future_wait(f);
}

int dzzw_worker_count(void) {
    return g_pool ? g_pool->num_workers : 0;
}

int dzzw_pending_count(void) {
    return g_pool ? atomic_load(&g_pool->pending_count) : 0;
}