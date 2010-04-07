# -*- coding: utf-8 -*-
import web

import re

from web.contrib.template import render_mako

from count import entity_existence, prefixes, rev_prefixes
from show_counts import entity_found_in_items, entity_lookup, save_set, browse_set, get_dateline_url, item_stats

from getmetadata import titlelookup

from show_counts import get_entities_in_pid, entity_breakdown, get_ora_totals

from geolocate import get_gchart_map_for_pid 

from urllib import unquote

import simplejson

from redis import Redis

urls = ("/", "usage",
        "/geo/(.*)", "geo",
        "/pid(/.*)?", "pid",
        "/browse(/.*)?", "browse",
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
        return render.home(c = get_ora_totals(r))

class entity:
    def GET(self, id = None, format = "json"):
        options = web.input()
        id = id or options.get("entity")
        if id:
            if id.startswith("/"):
                id = id[1:]
            if id.find("%3A") != -1:
                id = ":".join(id.split("%3A"))
            format = options.get("format", format)
            if id.count(":") == 1 and id.split(":")[0] in ['n','i','s','f','k','type','col','tt']:
                tagtype = rev_prefixes.get(id.split(":")[0])
                eb = entity_breakdown(id, r)
                eb['eid'] = id
                if format == "html":
                    return render.entity_view(entities={tagtype:eb})
                return simplejson.dumps({tagtype:eb})
            else:
                results = {}
                for tagtype in prefixes:
                    tag = entity_existence(id, tagtype, r)
                    if tag:
                        results[tagtype] = entity_breakdown(tag, r)
                        results[tagtype]['eid'] = tag
                if format == "html":
                    return render.entity_view(entities=results)
                return simplejson.dumps(results)
        else:
            return render.entity_form()

    def POST(self, id):
        params = web.input()
        if "entity" in params:
            return self.GET(id = params['entity'], format=params.get("format","html"))

class pid:
    def GET(self, id = None, format = 'json'):
        if id:
            if id.startswith("/"):
                id = id[1:]
            id = unquote(id)
            #if id.find("%3A") != -1:
            #    id = ":".join(id.split("%3A"))
            params = {'pid':id}
            params['label'] = titlelookup(id)
            params['dlist'], params['dates'], params['total'] = item_stats(id, r)
            if params['dlist']:
                params['sparkline_url'] = get_dateline_url(params['dlist'], params['dates'])
            else:
                params['sparkline_url'] = "http://ora.ouls.ox.ac.uk/ora_logo.png"
            params['entities'] = get_entities_in_pid(id, r)
            options = web.input()
            if 'geo' in options:
                params['geousage_url'] = get_gchart_map_for_pid(id, r)
            format = options.get('format', format)
            if format == "html":
                return render.item(**params)
            return simplejson.dumps(params)
        else:
            return render.item_form()

    def POST(self, id=None):
        params = web.input()
        if "pid" in params:
            return self.GET(params['pid'], format=params.get('format', 'html'))

class browse:
    def GET(self, id = None, format = "json", startswith=""):
        options = web.input()
        id = id or options.get("type")
        if id:
            if id.startswith("/"):
                id = id[1:]
            if id.find("%3A") != -1:
                id = ":".join(id.split("%3A"))
            format = options.get("format", format)
            bset = browse_set(id, r, 0, startswith)
            if format == "html":
                return render.browse_set(bset=bset, startswith=startswith, settype=id)
            return simplejson.dumps({'startswith':startswith,
                                     'settype':id,
                                     'bset':bset})
        else:
            return render.browse_form()

    def POST(self, id):
        params = web.input()
        if "type" in params:
            if "startswith" in params:
                return self.GET(id = params['type'], format=params.get("format","html"), startswith=params.get("startswith",""))
            return self.GET(id = params['type'], format=params.get("format","html"))

class geo:
    def GET(self, id):
        tagtype = determine_tagtype(id)
        if tagtype == "s":
            set_data = browse_set(id, r)

if __name__ == "__main__":
    app.run()

