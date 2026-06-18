/* ═══════════════════════════════════════════════════════════════
 *  DZZW — Parallel Multi-Tasking Runtime for H#  v2.0
 *  Work-stealing thread pool, VM reuse, memory pooling,
 *  futures, channels, mutex, parallel-for/reduce, continuations
 * ═══════════════════════════════════════════════════════════════ */

#ifndef DZZW_H
#define DZZW_H

#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>

/* Forward declaration of Value */
typedef struct Value Value;
typedef struct VM VM;

/* ═══════════════════════════════════════════════════════════════
 *  FUTURE — awaitable task result
 * ═══════════════════════════════════════════════════════════════ */

typedef enum { DZZW_PENDING, DZZW_RUNNING, DZZW_DONE, DZZW_ERROR } DZZW_FutureState;

typedef struct DZZW_Future {
    DZZW_FutureState    state;
    Value              *result;
    pthread_mutex_t     mu;
    pthread_cond_t      cv;
    int                 refcount;
} DZZW_Future;

DZZW_Future *dzzw_future_new(void);
void         dzzw_future_set(DZZW_Future *f, Value *v);
void         dzzw_future_set_error(DZZW_Future *f, Value *v);
Value       *dzzw_future_wait(DZZW_Future *f);
Value       *dzzw_future_try_wait(DZZW_Future *f);
void         dzzw_future_free(DZZW_Future *f);

/* ═══════════════════════════════════════════════════════════════
 *  TASK — a unit of work (function + arguments)
 * ═══════════════════════════════════════════════════════════════ */

typedef struct DZZW_Task {
    Value             *fn;
    Value            **args;
    int                argc;
    DZZW_Future       *future;
    struct DZZW_Task  *next;
} DZZW_Task;

/* ═══════════════════════════════════════════════════════════════
 *  WORKER — per-worker state (VM reuse + local work-stealing queue)
 * ═══════════════════════════════════════════════════════════════ */

#define DZZW_LOCAL_QUEUE_SIZE 256

typedef struct DZZW_Worker {
    int                 id;
    pthread_t           thread;
    VM                 *vm;              /* Per-worker VM — reused across tasks! */
    void               *executor_data;   /* Opaque data for executor callback */
    
    /* Lock-free local work-stealing queue (bounded ring buffer) */
    DZZW_Task          *local_queue[DZZW_LOCAL_QUEUE_SIZE];
    atomic_int          local_head;      /* Worker writes here (tail) */
    atomic_int          local_tail;      /* Worker + thieves read here (head) */
    
    /* Stats */
    atomic_int          tasks_executed;
    atomic_int          steals_success;
    atomic_int          steals_failed;
} DZZW_Worker;

/* ═══════════════════════════════════════════════════════════════
 *  CHANNEL — bounded communication channel between tasks
 * ═══════════════════════════════════════════════════════════════ */

typedef struct DZZW_Channel {
    Value            **buf;
    int                cap;
    int                head;
    int                tail;
    int                count;
    pthread_mutex_t    mu;
    pthread_cond_t     not_empty;
    pthread_cond_t     not_full;
} DZZW_Channel;

DZZW_Channel *dzzw_channel_new(int capacity);
void          dzzw_channel_send(DZZW_Channel *ch, Value *v);
Value        *dzzw_channel_recv(DZZW_Channel *ch);
void          dzzw_channel_free(DZZW_Channel *ch);

/* ═══════════════════════════════════════════════════════════════
 *  EXECUTOR — callback type for worker threads to execute H# code
 *  v2: now receives worker pointer for VM reuse
 * ═══════════════════════════════════════════════════════════════ */

typedef void (*DZZW_ExecutorFn)(Value *fn, Value **args, int argc,
                                DZZW_Future *fut, DZZW_Worker *worker);
void dzzw_set_executor(DZZW_ExecutorFn exec);

/* ═══════════════════════════════════════════════════════════════
 *  MUTEX — mutual exclusion wrapper
 * ═══════════════════════════════════════════════════════════════ */

typedef struct DZZW_Mutex {
    pthread_mutex_t mu;
} DZZW_Mutex;

DZZW_Mutex *dzzw_mutex_new(void);
void        dzzw_mutex_lock(DZZW_Mutex *m);
void        dzzw_mutex_unlock(DZZW_Mutex *m);
void        dzzw_mutex_free(DZZW_Mutex *m);

/* ═══════════════════════════════════════════════════════════════
 *  THREAD POOL — work-stealing workers + global queue + memory pool
 * ═══════════════════════════════════════════════════════════════ */

#define DZZW_MEMPOOL_TASK_SIZE 1024

typedef struct DZZW_Pool {
    int                 num_workers;
    DZZW_Worker        *workers;
    
    /* Global overflow queue (used when local queues are full) */
    DZZW_Task          *global_queue_head;
    DZZW_Task          *global_queue_tail;
    int                 global_queue_len;
    pthread_mutex_t     global_queue_mu;
    pthread_cond_t      global_queue_cv;
    
    /* Task memory pool — avoids repeated malloc/free */
    DZZW_Task          *task_pool;
    int                 task_pool_count;
    pthread_mutex_t     task_pool_mu;
    
    /* Future memory pool */
    DZZW_Future        *future_pool;
    int                 future_pool_count;
    pthread_mutex_t     future_pool_mu;
    
    atomic_bool         running;
    atomic_int          pending_count;
    atomic_int          total_tasks_submitted;
    atomic_int          total_tasks_completed;
    
    /* Blocking vs non-blocking enqueue */
    bool                allow_blocking_enqueue;
} DZZW_Pool;

/* Initialize the thread pool (auto-detect workers if num_workers <= 0) */
void dzzw_init(int num_workers);

/* Shutdown — wait for all workers to finish, free resources */
void dzzw_shutdown(void);

/* ═══════════════════════════════════════════════════════════════
 *  TASK SPAWN & ENQUEUE
 * ═══════════════════════════════════════════════════════════════ */

/* Spawn a task — returns a Future */
DZZW_Future *dzzw_spawn(Value *fn, Value **args, int argc);

/* Enqueue a task directly (used internally by parallel_map etc.) */
void dzzw_enqueue(DZZW_Task *task);

/* Batch enqueue — N tasks with a single lock acquisition */
void dzzw_enqueue_batch(DZZW_Task **tasks, int n);

/* ═══════════════════════════════════════════════════════════════
 *  FUTURE OPERATIONS
 * ═══════════════════════════════════════════════════════════════ */

/* Wait for a future — blocking */
Value *dzzw_await(DZZW_Future *f);

/* Non-blocking wait — returns result if done, NULL if pending */
Value *dzzw_try_await(DZZW_Future *f);

/* Wait for ANY future to complete — returns index */
int dzzw_await_any(DZZW_Future **futures, int n);

/* Wait for ALL futures to complete */
void dzzw_await_all(DZZW_Future **futures, int n);

/* Attach a continuation callback */
void dzzw_then(DZZW_Future *f, void (*callback)(Value *result));

/* ═══════════════════════════════════════════════════════════════
 *  HIGH-LEVEL PARALLEL PRIMITIVES
 * ═══════════════════════════════════════════════════════════════ */

/* Parallel for: split [start, end) across workers, call fn(i) for each */
typedef void (*DZZW_RangeFn)(int index, void *userdata);
void dzzw_parallel_for(int start, int end, DZZW_RangeFn fn, void *userdata);

/* Parallel reduce: combine results from multiple tasks */
typedef void *(*DZZW_MapFn)(int index, void *userdata);
typedef void *(*DZZW_ReduceFn)(void *a, void *b, void *userdata);
void *dzzw_parallel_reduce(int start, int end, DZZW_MapFn map_fn,
                           DZZW_ReduceFn reduce_fn, void *userdata,
                           int chunk_size);

/* ═══════════════════════════════════════════════════════════════
 *  THREAD POOL INFO & CONTROL
 * ═══════════════════════════════════════════════════════════════ */

int dzzw_worker_count(void);
int dzzw_pending_count(void);
int dzzw_total_completed(void);
int dzzw_total_submitted(void);

/* Dump performance stats to stderr */
void dzzw_dump_stats(void);

/* Set whether enqueue blocks when queue is full (default: true) */
void dzzw_set_blocking_enqueue(bool block);

/* Set a cleanup callback for worker-specific data (called during shutdown) */
void dzzw_set_worker_cleanup(void (*fn)(DZZW_Worker *));

#endif /* DZZW_H */