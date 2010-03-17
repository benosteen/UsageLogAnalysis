import re

# Matches only object record page hits
OBJ_VIEW = re.compile(r"""GET /objects/(?P<namespace>ora|uuid|hdl)(\:|\%3A|\%253A)(?P<id>[0-9abcedf\-]+)[/]? """, re.I|re.U)

# Matches any GET on an object resource base URL, inc. record views
OBJ_GETS = re.compile(r"""GET /objects/(?P<namespace>ora|uuid|hdl)(\:|\%3A|\%253A)(?P<id>[0-9abcedf\-]+)[/]?""", re.I|re.U)

# Matches any GET on an object datastream
OBJ_DATASTREAM = re.compile(r"""GET /objects/(?P<namespace>ora|uuid|hdl)(\:|\%3A|\%253A)(?P<id>[0-9abcedf\-]+)/datastreams/(?P<dsid>[0-9A-z\-]+) """, re.I|re.U)

IP_TEST = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

import logging

logger = logging.getLogger("logfile_utils")
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)

logger.addHandler(ch)

def parseline(line):
    tokens = line.split(" ")
    columns = []
    escaped = []
    for token in tokens:
        token = token.strip()
        if token:
            if escaped:
                if token.endswith("\""):
                    escaped.append(token[:-1])
                    columns.append(" ".join(escaped))
                    escaped = []
                else:
                    escaped.append(token)
            else:
                if token.startswith("\""):
                    if token.endswith("\""):
                        columns.append(token[1:-1])
                    else:
                        escaped = [token[1:]]
                else:
                    columns.append(token)
    return columns

def pageview(parsedline):
    if len(parsedline) == 6:
        return False
    try:
        logger.debug("Checking to see if %s is a object/pageview" % parsedline[9])
        m = OBJ_VIEW.match(parsedline[9])
    except IndexError, e:
        logger.debug("Failed to match - Exception thrown")
        return False
    if m != None:
        results = m.groupdict()
        if results.get("id") and results.get("namespace"):
            logger.debug("It is a view/dl!")
            return "%s:%s" % (results['namespace'], results['id'])
    return False
    
def getonobjecturl(parsedline):
    if len(parsedline) == 6:
        return False
    try:
        logger.debug("Checking to see if %s is a object-orientated URL" % parsedline[9])
        m = OBJ_GETS.match(parsedline[9])
    except IndexError, e:
        logger.debug("Failed to match - Exception thrown")
        return False
    if m != None:
        results = m.groupdict()
        if results.get("id") and results.get("namespace"):
            logger.debug("It is an object-oriented URL!")
            return "%s:%s" % (results['namespace'], results['id'])
    return False
    
def isbotip(ip, r):   # r = redis_client
    for botlist in r.smembers('botlist'):
        domainip = "1234567890"
        try:
            domainip = ".".join(ip.split(".")[:3])
        except:
            logger.debug("Domain IP parse Fail")
            pass
        if r.sismember(botlist, ip) or r.sismember(botlist, domainip):
            return True
    return False

def characterise_logline(line, r):
    pl = parseline(line)
    
    if len(pl)>5:
        pid = getonobjecturl(pl)
        logger.debug("Testing if %s is a bot" % (pl[4]))
        if IP_TEST.match(pl[4]) != None and pl[10] != "404":
            if isbotip(pl[4], r):
                logger.debug("It is a bot!")
                return "bot"
            elif pid:
                return "itemview"
            else:
                return "other"
        else:
            return "fourohfour"
    else:
        return


def characterise_and_requeue_logline(line, r = None, bothits = "bothits", objectviews = "objectviews", other = "other", fourohfour = "fof"):
    if r == None:
        logger.error("You must pass a redis client to this function for it to work")
    character = characterise_logline(line, r)
    if character.startswith("b"):
        r.incr("u:%s" % bothits)
        r.lpush("q:%s" % bothits, line)
    elif character.startswith("i"):
        r.incr("u:%s" % objectviews)
        r.lpush("q:%s" % objectviews, line)
    elif character.startswith("o"):
        r.incr("u:%s" % other)
        r.lpush("q:%s" % other, line)
    elif character.startswith("f"):
        r.incr("u:%s" % fourohfour)
        r.lpush("q:%s" % fourohfour, line)
    else:
        #ignore the line
        pass
                                
                                
#if __name__ == "__main__":
#    from redis import Redis
#    from os import listdir
#    from os.path import isdir, join
#    r = Redis()
#    for logfile in [x for x in listdir(logpath) if not isdir(join(logpath,x))]:
#        logger.debug("Parsing %s" % logfile)
#        parselog("%s/%s" % (logpath, logfile), r, 1000)
