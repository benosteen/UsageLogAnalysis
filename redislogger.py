import logging

from redis import Redis

class RedisLogger(logging.Handler):
  def __init__(self, host, list_name, port=6379, db=0):
    logging.Handler.__init__(self)
    self.host = host
    self.list_name = list_name
    self.port = port
    self.db = db
    self.r = Redis(host, port=port, db=db)

  def emit(self, record):
    try:
      self.r.lpush(self.list_name, self.format(record))
    except:
      try:
        self.r = Redis(self.host)
        self.r.lpush(self.list_name, self.format(record))
      except:
        print "Failed to log on Redis queue"

if __name__ == "__main__":
  import logging
  import logging.config

  logging.config.fileConfig("logging.conf.example")
  
  logger = logging.getLogger("root")
 
  print "Logging a message, both to a file (access.log) and also lpush the same string to a redis list (q:demo in db=10)"
  print "These are defined in the example logging.conf.example file for reference"
  logger.info("Testing the dual logging abilities - to a file and to a redis list")
  print """Python 2.6.4 (r264:75706, Nov  2 2009, 14:44:17) 
[GCC 4.4.1] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> from redis import Redis
>>> r = Redis(db=10)
>>> r.llen("q:demo")
1
>>> r.lrange("q:demo", 0, 0)
['2010-03-17 15:15:08,693,693 INFO  [root] Testing the dual logging abilities - to a file and to a redis list']
"""
