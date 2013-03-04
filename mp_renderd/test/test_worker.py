# from mp_renderd.broker import AvailableWorkers, WorkerData

# def test_available_worker():
#     workers = [
#         WorkerData(queue='q1', process='p1'),
#         WorkerData(queue='q2', process='p2'),
#     ]
#     pool = AvailableWorkers(workers)

#     assert pool.is_available()
#     w1 = pool.get()
#     assert w1 in workers
#     assert pool.is_available()

#     w2 = pool.get()
#     assert w2 in workers
#     assert not pool.is_available()

#     assert w1 != w2

#     pool.put(hash(w2))
#     assert pool.is_available()

#     w3 = pool.get()
#     assert not pool.is_available()

#     assert w2 is w3
