import requests
from google.transit import gtfs_realtime_pb2
from protobuf_to_dict import protobuf_to_dict
import datetime
import csv
from dateutil import tz
import time
import os

feed = gtfs_realtime_pb2.FeedMessage()
mtaKey = API_KEY

def stops():
	r = requests.get('http://web.mta.info/developers/data/nyct/subway/Stations.csv')
	sp = list(csv.reader(r.text.split('\r\n')))

	t = [dict(zip(sp[0],k)) for k in sp[1:]]

	return {k['GTFS Stop ID']:k for k in t[:-1]}

def lineIds():
	l = list(csv.reader(open('lineref.csv','rb')))
	return {k[0]:k[1] for k in l}

def retFeed(feedId):
	url = 'http://datamine.mta.info/mta_esi.php?key={}&feed_id={}'.format(mtaKey,str(feedId))
	r = requests.get(url)
	feed.ParseFromString(r.content)
	f = protobuf_to_dict(feed)
	return f

def pTime(timeInt):
	#time is gmt - convert it to EST before returning it
	from_zone = tz.gettz('UTC')
	to_zone = tz.gettz('America/New_York')
	utc = datetime.datetime.utcfromtimestamp(timeInt)
	utc = utc.replace(tzinfo=from_zone)
	return utc.astimezone(to_zone)

def parseupdate(updatein,line,ns):
	if 'stop_time_update' in updatein['trip_update'].keys():
		if updatein['trip_update']['trip']['route_id'] == line:
			if updatein['trip_update']['trip']['trip_id'][-1] == ns:
				return True

def getTimes(line,stop,ns):
	sData = allStops[stop]
	lId = allIds[line]
	f = retFeed(lId)
	e = f['entity']
	updates = [k for  k in e if 'trip_update' in k]
	requestedRoute = [k for k in updates if parseupdate(k,line,ns)]

	stoparrivals = list()

	for r in requestedRoute:
		update = r['trip_update']
		stoptimes = update['stop_time_update']
		if stop in [k['stop_id'][:-1] for k in stoptimes]:
			#the stop is coming up in the future of this trip
			stoparrival = pTime([fs['arrival']['time'] for fs in stoptimes if fs['stop_id'][:-1] == stop][0])
			stoparrivals.append(stoparrival)

	#don't think this needs to be done, but for good measure:
	stoparrivals.sort()
	return stoparrivals

def minsAway(timeIn):
	now = pTime(time.time())
	d = timeIn - now
	if now > timeIn:
		return 0
	else:
		return d.seconds // 60

allStops = stops()
allIds = lineIds()
s = 'M16'


while True:
	try:
		js = getTimes('J',s,'S')


		print js

		ms = getTimes('M',s,'S')

		nextj = minsAway(js[0])
		followingj = minsAway(js[1])
		nextm = minsAway(ms[0])
		followingm = minsAway(ms[1])

		if nextj == 0:
			nextj = 'arriving now'
		else:
			nextj = str(nextj) + ' mins away'

		if nextm == 0:
			nextm = 'arriving now'
		else:
			nextm = str(nextm) + ' mins away'

		now = datetime.datetime.now().strftime('%H:%M')

		jstr = ' J: {}'.format(nextj)
		mstr = ' M: {}'.format(nextm)
		cmdstr = 'sudo /home/pi/rpi-rgb-led-matrix/examples-api-use/scrolling-text-example --led-rows 16 -f /home/pi/rpi-rgb-led-matrix/fonts/6x13B.bdf -s 5 -l 1'
		os.system(cmdstr + jstr)
		os.system(cmdstr + mstr)
		print jstr
		print mstr
		#time.sleep()
	except:
		time.sleep(2)
