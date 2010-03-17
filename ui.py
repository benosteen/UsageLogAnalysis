import web

import re

from web.contrib.template import render_mako

from count import entity_existence, prefixes, rev_prefixes
from show_counts import entity_found_in_items, entity_lookup, save_set, browse_set, get_dateline_url, item_stats

from show_counts import get_entities_in_pid, entity_breakdown

from geolocate import get_gchart_map_for_pid 

from urllib import unquote

import simplejson

from redis import Redis

urls = ("/", "usage",
        "/geo/(.*)", "geo",
        "/pid/(.*)", "pid",
        "/report/(.*)", "report",
        "/entity(/.*)?", "entity",
        )
app = web.application(urls, globals())

render = render_mako(
        directories=['templates'],
        input_encoding='utf-8',
        output_encoding='utf-8',
        )

r = Redis()

def determine_tagtype(tag):
    if phrase in prefixes:
        return "s" # set
    elif phrase.count(":") == 1:
        if phrase.startswith("uuid") or phrase.startswith("ora"):
            return "i" # item
        else:
            return "e" # entity
    else:
        return "f" # unknown, try searching for the freetext as an entity

class usage:
    def GET(self):
        return 'Usage docs to appear here, once functionality is done'

class entity:
    def GET(self, id = None):
        if id:
            if id.find("%3A") != -1:
                id = ":".join(id.split("%3A"))
            if id.count(":") == 1 and id.split(":")[0] in ['n','i','s','f','k','type','col','tt']:
                tagtype = rev_prefixes.get(id.split(":")[0]) 
                return simplejson.dumps({tagtype:entity_breakdown(id, r)})
            else:
                results = {}
                for tagtype in prefixes:
                    tag = entity_existence(id, tagtype, r)
                    if tag:
                        results[tagtype] = entity_breakdown(tag, r)
                return simplejson.dumps(results)
        else:
            return render.entity()

    def POST(self, id):
        params = web.input()
        if "entity" in params:
            return self.GET(params['entity'])

class pid:
    def GET(self, id = None):
        if id:
            id = unquote(id)
            #if id.find("%3A") != -1:
            #    id = ":".join(id.split("%3A"))
            params = {'pid':id}
            params['dlist'], params['dates'], params['total'] = item_stats(id, r)
            if params['dlist']:
                params['sparkline_url'] = get_dateline_url(params['dlist'], params['dates'])
            else:
                params['sparkline_url'] = "http://ora.ouls.ox.ac.uk/ora_logo.png"
            #params['geousage_url'] = get_gchart_map_for_pid(id, r)
            params['entities'] = get_entities_in_pid(id, r)
            #return render.item(**params)
            return simplejson.dumps(params)
        else:
            return simplejson.dumps({'total':{'v':0,'d':0,'o':0}})

class geo:
    def GET(self, id):
        tagtype = determine_tagtype(id)
        if tagtype == "s":
            set_data = browse_set(id, r)

if __name__ == "__main__":
    app.run()

