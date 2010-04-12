#!/usr/bin/env python

from show_counts import analyse_past_days_dls
from redis import Redis

r=Redis()

results = analyse_past_days_dls(r, "current", days=30, size=20, 
                                exclude=["uuid:d590b7f4-e0a9-4957-9586-31089b914bd7",
                                         "uuid:aa490518-5a4b-4cb3-8882-a58620d8fe54"])
