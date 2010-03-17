import logging

logger = logging.getLogger("debotandseparatelogs")
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)

logger.addHandler(ch)

from utils import characterise_and_requeue_logline
from time import sleep

from redis import Redis

import sys

feedqueue = "q:loglines"
bot = "bothits"
item = "objectviews"
other = "other"
                            
if __name__ == "__main__":
    if len(sys.argv) == 2:
        feedqueue = sys.argv[1]
    r = Redis()
    if feedqueue == "--dryrun":
        while(True):
            logger.info("Dry-run only - not going to enter parse and requeue loop")
            sleep(10000)
    while(True):
        line = r.rpop(feedqueue)
        if line:
            characterise_and_requeue_logline(line, r, bothits = bot, objectviews = item, other = other)
            if (r.llen("q:%s" % bot) > 10000) or (r.llen("q:%s" % item) > 10000) or (r.llen("q:%s" % other) > 10000):
                # rate limit to an extent
                sleep(0.1)
        else:
            sleep(1)
