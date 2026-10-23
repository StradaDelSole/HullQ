"""Unit tests for hullq.api.app's bounded export-job admission gate.

Independent review round 3, Finding A (2026-10-16 amendment line): round 2's
`_run_export_job` attached the admission-slot release to the `asyncio.Future`
that `run_in_executor`/`wrap_future` hands back to the awaiting caller, not to
the real underlying `concurrent.futures.Future`. `asyncio.Future.cancel()`
unconditionally transitions a still-pending asyncio future to CANCELLED --
firing its done callbacks -- the instant the awaiting Task is cancelled,
regardless of whether the real `concurrent.futures.Future` could actually be
cancelled (it only can while the job has not yet started on a worker thread).
That let a cancelled-but-still-running export job's admission slot be freed
while the real worker thread kept executing, letting concurrently *running*
jobs exceed `_EXPORT_MAX_CONCURRENT_JOBS`.

These tests exercise the fixed `_run_export_job` directly against the module
globals it actually reads (`_export_executor`, `_export_admission_semaphore`),
monkeypatched per test to a dedicated, deterministically sized executor/
semaphore pair so each test can control exactly how many real worker threads
and admission slots exist without touching the shared production pool sized
by `_EXPORT_MAX_CONCURRENT_JOBS`. Synchronization is via `threading.Event`
(for the real worker threads) and a bounded `asyncio.sleep(0)` settle loop
(a pure scheduling yield, not a wall-clock wait) for the event loop side --
never a timing-based `sleep()` whose correctness depends on a race being won.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading

import pytest

from hullq.api import app as app_module


class _ObservableSemaphore:
    """Drop-in for the two methods `_run_export_job` actually calls on
    `_export_admission_semaphore`: `.acquire(blocking=False)` and
    `.release()`. Backed by a `threading.BoundedSemaphore` so a double
    release (the exact round-2 defect class) raises `ValueError`
    immediately instead of silently over-admitting; also exposes a
    release count and a `threading.Event` so tests can deterministically
    observe "a release has now happened" without any wall-clock sleep.
    """

    def __init__(self, value: int) -> None:
        self._sem = threading.BoundedSemaphore(value)
        self._count_lock = threading.Lock()
        self.release_count = 0
        self.release_event = threading.Event()

    def acquire(self, blocking: bool = True) -> bool:
        return self._sem.acquire(blocking)

    def release(self) -> None:
        self._sem.release()
        with self._count_lock:
            self.release_count += 1
        self.release_event.set()


async def _settle(iterations: int = 200) -> None:
    """Yield the event loop repeatedly so every already-scheduled
    `call_soon` callback (asyncio Future cancellation propagation, task
    wakeups, `concurrent.futures` done-callback chaining) gets a chance to
    run. This is a pure scheduling yield (`asyncio.sleep(0)`), never a
    wall-clock wait -- the invariants these tests check are gated by real
    `threading.Event`s a background worker thread controls, so no number
    of extra loop iterations here can make an assertion pass that
    shouldn't; the bound only guards against an actual deadlock."""
    for _ in range(iterations):
        await asyncio.sleep(0)


async def _await_event(event: threading.Event, *, max_iterations: int = 10_000) -> None:
    """Poll `event.is_set()` (non-blocking), yielding the event loop
    between checks. Required instead of the blocking `Event.wait()`
    whenever what we are waiting for can only happen once the *current*
    asyncio task itself gets a chance to run -- e.g. immediately after
    `asyncio.create_task(...)`, before the task has ever been stepped. A
    blocking `wait()` there would starve that very task: nothing else can
    run on this single event-loop thread while it is blocked, so the
    worker thread that would eventually set the event can never even be
    submitted. Safe to use everywhere else too -- it is simply unnecessary
    (and this repo avoids wall-clock-timing-dependent tests either way)
    once the thing being waited for is driven by an independent OS
    thread that does not itself need the event loop to make progress."""
    for _ in range(max_iterations):
        if event.is_set():
            return
        await asyncio.sleep(0)
    pytest.fail("event was never set before the deadlock-guard bound")


def _patch_bounded_resources(
    monkeypatch: pytest.MonkeyPatch, *, workers: int, slots: int
) -> tuple[concurrent.futures.ThreadPoolExecutor, _ObservableSemaphore]:
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    semaphore = _ObservableSemaphore(slots)
    monkeypatch.setattr(app_module, "_export_executor", executor)
    monkeypatch.setattr(app_module, "_export_admission_semaphore", semaphore)
    return executor, semaphore


class TestCancellationWhileWorkerRunning:
    """Test A: cancelling the awaiting coroutine while the real worker
    thread is still actively running must never release the admission
    slot -- the slot is only freed when the real work genuinely finishes."""

    def test_slot_stays_held_until_real_worker_completion(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        executor, semaphore = _patch_bounded_resources(monkeypatch, workers=1, slots=1)
        try:
            started = threading.Event()
            release_worker = threading.Event()
            finished = threading.Event()

            def blocking_job() -> str:
                started.set()
                assert release_worker.wait(timeout=5), "test never released the worker"
                finished.set()
                return "done"

            async def scenario() -> None:
                task = asyncio.create_task(app_module._run_export_job(blocking_job))
                await _await_event(started)

                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
                await _settle()

                # The real worker thread must still be running: cancelling
                # the awaiting coroutine never stops it, and it was never
                # signalled to finish.
                assert not finished.is_set()
                assert semaphore.release_count == 0

                # The single slot is still genuinely in use by the
                # still-running worker -- a second job must be refused
                # BUSY, not queued and not silently admitted.
                busy_result = await app_module._run_export_job(lambda: "must not run")
                assert busy_result is app_module._EXPORT_BUSY
                assert semaphore.release_count == 0

                # Let the real worker finish, then the slot is released
                # exactly once.
                release_worker.set()
                assert finished.wait(timeout=5), "worker never completed"
                assert semaphore.release_event.wait(timeout=5)
                assert semaphore.release_count == 1

                # The now-genuinely-free slot admits a fresh job normally.
                result = await app_module._run_export_job(lambda: "fresh")
                assert result == "fresh"
                assert semaphore.release_count == 2

            asyncio.run(scenario())
        finally:
            executor.shutdown(wait=True)


class TestCancellationBeforeWorkerStart:
    """Test B: a job that is admitted (its admission slot acquired and its
    `concurrent.futures.Future` submitted) but genuinely never picked up by
    any worker thread, because every real worker is still busy, must never
    run its body once cancelled -- and its slot must be released."""

    def test_queued_job_cancelled_before_start_never_runs_and_releases_slot(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # One real worker thread, but two admission slots: the first job
        # occupies the only worker; the second is genuinely admitted
        # (semaphore acquired, future submitted) yet cannot start, because
        # no worker thread is free to run it.
        executor, semaphore = _patch_bounded_resources(monkeypatch, workers=1, slots=2)
        try:
            job1_started = threading.Event()
            release_job1 = threading.Event()
            job2_ran = threading.Event()

            def job1() -> str:
                job1_started.set()
                assert release_job1.wait(timeout=5), "test never released job1"
                return "job1-done"

            def job2() -> str:
                job2_ran.set()
                return "job2-done"

            async def scenario() -> None:
                task1 = asyncio.create_task(app_module._run_export_job(job1))
                await _await_event(job1_started)

                task2 = asyncio.create_task(app_module._run_export_job(job2))
                # Let task2 actually run its synchronous prelude (acquire
                # the slot, submit to the executor, register the done
                # callback, start awaiting) -- it cannot progress past that
                # await, since the only worker thread is occupied by job1.
                await _settle()

                task2.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task2
                await _settle()

                # job2's body must never have executed: its future was
                # still queued (never running) when cancelled, so
                # `concurrent.futures` never invokes the work item at all.
                assert not job2_ran.is_set()
                # Cancelling a genuinely queued-but-never-started future
                # succeeds immediately, so its slot is already released --
                # never left held because "it might still be about to run".
                assert semaphore.release_event.wait(timeout=5)
                assert semaphore.release_count == 1

                release_job1.set()
                result1 = await task1
                assert result1 == "job1-done"
                assert semaphore.release_count == 2

            asyncio.run(scenario())
        finally:
            executor.shutdown(wait=True)


class TestNormalCompletion:
    """Test C: an ordinary successful run releases its slot exactly once,
    and a subsequent job is admitted normally afterwards."""

    def test_successful_job_releases_exactly_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        executor, semaphore = _patch_bounded_resources(monkeypatch, workers=1, slots=1)
        try:

            async def scenario() -> None:
                result1 = await app_module._run_export_job(lambda: "first")
                assert result1 == "first"
                assert semaphore.release_count == 1

                result2 = await app_module._run_export_job(lambda: "second")
                assert result2 == "second"
                assert semaphore.release_count == 2

            asyncio.run(scenario())
        finally:
            executor.shutdown(wait=True)


class TestWorkerException:
    """Test D: a worker raising an exception still releases its slot
    exactly once -- the exception propagates to the caller, no slot leak,
    no double release (which `_ObservableSemaphore`'s `BoundedSemaphore`
    backing would raise `ValueError` on)."""

    def test_failing_job_releases_exactly_once_and_propagates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        executor, semaphore = _patch_bounded_resources(monkeypatch, workers=1, slots=1)
        try:

            class _Boom(RuntimeError):
                pass

            def failing_job() -> None:
                raise _Boom("deliberate worker failure")

            async def scenario() -> None:
                with pytest.raises(_Boom):
                    await app_module._run_export_job(failing_job)
                assert semaphore.release_count == 1

                # The slot is available again -- a following job runs
                # normally, proving no leak.
                result = await app_module._run_export_job(lambda: "ok")
                assert result == "ok"
                assert semaphore.release_count == 2

            asyncio.run(scenario())
        finally:
            executor.shutdown(wait=True)


class TestConcurrentCancellationNeverExceedsCap:
    """Test E: overlapping cancellation and real completion among several
    concurrently admitted jobs must never let the number of genuinely
    *running* worker bodies exceed the admission cap, and every slot must
    end up available again."""

    def test_true_running_concurrency_never_exceeds_cap(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cap = 2
        executor, semaphore = _patch_bounded_resources(monkeypatch, workers=cap, slots=cap)
        try:
            lock = threading.Lock()
            running = 0
            max_running = 0

            def make_job(release_event: threading.Event) -> object:
                def job() -> str:
                    nonlocal running, max_running
                    with lock:
                        running += 1
                        max_running = max(max_running, running)
                    assert release_event.wait(timeout=5), "test never released this job"
                    with lock:
                        running -= 1
                    return "ok"

                return job

            async def scenario() -> None:
                release0 = threading.Event()
                release1 = threading.Event()
                release4 = threading.Event()
                release4.set()  # job4 is deliberately instantaneous

                task0 = asyncio.create_task(app_module._run_export_job(make_job(release0)))
                task1 = asyncio.create_task(app_module._run_export_job(make_job(release1)))

                # Both real worker slots are occupied once `running == 2`
                # is reachable only by both actually having started.
                for _ in range(10_000):
                    with lock:
                        if running == cap:
                            break
                    await asyncio.sleep(0)
                else:
                    pytest.fail("job0/job1 never both started")

                # Every slot is genuinely in use: a third admission attempt
                # is refused BUSY, never queued.
                busy1 = await app_module._run_export_job(lambda: "must not run")
                assert busy1 is app_module._EXPORT_BUSY

                # Cancel task0's *awaiting coroutine* while its real worker
                # thread is still genuinely running (blocked on release0).
                task0.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task0
                await _settle()

                # The real worker for job0 is still running -- cancelling
                # the await must never have freed its slot.
                with lock:
                    assert running == cap
                busy2 = await app_module._run_export_job(lambda: "must not run either")
                assert busy2 is app_module._EXPORT_BUSY

                # Let job0's real worker actually finish now.
                release0.set()
                assert semaphore.release_event.wait(timeout=5)
                with lock:
                    assert running == cap - 1

                # The genuinely freed slot admits job4 normally, while
                # job1 is still running -- true concurrency reaches the
                # cap again (job1 + job4) but never exceeds it.
                result4 = await app_module._run_export_job(make_job(release4))
                assert result4 == "ok"

                release1.set()
                result1 = await task1
                assert result1 == "ok"

                with lock:
                    final_running = running
                assert final_running == 0
                assert max_running == cap

                # Every slot is available again at the end.
                for _ in range(cap):
                    assert semaphore.acquire(blocking=False)
                for _ in range(cap):
                    semaphore.release()

            asyncio.run(scenario())
        finally:
            executor.shutdown(wait=True)
