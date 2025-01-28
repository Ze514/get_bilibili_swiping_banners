import time
import re
import urllib.request, urllib.error
from bs4 import BeautifulSoup
from random import choice
from datetime import datetime
baseurl = "https://bilibili.com/"
location = 'D:\\btio\\test\\'
def geturl(url):
	ua_file = open('.\\uapool.txt', 'r')
	ua_lines = ua_file.readlines()
	ua = choice(ua_lines)
	ua = ua[:-1]
	print("\n",ua,"\n")
	headers = {'User-Agent': ua}
	req = urllib.request.Request(url, headers=headers)
	html = ""
	try:
		resp = urllib.request.urlopen(req)
		html = resp.read().decode("utf-8")
	except urllib.error.URLError as e:
		if hasattr(e, "code") or hasattr(e, "reason"):
			print("enter retry now.\n")
			geturl(baseurl)	
	return html
def analysisdata(url):
	saver = []
	html = geturl(url)
	soup = BeautifulSoup(html, "html5lib")
	item = soup.findAll("picture", attrs={"class": "v-img carousel-inner__img"})
	print(item)
	for e in item:
		e=str(e)
		e=re.findall("srcset=(.*?)@",e)
		e.pop(-1)
		for i in e:
			saver.append(i)
	return saver
def main():
	download(analysisdata(baseurl))
def download(url_list):
	model = r"https:"
	for var in url_list:
		alternative=[]
		now=datetime.now()
		dt_string=now.strftime("%Y-%m-%d--%H-%M-%S")
		var=var[1:]
		alternative.append(model)
		alternative.append(var)
		name=location + dt_string + ".png"
		new_str=''.join(alternative)
		start=time.time()
		urllib.request.urlretrieve(new_str,name)
		end=time.time()
		print(f"time elimpsed {end - start} seconds, file {name} successfully saved!")
		time.sleep(1)
	print("\n\nfiles are saved in the dictionary:\n\n"+location)
if __name__ == '__main__':
	main()