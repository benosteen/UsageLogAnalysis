from redisqueue import RedisQueue
from redis import Redis
import unittest

class TestBasicQueueFunctions(unittest.TestCase):
  def setUp(self):
    self.rq = RedisQueue("testqueue", "testworker01", db=10)
    self.r = Redis(db=10)
    self.r.delete("testqueue")
    self.r.delete(self.rq.workeritem)

  def test_add_to_queue(self):
    self.rq.push("testitem")
    self.assertEqual(len(self.rq), 1)
    self.assertEqual(self.rq.pop(), "testitem")

  def test_multiple_additions(self):
    results = map(self.rq.push, xrange(10))
    self.assertEquals(results, [True]*10)

  def test_temp_workerqueue(self):
    self.rq.push("testitem")
    self.rq.push("nextitem")
    # worker can pop item, but until it declares complete/fail, 
    # subsequent pops will return that same item
    item = self.rq.pop()
    self.assertEqual(item, "testitem")
    self.assertEqual(len(self.rq), 1)
    item = self.rq.pop()
    self.assertEqual(item, "testitem")
    self.assertEqual(len(self.rq), 1)

  def test_workerqueue_complete(self):
    self.rq.push("testitem")
    self.rq.push("nextitem")
    # worker can pop item, but until it declares complete/fail, 
    # subsequent pops will return that same item
    item = self.rq.pop()
    self.assertEqual(item, "testitem")
    self.assertEqual(len(self.rq), 1)
    item = self.rq.pop()
    self.assertEqual(item, "testitem")
    self.assertEqual(len(self.rq), 1)
    self.rq.task_complete()
    item = self.rq.pop()
    self.assertEqual(item, "nextitem")
    self.assertEqual(len(self.rq), 0)

  def test_requeue_on_fail(self):
    self.rq.push("testitem")
    self.rq.push("nextitem")
    # worker can pop item, but until it declares complete/fail, 
    # subsequent pops will return that same item
    item = self.rq.pop()
    self.assertEqual(item, "testitem")
    self.assertEqual(len(self.rq), 1)
    item = self.rq.pop()
    self.assertEqual(item, "testitem")
    self.assertEqual(len(self.rq), 1)
    self.rq.task_failed()
    self.assertEqual(len(self.rq), 2)

  def test_requeue_to_end_on_fail(self):
    self.rq.push("testitem")
    self.rq.push("nextitem")
    # worker can pop item, but until it declares complete/fail, 
    # subsequent pops will return that same item
    item = self.rq.pop()
    self.assertEqual(item, "testitem")
    self.assertEqual(len(self.rq), 1)
    self.rq.task_failed()
    self.assertEqual(len(self.rq), 2)
    item = self.rq.pop()
    self.assertEqual(item, "nextitem")
    self.assertEqual(len(self.rq), 1)
    self.rq.task_complete()
    item = self.rq.pop()
    self.assertEqual(item, "testitem")
    self.assertEqual(len(self.rq), 0)
    
if __name__ == '__main__':
  unittest.main()

