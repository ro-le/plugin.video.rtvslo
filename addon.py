import sys
import urlparse
import re
import urllib
import urllib2
import xml.etree.ElementTree as ET
import xbmcgui
import xbmcplugin

#scrape podcast info from rtvslo.si
class Podcast:
	'Audio/video podcast'
	def __init__(self):
		self.name = ""
		self.url = ""
		self.img = ""
		self.type = -1	#0 = audio, 1 = video

#parse media info from xml
class Media:
	'Podcast media info'
	def __init__(self):
		self.title = ""
		self.date = ""
		self.url = ""
		self.length = 0
		self.desc = ""
		self.type = -1	#0 = audio, 1 = video

	def isValid(self):
		#return True
		if self.title is None:
			return False
		if self.date is None:
			return False
		if self.url is None:
			return False
		if self.length is None:
			return False
		if self.type == -1:
			return False
		return True

#scrapes xml links (and some additional info) of all available podcasts
def scrapeRtvSlo(rtvsloUrl, podcastLink, contentType):

	#variables
	mediaType = -1
	audioTag = "Avdio podcasti"
	videoTag = "Video podcasti"
	podcastList = []
	duplicateList = []

	#connect
	rtvsloHtml = urllib2.urlopen(rtvsloUrl)
	rtvsloData = rtvsloHtml.read().split("\n")
	rtvsloHtml.close()

	#scrape
	for line in rtvsloData:

		#figure out media type
		if audioTag in line:
			mediaType = 0
		elif videoTag in line:
			mediaType = 1

		#find podcast xml files
		if podcastLink in line:

			#create new object
			p = Podcast()

			#regex html tags
			stripped = line.strip()
			tags = re.findall('[a-z]+?=".+?"', stripped)

			#update key-value attribute pairs
			for tag in tags:
				attr = tag.split("=")
				key = attr[0]
				val = attr[1].strip("\"")
				if key == "href":
					p.url = val
				elif key == "title":
					p.name = escape(val)
				elif key == "src":
					p.img = val

			#append podcast to array (if not a duplicate and if proper type)
			if p.name not in duplicateList:
				if mediaType == contentType:
					p.type = mediaType
					podcastList.append(p)
					duplicateList.append(p.name)
	return podcastList

#read and parse podcast xml
def parsePodcastXml(p):

	#variables
	mediaType = -1
	mediaList = []

	#connect
	podcastXml = urllib2.urlopen(p.url)
	podcastData = podcastXml.read()
	podcastXml.close()

	#parse
	root = ET.fromstring(podcastData)
	channel = root.find("channel")
	if channel is not None:
		item = channel.findall("item")
		if item is not None:
			for i in item:

				#create Media object
				m = Media()

				#update title
				title = i.find("title")
				if title is not None:
					m.title = escape(title.text)
				#update date
				pubDate = i.find("pubDate")
				if pubDate is not None:
					dt = pubDate.text.split()
					m.date = dt[1]+"."+getMonth(dt[2])+"."+dt[3]
				#update description
				desc = i.find("description")
				if desc is not None:
					m.desc = escape(desc.text)
				#update url, length and media type
				enclosure = i.find("enclosure")
				if enclosure is not None:
					url = enclosure.get("url")
					if url is not None:
						m.url = url
					avType = enclosure.get("type")
					if avType is not None:
						mediaType = -1
						if avType == "audio/mpeg":
							mediaType = 0
						elif avType == "video/mp4":
							mediaType = 1
						m.type = mediaType
					length = enclosure.get("length")
					if length is not None:
						laudio = int(int(length)/16000)
						lvideo = int(int(length)/117000)
						if mediaType == 0:
							m.length = laudio	#s
						elif mediaType == 1:
							m.length = lvideo/60	#min
						

				#add to list if valid
				if m.isValid():
					mediaList.append(m)
	return mediaList

#convert month from string to int
def getMonth(m):
	mDict = {'Jan': '1',
			'Feb': '2',
			'Mar': '3',
			'Apr': '4',
			'May': '5',
			'Jun': '6',
			'Jul': '7',
			'Aug': '8',
			'Sep': '9',
			'Oct': '10',
			'Nov': '11',
			'Dec': '12'}
	return mDict.get(m)

#escapes some weird characters
def escape(s):
	s = s.replace('<br />', ' ')
	s = s.replace('&lt;', '<')
	s = s.replace('&gt;', '>')
	s = s.replace('&amp;', '&')
	s = s.replace('&#039;', '\'')
	s = s.replace('&quot;', '"')
	s = s.replace('&nbsp;', ' ')
	s = s.replace('&#x26;', '&')
	s = s.replace('&#x27;', '\'')
	return s

def build_url(base, query):
	return base+'?'+urllib.urlencode(query)

#MAIN
if __name__ == "__main__":
	try:
		#get add-on base url
		base = str(sys.argv[0])
		
		#get add-on handle
		handle = int(sys.argv[1])

		#get add-on args
		args = urlparse.parse_qs(sys.argv[2][1:])

		#get content type
		#contentType == "audio"
		#contentType == "video"
		contentType = str(args.get('content_type')[0])
		contentTypeInt = -1
		if contentType == 'audio':
			contentTypeInt = 0
			xbmcplugin.setContent(handle, 'songs')
		elif contentType == 'video':
			contentTypeInt = 1
			xbmcplugin.setContent(handle, 'tvshows')

		#get mode
		#mode == -1: list available podcasts
		#mode >= 0: list available media from selected podcast
		modeArg = args.get('mode', ['-1'])
		mode = int(modeArg[0])

		#variables
		rtvsloUrl = "http://www.rtvslo.si/podcast"
		podcastUrl = "http://podcast.rtvslo.si/"
		podcastList = []
		mediaList = []

		#step 1: Collect underpants...
		podcastList = scrapeRtvSlo(rtvsloUrl, podcastUrl, contentTypeInt)
		if mode == -1:
			pIdx = 0
			for p in podcastList:
				li = xbmcgui.ListItem(p.name, iconImage=p.img)
				url = build_url(base, {'content_type': contentType, 'mode': pIdx})
				xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)
				pIdx = pIdx + 1

		#step 2: ...?...
		#step 3: ...profit!
		elif len(podcastList) > mode:
			p = podcastList[mode]
			mediaList = parsePodcastXml(p)
			for m in mediaList:
				li = xbmcgui.ListItem(m.date+" "+m.title, iconImage=p.img)
				if contentTypeInt == 0:
					li.setInfo('music', {'duration': m.length})
				elif contentTypeInt == 1:
					li.setInfo('video', {'duration': m.length})
				xbmcplugin.addDirectoryItem(handle=handle, url=m.url, listitem=li)
		xbmcplugin.endOfDirectory(handle)

	except Exception as e:
		xbmcgui.Dialog().ok('RTVSlo.si', 'OMG, an error has occured?!\n'+e.message)
