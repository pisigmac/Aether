from aether.jobs import JobStore


def test_job_progress_lifecycle():
    store = JobStore()
    job = store.create()
    store.update(job.id, 22, "Sampling git history")
    mid = store.get(job.id)
    assert mid is not None
    assert mid.percent == 22
    assert mid.stage == "Sampling git history"
    store.finish(job.id, {"universe_id": "abc"})
    done = store.get(job.id)
    assert done is not None
    assert done.status == "done"
    assert done.percent == 100
    assert done.result["universe_id"] == "abc"


def test_job_list_newest_first():
    store = JobStore()
    older = store.create(label="first")
    newer = store.create(label="second")
    store.update(older.id, 10, "Parsing")
    rows = store.list(limit=10)
    assert [row.id for row in rows] == [newer.id, older.id]
    assert rows[1].label == "first"
    assert rows[1].percent == 10
    assert rows[0].created_at
    assert len(store.list(limit=1)) == 1
