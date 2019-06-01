from datetime import datetime

from pytz import timezone

import pytz


# utc = pytz.utc
# print(utc.zone)

# us = timezone('US/Eastern')
# ua = timezone('EST/UTC+3')
ua2 = timezone('Europe/Kiev')




# print(datetime.now(us))
# print(datetime.now(ua))
# print(datetime.now(aaa))
# print(datetime.now(bbb))

# print(datetime.now(us).strftime('%H:%M'))
# print(datetime.now(ua).strftime('%H:%M'))
print(datetime.now(ua2).strftime('%H:%M'))



# asd = timezone()
# print(ua.localize(datetime.now()))
