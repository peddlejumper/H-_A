/* ═══════════════════════════════════════════════════════════════
 *  DZZW — Parallel Multi-Tasking Runtime for H#  v2.0
 *  Work-stealing thread pool, VM reuse, memory pooling,
 *  futures, channels, mutex, parallel-for/reduce, continuations
 * ═══════════════════════════════════════════════════════════════ */

#include "dzzw.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <unistd.h>
#include <time.h>

/* ═══════════════════════════════════════════════════════════════
 *  GLOBAL POOL STATE
 * ═══════════════════════════════════════════════════════════════ */

static DZZW_Pool *g_pool = NULL;
static DZZW_ExecutorFn g_executor = NULL;
static void (*g_worker_cleanup)(DZZW_Worker *) = NULL;

void dzzw_set_executor(DZZW_ExecutorFn exec) {
    g_executor = exec;
}

void dzzw_set_worker_cleanup(void (*fn)(DZZW_Worker *)) {
    g_worker_cleanup = fn;
}

/* ═══════════════════════════════════════════════════════════════
 *  MEMORY POOL — Task & Future object pools
 * ═══════════════════════════════════════════════════════════════ */

static DZZW_Task *pool_alloc_task(void) {
    pthread_mutex_lock(&g_pool->task_pool_mu);
    DZZW_Task *t = NULL;
    if (g_pool->task_pool_count > 0) {
        t = g_pool->task_pool;
        g_pool->task_pool = t->next;
        g_pool->task_pool_count--;
        t->next = NULL;
    }
    pthread_mutex_unlock(&g_pool->task_pool_mu);
    
    if (!t) {
        t = calloc(1, sizeof(DZZW_Task));
    }
    return t;
}

static void pool_free_task(DZZW_Task *t) {
    if (!t) return;
    pthread_mutex_lock(&g_pool->task_pool_mu);
    if (g_pool->task_pool_count < DZZW_MEMPOOL_TASK_SIZE) {
        memset(t, 0, sizeof(DZZW_Task));
        t->next = g_pool->task_pool;
        g_pool->task_pool = t;
        g_pool->task_pool_count++;
        pthread_mutex_unlock(&g_pool->task_pool_mu);
        return;
    }
    pthread_mutex_unlock(&g_pool->task_pool_mu);
    free(t);
}

static DZZW_Future *pool_alloc_future(void) {
    pthread_mutex_lock(&g_pool->future_pool_mu);
    DZZW_Future *f = NULL;
    if (g_pool->future_pool_count > 0) {
        f = g_pool->future_pool;
        /* Futures are singly linked in the pool */
        f = g_pool->future_pool;
        g_pool->future_pool = NULL; /* we pop one */
        g_pool->future_pool_count--;
        /* Initialize the fresh future */
        f->state = DZZW_PENDING;
        f->result = NULL;
        f->refcount = 1;
    }
    pthread_mutex_unlock(&g_pool->future_pool_mu);
    
    if (!f) {
        f = dzzw_future_new();
    }
    return f;
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

Value *dzzw_future_try_wait(DZZW_Future *f) {
    pthread_mutex_lock(&f->mu);
    if (f->state == DZZW_PENDING || f->state == DZZW_RUNNING) {
        pthread_mutex_unlock(&f->mu);
        return NULL;
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

void dzzw_mutex_lock(DZZW_Mutex *m) { pthread_mutex_lock(&m->mu); }
void dzzw_mutex_unlock(DZZW_Mutex *m) { pthread_mutex_unlock(&m->mu); }
void dzzw_mutex_free(DZZW_Mutex *m) {
    if (!m) return;
    pthread_mutex_destroy(&m->mu);
    free(m);
}

/* ═══════════════════════════════════════════════════════════════
 *  WORK-STEALING QUEUE — Local Bounded Ring Buffer
 * ═══════════════════════════════════════════════════════════════ */

/* Push a task to the worker's local queue (called by owning thread) */
static bool local_queue_push(DZZW_Worker *w, DZZW_Task *task) {
    int head = atomic_load(&w->local_head);
    int tail = atomic_load(&w->local_tail);
    
    /* Check if full */
    if (head - tail >= DZZW_LOCAL_QUEUE_SIZE) {
        return false;
    }
    
    w->local_queue[head % DZZW_LOCAL_QUEUE_SIZE] = task;
    atomic_store(&w->local_head, head + 1);
    return true;
}

/* Pop a task from the worker's local queue (called by owning thread) */
static DZZW_Task *local_queue_pop(DZZW_Worker *w) {
    int tail = atomic_load(&w->local_tail);
    int head = atomic_load(&w->local_head);
    
    if (head <= tail) return NULL;
    
    head--;
    atomic_store(&w->local_head, head);
    
    /* Memory fence: ensure task is visible before checking */
    atomic_thread_fence(memory_order_seq_cst);
    
    DZZW_Task *task = w->local_queue[head % DZZW_LOCAL_QUEUE_SIZE];
    
    /* CAS to claim the task */
    if (head > tail) {
        return task;
    }
    
    /* Race with stealer — put it back if we lost */
    atomic_store(&w->local_head, head + 1);
    return NULL;
}

/* Steal a task from another worker's queue (called by thief) */
static DZZW_Task *local_queue_steal(DZZW_Worker *w) {
    int tail = atomic_load(&w->local_tail);
    atomic_thread_fence(memory_order_acquire);
    int head = atomic_load(&w->local_head);
    
    if (head <= tail) return NULL;
    
    DZZW_Task *task = w->local_queue[tail % DZZW_LOCAL_QUEUE_SIZE];
    
    /* CAS to claim the task slot */
    if (!atomic_compare_exchange_strong(&w->local_tail, &tail, tail + 1)) {
        return NULL; /* Another thief beat us */
    }
    
    return task;
}

/* ═══════════════════════════════════════════════════════════════
 *  THREAD POOL — GLOBAL QUEUE + ENQUEUE
 * ═══════════════════════════════════════════════════════════════ */

static void global_queue_enqueue(DZZW_Task *task) {
    pthread_mutex_lock(&g_pool->global_queue_mu);
    task->next = NULL;
    if (g_pool->global_queue_tail) {
        g_pool->global_queue_tail->next = task;
    } else {
        g_pool->global_queue_head = task;
    }
    g_pool->global_queue_tail = task;
    g_pool->global_queue_len++;
    pthread_cond_signal(&g_pool->global_queue_cv);
    pthread_mutex_unlock(&g_pool->global_queue_mu);
}

static DZZW_Task *global_queue_dequeue(void) {
    pthread_mutex_lock(&g_pool->global_queue_mu);
    while (g_pool->global_queue_len == 0 && g_pool->running) {
        pthread_cond_wait(&g_pool->global_queue_cv, &g_pool->global_queue_mu);
    }
    if (!g_pool->running && g_pool->global_queue_len == 0) {
        pthread_mutex_unlock(&g_pool->global_queue_mu);
        return NULL;
    }
    DZZW_Task *task = g_pool->global_queue_head;
    if (task) {
        g_pool->global_queue_head = task->next;
        if (!g_pool->global_queue_head) g_pool->global_queue_tail = NULL;
        g_pool->global_queue_len--;
    }
    pthread_mutex_unlock(&g_pool->global_queue_mu);
    return task;
}

void dzzw_enqueue(DZZW_Task *task) {
    atomic_fetch_add(&g_pool->pending_count, 1);
    atomic_fetch_add(&g_pool->total_tasks_submitted, 1);
    
    /* Try to push to a random worker's local queue (avoids global lock) */
    static _Thread_local int rr_counter = 0;
    int wid = rr_counter % g_pool->num_workers;
    rr_counter++;
    
    if (local_queue_push(&g_pool->workers[wid], task)) {
        pthread_cond_signal(&g_pool->global_queue_cv);
        return;
    }
    
    /* Local queue full — fall through to global queue */
    global_queue_enqueue(task);
}

void dzzw_enqueue_batch(DZZW_Task **tasks, int n) {
    atomic_fetch_add(&g_pool->pending_count, n);
    atomic_fetch_add(&g_pool->total_tasks_submitted, n);
    
    /* Try local push first — distribute round-robin */
    static _Thread_local int bb_counter = 0;
    for (int i = 0; i < n; i++) {
        int wid = (bb_counter + i) % g_pool->num_workers;
        if (local_queue_push(&g_pool->workers[wid], tasks[i])) {
            continue;
        }
        /* Fall through to global */
        global_queue_enqueue(tasks[i]);
    }
    bb_counter += n;
    pthread_cond_broadcast(&g_pool->global_queue_cv);
}

/* ═══════════════════════════════════════════════════════════════
 *  WORKER — TASK ACQUISITION LOOP (work-stealing)
 * ═══════════════════════════════════════════════════════════════ */

static DZZW_Task *worker_acquire_task(DZZW_Worker *w) {
    /* 1. Try local queue */
    DZZW_Task *task = local_queue_pop(w);
    if (task) return task;
    
    /* 2. Try global queue (non-blocking poll first) */
    pthread_mutex_lock(&g_pool->global_queue_mu);
    if (g_pool->global_queue_len > 0) {
        task = g_pool->global_queue_head;
        g_pool->global_queue_head = task->next;
        if (!g_pool->global_queue_head) g_pool->global_queue_tail = NULL;
        g_pool->global_queue_len--;
        pthread_mutex_unlock(&g_pool->global_queue_mu);
        return task;
    }
    pthread_mutex_unlock(&g_pool->global_queue_mu);
    
    /* 3. Steal from a random victim */
    int n = g_pool->num_workers;
    int start = (w->id + 1) % n;
    for (int i = 0; i < n; i++) {
        int victim = (start + i) % n;
        if (victim == w->id) continue;
        DZZW_Task *stolen = local_queue_steal(&g_pool->workers[victim]);
        if (stolen) {
            atomic_fetch_add(&w->steals_success, 1);
            return stolen;
        }
        atomic_fetch_add(&w->steals_failed, 1);
    }
    
    /* 4. Block on global queue */
    pthread_mutex_lock(&g_pool->global_queue_mu);
    while (g_pool->global_queue_len == 0 && g_pool->running) {
        /* Re-check local queue while waiting */
        pthread_mutex_unlock(&g_pool->global_queue_mu);
        
        task = local_queue_pop(w);
        if (task) return task;
        
        /* Try steal again */
        for (int i = 0; i < n; i++) {
            int victim = (start + i) % n;
            if (victim == w->id) continue;
            DZZW_Task *stolen = local_queue_steal(&g_pool->workers[victim]);
            if (stolen) {
                atomic_fetch_add(&w->steals_success, 1);
                return stolen;
            }
        }
        
        /* Small yield before blocking */
        struct timespec ts = {0, 100000}; /* 100us */
        nanosleep(&ts, NULL);
        
        pthread_mutex_lock(&g_pool->global_queue_mu);
        if (g_pool->global_queue_len > 0) break;
        
        /* Check if pool is shutting down */
        if (!g_pool->running) {
            pthread_mutex_unlock(&g_pool->global_queue_mu);
            return NULL;
        }
    }
    
    if (g_pool->global_queue_len > 0) {
        task = g_pool->global_queue_head;
        g_pool->global_queue_head = task->next;
        if (!g_pool->global_queue_head) g_pool->global_queue_tail = NULL;
        g_pool->global_queue_len--;
    }
    pthread_mutex_unlock(&g_pool->global_queue_mu);
    return task;
}

/* ═══════════════════════════════════════════════════════════════
 *  WORKER LOOP
 * ═══════════════════════════════════════════════════════════════ */

static void *dzzw_worker_loop(void *arg) {
    DZZW_Worker *w = (DZZW_Worker *)arg;
    
    while (1) {
        DZZW_Task *task = worker_acquire_task(w);
        if (!task) break;
        
        if (task->future) {
            task->future->state = DZZW_RUNNING;
        }
        
        if (g_executor && task->fn) {
            g_executor(task->fn, task->args, task->argc, task->future, w);
        } else if (task->future) {
            dzzw_future_set_error(task->future, (Value*)1);
        }
        
        atomic_fetch_add(&w->tasks_executed, 1);
        atomic_fetch_sub(&g_pool->pending_count, 1);
        atomic_fetch_add(&g_pool->total_tasks_completed, 1);
        
        /* Free task args (not pooled to avoid complexity) */
        if (task->args) free(task->args);
        
        /* Return task to pool */
        pool_free_task(task);
    }
    
    return NULL;
}

/* ═══════════════════════════════════════════════════════════════
 *  INIT / SHUTDOWN
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
    g_pool->allow_blocking_enqueue = true;
    
    /* Global queue */
    g_pool->global_queue_head = NULL;
    g_pool->global_queue_tail = NULL;
    g_pool->global_queue_len = 0;
    pthread_mutex_init(&g_pool->global_queue_mu, NULL);
    pthread_cond_init(&g_pool->global_queue_cv, NULL);
    
    /* Memory pools */
    pthread_mutex_init(&g_pool->task_pool_mu, NULL);
    g_pool->task_pool = NULL;
    g_pool->task_pool_count = 0;
    
    pthread_mutex_init(&g_pool->future_pool_mu, NULL);
    g_pool->future_pool = NULL;
    g_pool->future_pool_count = 0;
    
    /* Workers */
    g_pool->workers = calloc(num_workers, sizeof(DZZW_Worker));
    for (int i = 0; i < num_workers; i++) {
        DZZW_Worker *w = &g_pool->workers[i];
        w->id = i;
        w->vm = NULL;
        w->executor_data = NULL;
        w->local_head = 0;
        w->local_tail = 0;
        w->tasks_executed = 0;
        w->steals_success = 0;
        w->steals_failed = 0;
        pthread_create(&w->thread, NULL, dzzw_worker_loop, w);
    }
    
    fprintf(stderr, "[DZZW v2.0] Work-stealing thread pool: %d workers\n", num_workers);
}

void dzzw_shutdown(void) {
    if (!g_pool) return;
    
    /* Wait for all pending tasks to complete */
    while (atomic_load(&g_pool->pending_count) > 0) {
        usleep(1000);
    }
    
    /* Signal workers to stop */
    g_pool->running = false;
    pthread_mutex_lock(&g_pool->global_queue_mu);
    pthread_cond_broadcast(&g_pool->global_queue_cv);
    pthread_mutex_unlock(&g_pool->global_queue_mu);
    
    /* Join workers */
    for (int i = 0; i < g_pool->num_workers; i++) {
        pthread_join(g_pool->workers[i].thread, NULL);
    }
    
    /* Cleanup per-worker data (e.g., cached VMs) */
    if (g_worker_cleanup) {
        for (int i = 0; i < g_pool->num_workers; i++) {
            g_worker_cleanup(&g_pool->workers[i]);
        }
    }
    
    fprintf(stderr, "[DZZW v2.0] Thread pool shut down\n");
    
    /* Cleanup memory pools */
    pthread_mutex_lock(&g_pool->task_pool_mu);
    DZZW_Task *tp = g_pool->task_pool;
    while (tp) {
        DZZW_Task *next = tp->next;
        free(tp);
        tp = next;
    }
    pthread_mutex_unlock(&g_pool->task_pool_mu);
    
    pthread_mutex_lock(&g_pool->future_pool_mu);
    DZZW_Future *fp = g_pool->future_pool;
    while (fp) {
        DZZW_Future *next = NULL; /* Futures don't chain */
        dzzw_future_free(fp);
        fp = next;
    }
    pthread_mutex_unlock(&g_pool->future_pool_mu);
    
    pthread_mutex_destroy(&g_pool->global_queue_mu);
    pthread_cond_destroy(&g_pool->global_queue_cv);
    pthread_mutex_destroy(&g_pool->task_pool_mu);
    pthread_mutex_destroy(&g_pool->future_pool_mu);
    
    free(g_pool->workers);
    free(g_pool);
    g_pool = NULL;
}

/* ═══════════════════════════════════════════════════════════════
 *  SPAWN
 * ═══════════════════════════════════════════════════════════════ */

DZZW_Future *dzzw_spawn(Value *fn, Value **args, int argc) {
    if (!g_pool || !g_pool->running) return NULL;
    
    DZZW_Future *fut = pool_alloc_future();
    if (!fut) fut = dzzw_future_new();
    
    DZZW_Task *task = pool_alloc_task();
    task->fn = fn;
    task->argc = argc;
    task->args = calloc(argc, sizeof(Value*));
    memcpy(task->args, args, argc * sizeof(Value*));
    task->future = fut;
    
    dzzw_enqueue(task);
    return fut;
}

/* ═══════════════════════════════════════════════════════════════
 *  FUTURE OPERATIONS (v2)
 * ═══════════════════════════════════════════════════════════════ */

Value *dzzw_await(DZZW_Future *f) {
    if (!f) return NULL;
    return dzzw_future_wait(f);
}

int dzzw_await_any(DZZW_Future **futures, int n) {
    /* Poll all futures until one completes */
    while (1) {
        for (int i = 0; i < n; i++) {
            if (!futures[i]) continue;
            pthread_mutex_lock(&futures[i]->mu);
            if (futures[i]->state == DZZW_DONE || futures[i]->state == DZZW_ERROR) {
                pthread_mutex_unlock(&futures[i]->mu);
                return i;
            }
            pthread_mutex_unlock(&futures[i]->mu);
        }
        usleep(100); /* small sleep to avoid busy-looping */
    }
}

void dzzw_await_all(DZZW_Future **futures, int n) {
    for (int i = 0; i < n; i++) {
        if (futures[i]) {
            dzzw_future_wait(futures[i]);
        }
    }
}

void dzzw_then(DZZW_Future *f, void (*callback)(Value *result)) {
    /* Simple implementation: spawn a task that waits and calls callback */
    /* The callback is called synchronously on the waiting thread */
    /* For async, the user should spawn a task that awaits the future */
    Value *result = dzzw_future_wait(f);
    callback(result);
}

/* ═══════════════════════════════════════════════════════════════
 *  HIGH-LEVEL PARALLEL PRIMITIVES
 * ═══════════════════════════════════════════════════════════════ */

/* Internal struct for parallel_for tasks */
typedef struct {
    DZZW_RangeFn  fn;
    void         *userdata;
    int           start;
    int           end;
} DZZW_PF_Data;

static void *dzzw_pf_worker(void *arg) {
    DZZW_PF_Data *data = (DZZW_PF_Data *)arg;
    for (int i = data->start; i < data->end; i++) {
        data->fn(i, data->userdata);
    }
    return NULL;
}

void dzzw_parallel_for(int start, int end, DZZW_RangeFn fn, void *userdata) {
    if (start >= end) return;
    
    int n_workers = g_pool ? g_pool->num_workers : 1;
    int total = end - start;
    int chunk = (total + n_workers - 1) / n_workers;
    if (chunk < 1) chunk = 1;
    
    pthread_t *threads = calloc(n_workers, sizeof(pthread_t));
    DZZW_PF_Data *datas = calloc(n_workers, sizeof(DZZW_PF_Data));
    
    int actual = 0;
    for (int i = 0; i < n_workers; i++) {
        int s = start + i * chunk;
        int e = s + chunk;
        if (s >= end) break;
        if (e > end) e = end;
        
        datas[i].fn = fn;
        datas[i].userdata = userdata;
        datas[i].start = s;
        datas[i].end = e;
        
        pthread_create(&threads[i], NULL, dzzw_pf_worker, &datas[i]);
        actual++;
    }
    
    for (int i = 0; i < actual; i++) {
        pthread_join(threads[i], NULL);
    }
    
    free(threads);
    free(datas);
}

/* Internal struct for parallel_reduce tasks */
typedef struct {
    DZZW_MapFn     map_fn;
    DZZW_ReduceFn  reduce_fn;
    void          *userdata;
    int            start;
    int            end;
    void          *result;
} DZZW_PR_Data;

static void *dzzw_pr_worker(void *arg) {
    DZZW_PR_Data *data = (DZZW_PR_Data *)arg;
    
    /* Map phase */
    void *local = NULL;
    for (int i = data->start; i < data->end; i++) {
        void *mapped = data->map_fn(i, data->userdata);
        if (!local) {
            local = mapped;
        } else {
            local = data->reduce_fn(local, mapped, data->userdata);
        }
    }
    data->result = local;
    return NULL;
}

void *dzzw_parallel_reduce(int start, int end, DZZW_MapFn map_fn,
                           DZZW_ReduceFn reduce_fn, void *userdata,
                           int chunk_size) {
    if (start >= end) return NULL;
    
    int n_workers = g_pool ? g_pool->num_workers : 1;
    int total = end - start;
    
    if (chunk_size <= 0) {
        chunk_size = (total + n_workers - 1) / n_workers;
    }
    if (chunk_size < 1) chunk_size = 1;
    
    int n_chunks = (total + chunk_size - 1) / chunk_size;
    if (n_chunks > n_workers) n_chunks = n_workers;
    
    pthread_t *threads = calloc(n_chunks, sizeof(pthread_t));
    DZZW_PR_Data *datas = calloc(n_chunks, sizeof(DZZW_PR_Data));
    
    int actual = 0;
    for (int i = 0; i < n_chunks; i++) {
        int s = start + i * chunk_size;
        int e = s + chunk_size;
        if (s >= end) break;
        if (e > end) e = end;
        
        datas[i].map_fn = map_fn;
        datas[i].reduce_fn = reduce_fn;
        datas[i].userdata = userdata;
        datas[i].start = s;
        datas[i].end = e;
        datas[i].result = NULL;
        
        pthread_create(&threads[i], NULL, dzzw_pr_worker, &datas[i]);
        actual++;
    }
    
    /* Collect and reduce */
    void *global_result = NULL;
    for (int i = 0; i < actual; i++) {
        pthread_join(threads[i], NULL);
        if (!global_result) {
            global_result = datas[i].result;
        } else if (datas[i].result) {
            global_result = reduce_fn(global_result, datas[i].result, userdata);
        }
    }
    
    free(threads);
    free(datas);
    return global_result;
}

/* ═══════════════════════════════════════════════════════════════
 *  INFO & STATS
 * ═══════════════════════════════════════════════════════════════ */

int dzzw_worker_count(void) {
    return g_pool ? g_pool->num_workers : 0;
}

int dzzw_pending_count(void) {
    return g_pool ? atomic_load(&g_pool->pending_count) : 0;
}

int dzzw_total_completed(void) {
    return g_pool ? atomic_load(&g_pool->total_tasks_completed) : 0;
}

int dzzw_total_submitted(void) {
    return g_pool ? atomic_load(&g_pool->total_tasks_submitted) : 0;
}

void dzzw_dump_stats(void) {
    if (!g_pool) return;
    
    fprintf(stderr, "\n[DZZW v2.0 Stats]\n");
    fprintf(stderr, "  Workers:          %d\n", g_pool->num_workers);
    fprintf(stderr, "  Submitted:        %d\n", atomic_load(&g_pool->total_tasks_submitted));
    fprintf(stderr, "  Completed:        %d\n", atomic_load(&g_pool->total_tasks_completed));
    fprintf(stderr, "  Pending:          %d\n", atomic_load(&g_pool->pending_count));
    fprintf(stderr, "  Global queue:     %d\n", g_pool->global_queue_len);
    fprintf(stderr, "  Task pool:        %d\n", g_pool->task_pool_count);
    
    for (int i = 0; i < g_pool->num_workers; i++) {
        DZZW_Worker *w = &g_pool->workers[i];
        int local_len = atomic_load(&w->local_head) - atomic_load(&w->local_tail);
        fprintf(stderr, "  Worker %d: executed=%d steals_ok=%d steals_fail=%d local_q=%d\n",
                i, atomic_load(&w->tasks_executed),
                atomic_load(&w->steals_success),
                atomic_load(&w->steals_failed), local_len);
    }
    fprintf(stderr, "\n");
}

void dzzw_set_blocking_enqueue(bool block) {
    if (g_pool) g_pool->allow_blocking_enqueue = block;
}