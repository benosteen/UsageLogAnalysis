import simplejson

from redis import Redis
from os import listdir
from os.path import isdir, join

from time import sleep

from utils import parseline

import sys

import logging

logger = logging.getLogger("queuefromlogs")
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)

logger.addHandler(ch)

logpath = "logs"

out_queue = "q:loglines"

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        out_queue = sys.argv[1]
        if len(sys.argv) > 2 and isdir(sys.argv[2]):
            logpath = sys.argv[2]
    logger.info("Adding log lines from log files in %s directory" % logpath)
    r = Redis()
    for logfile in [x for x in listdir(logpath) if not isdir(join(logpath,x))]:
        logger.debug("Parsing %s" % logfile)
        with open(join(logpath,logfile), "r") as loghandle:
            for logline in loghandle:
                logger.debug("Passing log line to queue: %s" % logline)
                pl = parseline(logline)
                # make sure it is a message from the wsgi handler
                if pl[3] == "[wsgi]":
                    r.lpush(out_queue, logline)
                    # crude rate limiting
                    if r.llen(out_queue) > 10000:
                        logger.info("Rate limiting as there are 10000 msgs on the queue already. Sleep for 1 sec")
                        sleep(0.1)
                    if r.llen(out_queue) > 1000000:
                        logger.info("Rate limiting as there are 100000 msgs on the queue already! Sleep for 10 sec")
                        sleep(10)
