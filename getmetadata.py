
from solr import SolrConnection

import simplejson

from httplib import BadStatusLine

from time import sleep

import logging

logger = logging.getLogger("getmetadata")
logger.setLevel(logging.INFO)
# create console handler and set level to debug
ch = logging.StreamHandler()
# create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# add formatter to ch
ch.setFormatter(formatter)
# add ch to logger
logger.addHandler(ch)

import urllib

SERVER = "http://ora.ouls.ox.ac.uk:8080/fedora/risearch"

def getTrippi(query_type, query, lang='itql', format='Sparql',limit='100'):
  query_type = query_type.lower()
  if query != '' and (query_type == 'tuples' or query_type == 'triples'):
    queryparams = urllib.urlencode({'type' : query_type, 'lang' : lang, 'format' : format, 'query' : query, 'limit' : limit })
    response = urllib.urlopen( SERVER, queryparams).read()
    return response
  return None

def getTuples(query, lang='itql', format='sparql', limit='100', offset='0'):
  return getTrippi('tuples', query, lang, format, limit)

def resolveTinyPid(pid):
  query = "select $object from <#ri> where $object <info:fedora/fedora-system:def/model#label> '" + pid +"'"
  linelist = getTuples(query, format='csv').split("\n")
  if len(linelist) == 3:
    return linelist[1].split('/')[-1]
  else:
    return pid

def titlelookup(pid):
  s = SolrConnection("ora.ouls.ox.ac.uk:8080")
  results = {}
  query = ""
  if pid:
    pid = "\:".join(pid.split(":"))
    query = "id:%s" % pid
  elif uuid:
    query = "id:uuid\:%s" % uuid
  else:
    return results
  # Running actual query (3 tries, failover)
  tries = 0
  while(tries != 3):
    try:
      r = s.search(q = query, wt = "json", fl = "title")
      logger.debug("Solr response: %s" % r)
      tries = 3
    except BadStatusLine:
      sleep(0.5)
      tries = tries + 1
  try:
    results = simplejson.loads(r)
    assert results['response']['numFound'] == 1
    doc =  results['response']['docs'][0]
    return doc['title']
  except ValueError:
    logger.warn("Couldn't parse json response from Solr endpoint: %s" % r)
    return {}
  except AssertionError:
    logger.warn("Couldn't assert that only a single result was fetched: %s" % results)
    return {}


def oralookup(pid=None, uuid=None, fields_to_return="f_name, f_subject, f_keyphrase, faculty, f_institution, thesis_type, content_type, collection"):
  s = SolrConnection("ora.ouls.ox.ac.uk:8080")
  results = {}
  query = ""
  if pid:
    pid = "\:".join(pid.split(":"))
    query = "id:%s" % pid
  elif uuid:
    query = "id:uuid\:%s" % uuid
  else:
    return results
  # Running actual query (3 tries, failover)
  tries = 0
  while(tries != 3):
    try:
      r = s.search(q = query, wt = "json", fl = fields_to_return)
      logger.debug("Solr response: %s" % r)
      tries = 3
    except BadStatusLine:
      sleep(0.5)
      tries = tries + 1
  try:
    results = simplejson.loads(r)
    assert results['response']['numFound'] == 1
    return results['response']['docs'][0]
  except ValueError:
    logger.warn("Couldn't parse json response from Solr endpoint: %s" % r)
    return {}
  except AssertionError:
    logger.warn("Couldn't assert that only a single result was fetched: %s" % results)
    return {}


if __name__ == "__main__":
  print "Looking up 'ora:admin'"
  print oralookup(pid="ora:admin")
  print "-"*30
  print "Looking up a uuid"
  print oralookup(uuid="833f0dcf-8426-49e8-a10e-3f0f50300e2e")
  print "-"*30
  print "Looking up an invalid id"
  print oralookup(uuid="failifaifolaiflailfi")
