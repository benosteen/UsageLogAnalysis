#!/usr/bin/env python

from httplib2 import Http

from redis import Redis

import sys, traceback

hostip_t = "http://api.hostip.info/country.php?ip=%s"

h = Http()
r = Redis()

def get_total_ip_usage(pid,r):
  hits = {}
  ip_addresses = set()
  for hittype in ['v','d']:
    hits[hittype] = r.smembers("d%s:%s" % (hittype, pid))
    for date in hits[hittype]:
      ip_addresses.update(r.smembers("%s:%s:%s" % (date, pid, hittype)))
  return ip_addresses

def lookup_ip_geocode(ip,r):
  if not r.get("geocode:%s" % ip):
    (resp, content) = h.request(hostip_t % ip)
    if resp.status == 200:
      r.set("geocode:%s" % ip, content)
      return content
    else:
      raise Exception((resp, content))
  else:
    return r.get("geocode:%s" % ip)

def lookup_geoips_for_all_pids():
  for pid in r.smembers("objectids"):
    lookup_geoips(pid,r)

def get_gchart_map_for_pid(pid,r, ignore_unknowns=True):
  gmap_t = """http://chart.apis.google.com/chart?cht=t&chs=440x220&chd=s:_&chf=bg,s,EAF7FE&chtm=world&chco=FFFFFF,FF0000,FFFF00,00FF00&chld=%s&chd=t:%s"""
  places = lookup_geoips_for_pid(pid,r)
  if ignore_unknowns and places.has_key("XX"):
    del places['XX']
  # find max and min
  maxv, minv = (0,100)
  for key in places:
    if places[key] > maxv:
      maxv = places[key]
    if places[key] < minv:
      minv = places[key]

  scale_factor = 100.0 / (maxv - minv)
  clist, cvalues = [], []
  for key in places:
    clist.append(key)
    cvalues.append(str(int((places[key]-minv)*scale_factor)))
  return gmap_t % ("".join(clist), ",".join(cvalues))


def lookup_geoips_for_pid(pid,r):
  places = {}
  total_ips = get_total_ip_usage(pid,r)
  receipts = map(lambda x: r.sadd("t:ip:%s" % pid, x), total_ips)
  r.delete("g:%s" % pid)
  for ip in total_ips:
    try:
      geocode = lookup_ip_geocode(ip,r)
      r.lpush("g:%s" % pid, geocode)
      if places.has_key(geocode):
        places[geocode] = places[geocode] + 1
      else:
        places[geocode] = 1
    except:
        print "Exception in geo lookup:"
        print '-'*60
        traceback.print_exc(file=sys.stdout)
        print '-'*60
  return places
