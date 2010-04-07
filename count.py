import logging

logger = logging.getLogger("itemusagecounter")
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)

logger.addHandler(ch)

from utils import characterise_and_requeue_logline
from time import sleep

from redis import Redis

from utils import pageview, parseline, getonobjecturl, OBJ_VIEW, OBJ_GETS, OBJ_DATASTREAM 

from getmetadata import oralookup, resolveTinyPid
import hashlib

from datetime import datetime

import sys

item = "objectviews"

grouping = {"f_name":"names", 
            "f_subject":"subjects",
            "f_keyphrase":"keyphrases",
            "f_institution":"institution",
            "faculty":"faculty",
            "content_type":"contenttype",
            "thesis_type":"thesistype",
            "collection":"collection",
            "------":"objectids"}

prefixes = {"names":"n",
            "subjects":"s",
            "keyphrases":"k",
            "institution":"i",
            "faculty":"f",
            "contenttype":"type",
            "thesistype":"tt",
            "collection":"col",
            "objectids":"uuid"}

rev_prefixes = dict([(prefixes[x], x) for x in prefixes])

def get_entity_name(text, tagtype):
    prefix = prefixes.get(tagtype)
    if prefix:
        return "%s:%s" % (prefix, hashlib.md5(text).hexdigest())

def entity_existence(text, tagtype, r):
    key = get_entity_name(text, tagtype)
    if r.get(key):
        return key
    return False

def get_entity(text, tagtype, r, pid = None):
    key = entity_existence(text, tagtype, r)
    if not key:
        key = get_entity_name(text, tagtype)
        logger.debug("""Adding %s for "%s" (%s)""" % (key, text, tagtype))
        r.set(key, text)
        r.sadd(tagtype, key)
    if pid:
        r.sadd("e:%s" % key, pid)
        r.sadd("e:%s" % pid, key)
    return key

def inc_count(field, text, tag, pl, r, pid):
    text = text.encode('utf-8')
    tagtype = grouping.get(field)
    key = get_entity(text, tagtype, r, pid)
    newcount = r.incr("t:%s:%s" % (tag, key))
    logger.debug("""Incremented %s for %s to %s""" % (tag, key, newcount))

def increment_counts(pl, md, tag, r, pid):
    for field in [x for x in md if x in grouping]:
        if isinstance(md[field], list):
            for item in set(md[field]):
                if item:
                    inc_count(field, item, tag, pl, r, pid)
        elif md[field]:
            inc_count(field, md[field], tag, pl, r, pid)

if __name__ == "__main__":
    if len(sys.argv) == 2:
        item = sys.argv[1]
    r = Redis()
    if item == "--dryrun":
        while(True):
            logger.info("Dry-run only - not going to enter parse and requeue loop")
            sleep(10000)
    while(True):
        line = r.lpop("q:%s" % item)
        if line:
            logger.debug("Received a line from the queue, beginning: %s" % line[:30])
            pl = parseline(line)
            request_url = pl[9]
            # Get the basics - namespace/pid
            results = OBJ_GETS.match(request_url).groupdict()
            pid = "%s:%s" % (results['namespace'], results['id'])
            if results['namespace'] == "ora":
                pid = resolveTinyPid(pid)
            md = oralookup(pid=pid)
            logger.debug("pid found: %s" % pid)
            # Increment the total hits on this item
            r.sadd("objectids", pid)
            if pageview(pl):
                # It's a GET for the record page itself
                r.sadd("%s:%s:v" % (pl[0], pid), pl[4])
                r.sadd("dv:%s" % pid, pl[0])
                r.sadd("ua:%s" % pl[4], pl[13])
                increment_counts(pl, md, "views", r, pid)
                r.incr("t:views:%s" % pid)
                r.set("v:stamp", datetime.now().isoformat()[:22])
            else:
                m = OBJ_DATASTREAM.match(request_url)
                if m != None:
                    # its a download
                    r.sadd("%s:%s:d" % (pl[0], pid), pl[4])
                    r.sadd("dd:%s" % pid, pl[0])
                    r.sadd("ua:%s" % pl[4], pl[13])
                    increment_counts(pl, md, "dls", r, pid)
                    r.incr("t:dls:%s" % pid)
                    r.set("d:stamp", datetime.now().isoformat()[:22])
                else:
                    r.sadd("%s:%s:o" % (pl[0], pid), pl[4])
                    r.sadd("do:%s" % pid, pl[0])
                    r.sadd("ua:%s" % pl[4], pl[13])
                    increment_counts(pl, md, "other", r, pid)
                    r.incr("t:other:%s" % pid)
                    r.set("o:stamp", datetime.now().isoformat()[:22])
        else:
            sleep(2)
