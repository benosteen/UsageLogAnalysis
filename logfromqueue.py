from redis import Redis
    
import sys
from os.path import join

from random import randint

from time import sleep

LOGFILEPATH = "processed"

if __name__ == "__main__":
    if len(sys.argv) == 2:
        if sys.argv[1] == "--dryrun":
            while(True):
                print "Not going to listen to queue - dry run only"
                sleep(1000)
        # log and consume
        r = Redis()
        with open(join(LOGFILEPATH, "%s.log" % sys.argv[1]), "a+") as logfile:
            while(True):
                line = r.lpop("q:%s" % sys.argv[1])
                if line:
                    line = line.decode('utf-8')
                    if line.endswith("\n"):
                        logfile.write(line)
                    else:
                        logfile.writelines((line, "\n"))
                else:
                    # Might as well flush the IO
                    logfile.flush()
                    # Check again after a 5-10 seconds wait (to stop spikes)
                    sleep(randint(0,3))
    elif len(sys.argv) > 2:
        # log and fanout
        r = Redis()
        logfilename = sys.argv[1]
        queues = sys.argv[2:]
        with open(join(LOGFILEPATH, "%s.log" % sys.argv[1]), "a+") as logfile:
            while(True):
                line = r.lpop("q:%s" % sys.argv[1])
                if line:
                    if line.endswith("\n"):
                        logfile.write(line)
                    else:
                        logfile.writelines((line, "\n"))
                    for queue in queues:
                        r.lpush("q:%s" % queue, line)
                else:
                    # Flushing IO
                    logfile.flush()
                    # Check again after a 5-10 seconds wait (to stop spikes)
                    sleep(randint(0,3))
    else:
        print "Usage: logfromqueue.py log_name [daisy-chain_to_queues_-_space_delimited]"
        print "For example,"
        print "'logfromqueue.py foo' - listen to 'q:foo' and log msgs sent to it to 'foo.log'"
        print "'logfromqueue.py foo bar' - as above, but propagate the msg to 'q:bar' as well"
        sys.exit(2)
