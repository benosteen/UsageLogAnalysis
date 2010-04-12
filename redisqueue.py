#!/usr/bin/env python

from redis import Redis

WORKERPREFIX = "temp"
HOST = "localhost"
PORT = 6379
DB = 0

"""Simple wrapper around a redis queue that gives methods in line with the other Queue-style classes"""

class RedisQueue(object):
  def __init__(self, queuename, workername, db=DB, host=HOST, port=PORT, workerprefix=WORKERPREFIX):
    self.host = host
    self.port = port
    self.queuename = queuename
    self.workeritem = ":".join([workerprefix, workername])
    self.db = db
    self._initclient()

  def _initclient(self):
    self._r = Redis(host=self.host, db=self.db, port=self.port)

  def __len__(self):
    return self._r.llen(self.queuename)

  def __getitem__(self, index):
    return self._r.lrange(self.queuename, index, index)

  def inprogress(self):
    return self._r.lrange(self.workeritem, 0, 0).pop()

  def task_complete(self):
    return self._r.rpop(self.workeritem)

  def task_failed(self):
    return self._r.rpoplpush(self.workeritem, self.queuename)

  def push(self, item):
    return self._r.lpush(self.queuename, item)

  def pop(self):
    if self._r.llen(self.workeritem) == 0:
      return self._r.rpoplpush(self.queuename, self.workeritem)
    else:
      return self.inprogress()
