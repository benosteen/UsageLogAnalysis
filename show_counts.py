import sys

from count import entity_existence, prefixes, rev_prefixes

from redis import Redis


from getmetadata import titlelookup

from ucsv import UnicodeWriter as csvwriter

from geolocate import get_gchart_map_for_pid

from datetime import datetime

goog_encoding = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

def combined_count(*args):
  total = 0
  for item in args:
    if isinstance(item, int):
      total = total + item
  return total

def get_dateline(dlist, dates):
  basedate = datetime.strptime(dlist[0], "%Y-%m-%d")
  enddate = datetime.strptime(dlist[-1], "%Y-%m-%d")
  activity = []
  for day in xrange((enddate-basedate).days+1):
    activity.append(0)
  for date in dlist:
    record = dates[date]
    index = (datetime.strptime(date, "%Y-%m-%d") - basedate).days
    activity[index] = record['v'] + record['d']
  return activity

def get_dateline_url(dlist, dates):
  data = get_dateline(dlist, dates)
  #return "http://chart.apis.google.com/chart?chs=300x125&cht=ls&chco=0077CC&chds=0,%s&chxt=x&chxl=0:|%s|%s|%s|%s&chd=t:%s" % (max(data), dlist[0], dlist[len(dlist)/3], dlist[len(dlist)*2/3], dlist[-1], ",".join(map(str,data)))
  maxdata = max(data)
  adjusted_data = map(lambda x: int(x/float(maxdata)*60.0), data)
  return "http://chart.apis.google.com/chart?chs=400x125&cht=ls&chco=0077CC&chds=0,%s&chxt=x&chxl=0:|%s|%s|%s|%s&chd=e:%s" % (maxdata, dlist[0], dlist[len(dlist)/3], dlist[len(dlist)*2/3], dlist[-1], "".join([str(goog_encoding[x]) for x in adjusted_data]))

def item_stats(pid, r):
  hits = {}
  dates = {}
  total = {'v':0, 'd':0, 'o':0}
  for hittype in ['v','d','o']:
    hits[hittype] = r.smembers("d%s:%s" % (hittype, pid))
    if hits[hittype]:
      for date in hits[hittype]:
        dayhits = r.scard("%s:%s:%s" % (date, pid, hittype))
        total[hittype] = total[hittype] + dayhits
        if not dates.get(date):
          dates[date] = {'v':0, 'd':0, 'o':0}
        dates[date][hittype] = dayhits
  dlist = dates.keys()
  dlist.sort()
  return dlist, dates, total

def print_item_stats(pid,r,gen_charts=False):
  dlist, dates, total = item_stats(pid, r)
  print "Results for %s" % pid
  print "Title: %s" % titlelookup(pid)
  print "Totals - Views: %(v)s, Downloads: %(d)s, Other: %(o)s" % total
  print "Breakdown:"
  for date in dlist:
    print "%s" % date + " - Views: %(v)s, Downloads: %(d)s, Other: %(o)s" % dates[date]
  if gen_charts:
    print "Google Chart url for the user breakdown - (Red - heaviest usage, yellow - weakest)"
    print "%s" % get_gchart_map_for_pid(pid, r)
    print "Google Sparkline for item activity"
    print get_dateline_url(dlist, dates)

def browse_set(phrase, r, limit, startswith):
  items = []
  for item in (r.smembers(phrase) or []):
    if limit == 0 or combined_count(r.get("t:views:%s" % item), r.get("t:dls:%s" % item)) > limit:
      label = r.get(item)
      if not startswith or label.startswith(startswith):
        items.append((label, item, r.get("t:views:%s" % item), r.get("t:dls:%s" % item), r.get("t:other:%s" % item)))
  return items

def print_browse_set(phrase, r, limit, startswith):
  print "Listing entire set for '%s'" % phrase
  print "Tag - views, downloads, other"
  for itemrow in browse_set(phrase, r, limit, startswith):
    print "%s(%s) - %s, %s, %s" % itemrow
  

def Gpiechart(valuelist, maxvalue, minvalue=0):
  urltemplate = "http://chart.apis.google.com/chart?cht=bvs&chxt=x,y&chd=t:%s&chs=1000x200&chl=0:|%s|1:|%s|%s&chds=%s,%s"
  t = []
  labels = []
  for item in valuelist:
    value, label = item.split("~")
    t.append(value)
    labels.append("&amp;".join(label.split("&")))
  return urltemplate % (",".join(t), "|".join(labels), minvalue, maxvalue, maxvalue, minvalue)

def save_set(phrase, r, limit, startswith, csvfile, verbose=False):
  if verbose:
    print "Saving set for '%s' in %s" % (phrase, csvfile)
  with open(csvfile, "w+") as csvhandle:
    csv_list = csvwriter(csvhandle)
    csv_list.writerow(["Label", "Views", "File Downloads", "Other interactions", "[Internal ID]"])
    tv, td, to = (0,0,0)
    maxv, maxd, maxo = (0,0,0)
    dv, dd, do = [],[],[]
    items = r.smembers(phrase)
    if not items:
        items = []
    for item in items:
      if limit == 0 or combined_count(r.get("t:views:%s" % item), r.get("t:dls:%s" % item)) > limit:
        label = r.get(item)
        if not startswith or label.startswith(startswith):
          views, dls, other = (r.get("t:views:%s" % item), r.get("t:dls:%s" % item), r.get("t:other:%s" % item))
          csv_list.writerow([label, views, dls, other, item])
          dv.append("%s~%s" % (views,label))
          dd.append("%s~%s" % (dls, label))
          do.append("%s~%s" % (other, label))
          if views > maxv:
            maxv = views
          if dls > maxd:
            maxd = dls
          if other > maxo:
            maxo = other
          try:
            tv = tv + int(views)
            td = td + int(dls)
            to = to + int(other)
          except:
            pass
    csv_list.writerow(["","","","",""])
    csv_list.writerow(["Totals", tv, td, to, ""])
    csv_list.writerow(["","","","",""])
    csv_list.writerow(["","","","",""])
    csv_list.writerow(["Note, that the labels indicate the usage statistics for the records which directly indicate that they have authors with that affiliation","","","",""])

def entity_breakdown(id, r):
  label = r.get(id)
  if label:
    # Entity exist exists
    totals = {'v':0, 'd':0, 'o':0}
    dates = {}
    items = entity_found_in_items(id, r)
    for pid in [x[1] for x in items]:
      piddlist, piddates, pidtotal = item_stats(pid, r)
      for key in pidtotal:
        totals[key] = totals[key] + pidtotal[key]
        for date in piddates:
          if not dates.get(date):
            dates[date] = {'v':0, 'd':0, 'o':0}
          for hittype in ['v','d','o']:
            dates[date][hittype] = dates[date][hittype] + piddates[date][hittype]
    dlist = dates.keys()
    dlist.sort()
    if dlist:
      sparkline_url = get_dateline_url(dlist, dates)
      return {'label':label,
                                            'items':items,
                                            'total':totals,
                                            'dates':dates,
                                            'sparkline_url':get_dateline_url(dlist, dates)}

    return {'label':label,
                                            'items':items,
                                            'total':totals,
                                            'dates':dates,
                                            'sparkline_url':""}

def entity_found_in_items(phrase, r):
  return [(titlelookup(pid), pid) for pid in (r.smembers("e:%s" % phrase) or [])]

def entity_lookup(phrase, r):
  return (phrase, r.get(phrase), r.get("t:views:%s" % phrase), r.get("t:dls:%s" % phrase), r.get("t:other:%s" % phrase))

def get_entities_in_pid(pid, r):
  entities = {}
  for entity in (r.smembers("e:%s" % pid) or []):
    label = r.get(entity)
    try:
      itemtype = rev_prefixes.get(entity.split(":")[0])
    except:
      itemtype = "Unknown"
    if not entities.has_key(itemtype):
      entities[itemtype] = []
    entities[itemtype].append((label, entity))
  return entities
  

def print_entity_report(phrase, r, gen_charts):
  print "%s = %s - %s, %s, %s" % entity_lookup(phrase, r)
  print "Entity %s found in the following items" % (phrase)
  for title, pid in entity_found_in_items(phrase, r):
    print '"%s" - %s' % (title, pid)
    if gen_charts:
      print "Geo-breakdown (yellow -> red) %s" % get_gchart_map_for_pid(pid, r)
if __name__ == "__main__":
  if len(sys.argv) == 1:
    print "You have to supply the thing you want to find the count for"
    print "Try browsing a set such as one of the following: %s" % ", ".join(prefixes.keys())
    sys.exit(2)

  limit = 0
  startswith = None
  csvfile = None
  gen_charts = None

  r = Redis()

  phrase_tokens = []
  for argv in sys.argv[1:]:
    if argv.startswith("--limit="):
      print "Only showing results with more than %s views and dls" % argv[8:]
      limit = int(argv[8:])
    elif argv.startswith("--start="):
      print "Only showing results where the label starts with %s" % argv[8:]
      startswith = argv[8:]
    elif argv.startswith("--csv="):
      print "Saving as CSV to file %s" % argv[6:]
      csvfile = argv[6:]
    elif argv.startswith("--geo"):
      print "Generating geo charts"
      gen_charts = True
    else:
      phrase_tokens.append(argv)

  phrase = " ".join(phrase_tokens)

  if phrase in prefixes:
    if csvfile:
      save_set(phrase, r, limit, startswith, csvfile, verbose=True)
    else:
      print_browse_set(phrase, r, limit, startswith)
  elif phrase.count(":") == 1:
    if phrase.startswith("uuid") or phrase.startswith("ora"):
      print_item_stats(phrase, r, gen_charts)
    else:
      print_entity_report(phrase, r, gen_charts)
  else:
    print "Trying to find freetext %s" % phrase
    for tagtype in prefixes:
      tag = entity_existence(phrase, tagtype, r)
      if tag  and (limit == 0 or combined_count(r.get("t:views:%s" % tag), r.get("t:dls:%s" % tag)) > limit):
        print "Found %s (type: %s) for %s" % (tag, tagtype, phrase)
        print "Views: %s, Downloads: %s, Other: %s" % (r.get("t:views:%s" % tag), r.get("t:dls:%s" % tag), r.get("t:other:%s" % tag))
        print "Entity %s(in %s) found in the following items" % (phrase, tagtype)
        for pid in (r.smembers("e:%s" % tag) or []):
          print '"%s" - %s' % (titlelookup(pid), pid)
          if gen_charts:
            print "Geo-breakdown (yellow -> red) %s" % get_gchart_map_for_pid(pid, r)
        print "------------------------------------------------------"
