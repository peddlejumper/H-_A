/* ═══════════════════════════════════════════════════════════════
 *  DZZW — Parallel Multi-Tasking Runtime for H#
 *  Thread pool, futures, channels, mutex — zero external deps
 * ═══════════════════════════════════════════════════════════════ */

#ifndef DZZW_H
#define DZZW_H

#include <pthread.h>
#include <stdatomic.h>

/* Forward declaration of Value from hsvm.c */
typedef struct Value Value;

/* ═══════════════════════════════════════════════════════════════
 *  FUTURE — awaitable task result
 * ═══════════════════════════════════════════════════════════════ */

typedef enum { DZZW_PENDING, DZZW_RUNNING, DZZW_DONE, DZZW_ERROR } DZZW_FutureState;

typedef struct DZZW_Future {
    DZZW_FutureState state;
    Value *result;
    pthread_mutex_t mu;
    pthread_cond_t  cv;
    int refcount;
} DZZW_Future;

DZZW_Future *dzzw_future_new(void);
void dzzw_future_set(DZZW_Future *f, Value *v);
void dzzw_future_set_error(DZZW_Future *f, Value *v);
Value *dzzw_future_wait(DZZW_Future *f);
void dzzw_future_free(DZZW_Future *f);

/* ═══════════════════════════════════════════════════════════════
 *  TASK — a unit of work (function + arguments)
 * ═══════════════════════════════════════════════════════════════ */

typedef struct DZZW_Task {
    Value *fn;
    Value **args;
    int argc;
    DZZW_Future *future;
    struct DZZW_Task *next;
} DZZW_Task;

/* ═══════════════════════════════════════════════════════════════
 *  CHANNEL — bounded communication channel between tasks
 * ═══════════════════════════════════════════════════════════════ */

typedef struct DZZW_Channel {
    Value **buf;
    int cap;
    int head;
    int tail;
    int count;
    pthread_mutex_t mu;
    pthread_cond_t not_empty;
    pthread_cond_t not_full;
} DZZW_Channel;

DZZW_Channel *dzzw_channel_new(int capacity);
void dzzw_channel_send(DZZW_Channel *ch, Value *v);
Value *dzzw_channel_recv(DZZW_Channel *ch);
void dzzw_channel_free(DZZW_Channel *ch);

/* ═══════════════════════════════════════════════════════════════
 *  EXECUTOR — callback type for worker threads to execute H# code
 * ═══════════════════════════════════════════════════════════════ */

typedef void (*DZZW_ExecutorFn)(struct Value *fn, struct Value **args, int argc, DZZW_Future *fut);
void dzzw_set_executor(DZZW_ExecutorFn exec);

/* ═══════════════════════════════════════════════════════════════
 *  MUTEX — mutual exclusion wrapper
 * ═══════════════════════════════════════════════════════════════ */

typedef struct DZZW_Mutex {
    pthread_mutex_t mu;
} DZZW_Mutex;

DZZW_Mutex *dzzw_mutex_new(void);
void dzzw_mutex_lock(DZZW_Mutex *m);
void dzzw_mutex_unlock(DZZW_Mutex *m);
void dzzw_mutex_free(DZZW_Mutex *m);

/* ═══════════════════════════════════════════════════════════════
 *  THREAD POOL — worker threads + work queue
 * ═══════════════════════════════════════════════════════════════ */

typedef struct DZZW_Pool {
    int num_workers;
    pthread_t *workers;
    
    DZZW_Task *queue_head;
    DZZW_Task *queue_tail;
    int queue_len;
    pthread_mutex_t queue_mu;
    pthread_cond_t  queue_cv;
    
    atomic_bool running;
    atomic_int pending_count;
} DZZW_Pool;

/* Called once from main thread */
void dzzw_init(int num_workers);

/* Shutdown — wait for all workers to finish */
void dzzw_shutdown(void);

/* Spawn a task — returns a Future */
DZZW_Future *dzzw_spawn(Value *fn, Value **args, int argc);

/* Wait for a future to complete, return its result */
Value *dzzw_await(DZZW_Future *f);

/* Get number of workers */
int dzzw_worker_count(void);

/* Get pending task count */
int dzzw_pending_count(void);

/* Direct task enqueue (for parallel_map internal use) */
void dzzw_enqueue(DZZW_Task *task);

#endif /* DZZW_H */