# -*- coding: utf-8 -*-
import re
import sys
import urllib
import urlparse
import requests
import json
import xbmcgui
import xbmcplugin
#######################################

#classes
class Show():
	'SHOW'
	def __init__(self, showId, mediaType, title, link, thumbnail):
		self.showId = showId
		self.mediaType = mediaType
		self.title = title
		self.link = link
		self.thumbnail = thumbnail

class Stream():
	'STREAM'
	def __init__(self, streamId, mediaType, title, date, duration, link, thumbnail):
		self.streamId = streamId
		self.mediaType = mediaType
		self.title = title
		self.date = date
		self.duration = duration
		self.link = link
		self.thumbnail = thumbnail

class Live():
	'LIVE'
	def __init__(self, mediaType, title, link, thumbnail):
		self.mediaType = mediaType
		self.title = title
		self.link = link
		self.thumbnail = thumbnail
#######################################

#functions
def build_url(base, query):
	return base+'?'+urllib.urlencode(query)

def downloadSourceToString(url):
	rtvsloHtml = requests.get(url)
	return rtvsloHtml.text
	
def login(username, password):
	url = 'https://www.rtvslo.si/prijava'
	headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
	referurl = 'http://www.rtvslo.si/ttx'
	payload = {'action':'login', 'pass':password, 'referer':referurl, 'submit':'Prijava', 'user':username}

	s = requests.Session()
	s.post(url, headers=headers, data=payload)

	a = ''
	try:
		a = str(s.cookies['APISESSION'])
		if debug:
			xbmcgui.Dialog().ok('RTV Slovenija', 'Razhroščevanje vklopljeno - prijavljeni uporabnik: '+str(s.cookies['APISESSION_USER_NAME']))
	except:
		xbmcgui.Dialog().ok('RTV Slovenija', 'Prijava neuspešna!\n\nNekatere vsebine brez prijave na portalu rtvslo.si niso dosegljive.\nVnos podatkov za prijavo je mogoč v nastavitvah.')
	return a

def parseShowsToShowList(js):
	showList = []
	j = json.loads(js)
	j = j['response']['response']
	for show in j:
		showList.append(Show(show['id'], show['mediaType'], show['title'], show['link'], show['thumbnail']['show']))
	return showList

def parseShowToStreamList(js):
	streamList = []
	j = json.loads(js)
	j = j['response']['recordings']
	for stream in j:
		streamList.append(Stream(stream['id'], stream['mediaType'], stream['title'], stream['date'], stream['duration'], stream['link'], stream['images']['thumb']))
	return streamList

def parseStreamToPlaylist(js, folderType):
	j = json.loads(js)
	j = j['response']

	typeOK = True
	try:
		mediaType = j['mediaType']
		if folderType == 0 and mediaType == 'video':
			typeOK = False
		if folderType == 1 and mediaType == 'audio':
			typeOK = False
	except Exception as e:
		pass

	if typeOK:
		#newer video streams usually have this format
		try:
			playlist_type1 = j['addaptiveMedia']['hls']
			return playlist_type1
		except Exception as e:
			pass

		#audio streams and some older video streams have this format
		try:
			playlist_type2_part1 = j['mediaFiles'][0]['streamers']['http']
			playlist_type2_part2 = j['mediaFiles'][0]['filename']
			
			#replace some characters if needed
			if playlist_type2_part1.find('ava_archive02') > 0:
				playlist_type2_part1 = playlist_type2_part1.replace("ava_archive02", "podcast\/ava_archive02\/")
			else:
				regex_result = re.search(r'ava_archive[0-9]+', playlist_type2_part1)
				if regex_result is not None:
					playlist_type2_part1 = re.sub(r'ava_archive[0-9]+', regex_result.group()+'/', playlist_type2_part1)

			return playlist_type2_part1 + playlist_type2_part2
		except Exception as e:
			pass
	else:
		#something went wrong
		return False

def parseLiveStream(js):
	try:
		j = json.loads(js)
		j = j['response']
		live_media = j['mediaType']
		live_title = j['title']
		live_link = j['mediaFiles'][0]['streamer']+j['mediaFiles'][0]['file']
		live_thumb = j['images']['orig']
		return Live(live_media, live_title, live_link, live_thumb)
	except Exception as e:
		if debug:
			xbmcgui.Dialog().ok('RTV Slovenija', 'API response for live stream is invalid! :o')
		pass
#######################################

#main
if __name__ == "__main__":
	try:
		#get add-on base url
		base = str(sys.argv[0])
	
		#get add-on handle
		handle = int(sys.argv[1])

		#get add-on args
		args = urlparse.parse_qs(sys.argv[2][1:])

		#get content type
		#contentType == "audio" || "video"
		contentType = str(args.get('content_type')[0])
		contentTypeInt = -1
		if contentType == 'audio':
			contentTypeInt = 0
			xbmcplugin.setContent(handle, 'songs')
		elif contentType == 'video':
			contentTypeInt = 1
			xbmcplugin.setContent(handle, 'tvshows')

		#get mode and other parameters
		modeArg = args.get('mode', ['0'])
		mode = int(modeArg[0])
		letterArg = args.get('letter', ['A'])
		letter = letterArg[0]
		idArg = args.get('id', [''])
		id_ = idArg[0]
		pageArg = args.get('page', ['0'])
		page = int(pageArg[0])
		apiArg = args.get('api', [''])
		api = apiArg[0]
		
		#get settings
		username = xbmcplugin.getSetting(handle, 'username')
		password = xbmcplugin.getSetting(handle, 'password')
		debug = xbmcplugin.getSetting(handle, 'debug')
		if debug == 'true':
			debug = True
		else:
			debug = False
		
		#echo mode (debug)
		if debug:
			xbmcgui.Dialog().ok('RTV Slovenija', 'mode: '+str(mode))
#-----------------------
		#step 1: Collect underpants...
		if mode == 0:
			#mode == 0: list main menu (LIVE, ODDAJE, ARHIV)
			#login
			api = login(username, password)
			#LIVE
			li = xbmcgui.ListItem('V živo >')
			url = build_url(base, {'content_type': contentType, 'mode': 1, 'api': api})
			xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)
			#ARHIV 1/2
			li = xbmcgui.ListItem('Nove oddaje >')
			url = build_url(base, {'content_type': contentType, 'mode': 21, 'api': api})
			xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)
			#ARHIV 2/2
			li = xbmcgui.ListItem('Novi prispevki >')
			url = build_url(base, {'content_type': contentType, 'mode': 31, 'api': api})
			xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)
			#ODDAJE
			li = xbmcgui.ListItem('Arhiv oddaj >')
			url = build_url(base, {'content_type': contentType, 'mode': 11, 'api': api})
			xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)
#-----------------------
		#step 2: ...?...
		elif mode == 1:
			#mode == 1: list live streams (LIVE)
			mediaList = []
			if contentType == 'audio':
				mediaList = ['ra.a1', 'ra.val202', 'ra.ars', 'ra.rsi', 'ra.mb1', 'ra.kp', 'ra.capo', 'ra.mmr']#, 'ra.sport202']
			else:
				mediaList = ['tv.slo1', 'tv.slo2', 'tv.slo3', 'tv.kp1', 'tv.mb1', 'tv.mmctv']
			
			#api link
			liveApiA = 'http://api.rtvslo.si/ava/getLiveStream/'
			liveApiB = '?client_id=82013fb3a531d5414f478747c1aca622'
			
			loopIdx = 0
			for media in mediaList:
			
				#download response from rtvslo api
				js = downloadSourceToString(liveApiA+media+liveApiB)
				liveStream = parseLiveStream(js)
				
				#list live streams
				if isinstance(liveStream, Live):
					loopIdx = loopIdx + 1
					li = xbmcgui.ListItem(liveStream.title, iconImage=liveStream.thumbnail)
					li.setInfo('tvshows', {'tracknumber': loopIdx, 'title': liveStream.title})
					xbmcplugin.addDirectoryItem(handle=handle, url=liveStream.link, listitem=li)
#-----------------------
		elif mode == 11:
			#mode == 11: list letters menu (ODDAJE)
			oddaje = ['A','B','C','Č','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','Š','T','U','V','W','Z','Ž','0']
			for o in oddaje:
				li = xbmcgui.ListItem(o)
				url = build_url(base, {'content_type': contentType, 'mode': 12, 'letter': o, 'api': api})
				xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)
#-----------------------
		elif mode == 12:
			#mode == 12: letter selected, list shows (ODDAJE)

			#url parameters
			url_part1 = 'http://api.rtvslo.si/ava/getShowsSearch?client_id='
			url_part2 = '&sort=title&order=asc&pageNumber=0&pageSize=200&hidden=0&start='
			url_part3 = '&callback=jQuery111306175395867148092_1462381908718&_=1462381908719'
			client_id = '82013fb3a531d5414f478747c1aca622'
			start = letter

			#download response from rtvslo api
			js = downloadSourceToString(url_part1+client_id+url_part2+start+url_part3)

			#extract json from response
			x = js.find('({')
			y = js.rfind('});')
			if x < 0 or y < 0:
				if debug:
					xbmcgui.Dialog().ok('RTV Slovenija', 'API response is invalid! :o')
			else:
				#parse json to a list of shows
				js = js[x+1:y+1]
				showList = parseShowsToShowList(js)

				#list shows
				for show in showList:
					if (contentType == 'audio' and show.mediaType == 'radio') or (contentType == 'video' and show.mediaType == 'tv') or show.mediaType == 'mixed':
						li = xbmcgui.ListItem(show.title, iconImage=show.thumbnail)
						url = build_url(base, {'content_type': contentType, 'mode': 13, 'page': 0, 'id': show.showId, 'api': api})
						xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)
#-----------------------
		elif mode == 13:
			#mode == 13: show selected, list streams (ODDAJE)

			#url parameters
			url_part1 = 'http://api.rtvslo.si/ava/getSearch?client_id='
			url_part2 = '&pageNumber='
			url_part3 = '&pageSize=12&clip=show&sort=date&order=desc&from=1991-01-01&showId='
			url_part4 = '&callback=jQuery11130007442688502199202_1462387460339&_=1462387460342'
			client_id = '82013fb3a531d5414f478747c1aca622'
			page_no = page
			show_id = id_

			#download response from rtvslo api
			js = downloadSourceToString(url_part1+client_id+url_part2+str(page_no)+url_part3+show_id+url_part4)

			#extract json from response
			x = js.find('({')
			y = js.rfind('});')
			if x < 0 or y < 0:
				if debug:
					xbmcgui.Dialog().ok('RTV Slovenija', 'API response is invalid! :o')
			else:
				#parse json to a list of streams
				js = js[x+1:y+1]
				streamList = parseShowToStreamList(js)

				#find playlists and list streams
				loopIdx = 0
				for stream in streamList:
					
					#url parameters
					url_part1 = 'http://api.rtvslo.si/ava/getRecording/'
					recording = stream.streamId
					url_part2 = '?callback=ava_666&client_id='
					client_id = '82013fb3a531d5414f478747c1aca622'
					url_part3 = '&session_id='

					#download response from rtvslo api
					js = downloadSourceToString(url_part1+recording+url_part2+client_id+url_part3+api)
					
					#extract json from response
					x = js.find('({')
					y = js.rfind('});')
					if x < 0 or y < 0:
						if debug:
							xbmcgui.Dialog().ok('RTV Slovenija', 'API response is invalid! :o')
					else:
						#parse json to get a playlist
						js = js[x+1:y+1]
						playlist = parseStreamToPlaylist(js, contentTypeInt)

						#list stream
						loopIdx = loopIdx + 1
						li = xbmcgui.ListItem(stream.date+' - '+stream.title, iconImage=stream.thumbnail)
						if contentTypeInt == 0:
							li.setInfo('music', {'tracknumber': loopIdx, 'duration': stream.duration, 'title': stream.date+' - '+stream.title})
						elif contentTypeInt == 1:
							li.setInfo('video', {'tracknumber': loopIdx, 'duration': stream.duration, 'title': stream.date+' - '+stream.title})
						if playlist:
							xbmcplugin.addDirectoryItem(handle=handle, url=playlist, listitem=li)

				#show next page marker if needed
				if len(streamList) > 0:
					page_no = page_no + 1
					li = xbmcgui.ListItem('> '+str(page_no)+' >')
					url = build_url(base, {'content_type': contentType, 'mode': mode, 'page': page_no, 'id': show_id, 'api': api})
					xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)
#-----------------------
		elif mode == 21:
			#mode == 21: list new shows (ARHIV 1/2)

			#url parameters
			url_part1 = 'http://api.rtvslo.si/ava/getSearch?client_id='
			url_part2 = '&q=&showTypeId=&sort=date&order=desc&pageSize=12&pageNumber='
			url_part3 = '&source=&hearingAid=0&clip=show&from=2007-01-01&to=&WPId=&zkp=0&callback=jQuery11130980077945755083_1462458118383&_=1462458118384'
			client_id = '82013fb3a531d5414f478747c1aca622'
			page_no = page

			#download response from rtvslo api
			js = downloadSourceToString(url_part1+client_id+url_part2+str(page_no)+url_part3)

			#extract json from response
			x = js.find('({')
			y = js.rfind('});')
			if x < 0 or y < 0:
				if debug:
					xbmcgui.Dialog().ok('RTV Slovenija', 'API response is invalid! :o')
			else:
				#parse json to a list of streams
				js = js[x+1:y+1]
				streamList = parseShowToStreamList(js)

				#find playlists and list streams
				loopIdx = 0
				for stream in streamList:
					if (contentTypeInt == 0 and stream.mediaType == 'audio') or (contentTypeInt == 1 and stream.mediaType == 'video'):
						#url parameters
						url_part1 = 'http://api.rtvslo.si/ava/getRecording/'
						recording = stream.streamId
						url_part2 = '?callback=ava_666&client_id='
						client_id = '82013fb3a531d5414f478747c1aca622'
						url_part3 = '&session_id='

						#download response from rtvslo api
						js = downloadSourceToString(url_part1+recording+url_part2+client_id+url_part3+api)

						#extract json from response
						x = js.find('({')
						y = js.rfind('});')
						if x < 0 or y < 0:
							if debug:
								xbmcgui.Dialog().ok('RTV Slovenija', 'API response is invalid! :o')
						else:
							#parse json to get a playlist
							js = js[x+1:y+1]
							playlist = parseStreamToPlaylist(js, contentTypeInt)

							#list stream
							loopIdx = loopIdx + 1
							li = xbmcgui.ListItem(stream.date+' - '+stream.title, iconImage=stream.thumbnail)
							if contentTypeInt == 0:
								li.setInfo('music', {'tracknumber': loopIdx, 'duration': stream.duration, 'title': stream.date+' - '+stream.title})
							elif contentTypeInt == 1:
								li.setInfo('video', {'tracknumber': loopIdx, 'duration': stream.duration, 'title': stream.date+' - '+stream.title})
							if playlist:
								xbmcplugin.addDirectoryItem(handle=handle, url=playlist, listitem=li)

				#show next page marker if needed
				if len(streamList) > 0:
					page_no = page_no + 1
					li = xbmcgui.ListItem('> '+str(page_no)+' >')
					url = build_url(base, {'content_type': contentType, 'mode': mode, 'page': page_no, 'api': api})
					xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)
#-----------------------
		elif mode == 31:
			#mode == 31: list new news stories (ARHIV 2/2)

			#url parameters
			url_part1 = 'http://api.rtvslo.si/ava/getSearch?client_id='
			url_part2 = '&q=&showTypeId=&sort=date&order=desc&pageSize=12&pageNumber='
			url_part3 = '&source=&hearingAid=0&clip=clip&from=2007-01-01&to=&WPId=&zkp=0&callback=jQuery111307342043845078507_1462458568679&_=1462458568680'
			client_id = '82013fb3a531d5414f478747c1aca622'
			page_no = page

			#download response from rtvslo api
			js = downloadSourceToString(url_part1+client_id+url_part2+str(page_no)+url_part3)

			#extract json from response
			x = js.find('({')
			y = js.rfind('});')
			if x < 0 or y < 0:
				if debug:
					xbmcgui.Dialog().ok('RTV Slovenija', 'API response is invalid! :o')
			else:
				#parse json to a list of streams
				js = js[x+1:y+1]
				streamList = parseShowToStreamList(js)

				#find playlists and list streams
				loopIdx = 0
				for stream in streamList:
					if (contentTypeInt == 0 and stream.mediaType == 'audio') or (contentTypeInt == 1 and stream.mediaType == 'video'):
						#url parameters
						url_part1 = 'http://api.rtvslo.si/ava/getRecording/'
						recording = stream.streamId
						url_part2 = '?callback=ava_666&client_id='
						client_id = '82013fb3a531d5414f478747c1aca622'
						url_part3 = '&session_id='

						#download response from rtvslo api
						js = downloadSourceToString(url_part1+recording+url_part2+client_id+url_part3+api)

						#extract json from response
						x = js.find('({')
						y = js.rfind('});')
						if x < 0 or y < 0:
							if debug:
								xbmcgui.Dialog().ok('RTV Slovenija', 'API response is invalid! :o')
						else:
							#parse json to get a playlist
							js = js[x+1:y+1]
							playlist = parseStreamToPlaylist(js, contentTypeInt)

							#list stream
							loopIdx = loopIdx + 1
							li = xbmcgui.ListItem(stream.date+' - '+stream.title, iconImage=stream.thumbnail)
							if contentTypeInt == 0:
								li.setInfo('music', {'tracknumber': loopIdx, 'duration': stream.duration, 'title': stream.date+' - '+stream.title})
							elif contentTypeInt == 1:
								li.setInfo('video', {'tracknumber': loopIdx, 'duration': stream.duration, 'title': stream.date+' - '+stream.title})
							if playlist:
								xbmcplugin.addDirectoryItem(handle=handle, url=playlist, listitem=li)

				#show next page marker if needed
				if len(streamList) > 0:
					page_no = page_no + 1
					li = xbmcgui.ListItem('> '+str(page_no)+' >')
					url = build_url(base, {'content_type': contentType, 'mode': mode, 'page': page_no, 'api': api})
					xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)
#-----------------------
		#step 3: ...profit!
		else:
			if debug:
				xbmcgui.Dialog().ok('RTV Slovenija', 'Invalid mode: '+str(mode))

		#write contents
		xbmcplugin.endOfDirectory(handle)

	except Exception as e:
		if debug:
			xbmcgui.Dialog().ok('RTV Slovenija', 'Error: \n'+e.message)
