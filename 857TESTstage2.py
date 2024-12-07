import time
import os
import re
import urllib.request, urllib.error
from bs4 import BeautifulSoup
import random
from datetime import datetime
baseurl = "https://bilibili.com/"
def geturl(url):
	ua_file = open('D:\\pyprojects\\uapool.txt', 'r')
	ua_lines = ua_file.readlines()
	count = len(ua_lines)
	random_int = 0
	random_int = random.randint(0,count-1)
	print(random_int)
	ua = ua_lines[random_int]
	ua_file.close()
	ua2 = re.sub(r'\n', "", ua)
	headers = {'User-Agent': ua2}
	req = urllib.request.Request(url, headers=headers)
	html = ""
	try:
		resp = urllib.request.urlopen(req)
		html = resp.read().decode("utf-8")
	except urllib.error.URLError as e:
		if hasattr(e, "code"):
			print(e.code)
		if hasattr(e, "reason"):
			print(e.reason)
	return html
def analysisdata(url):
	html = geturl(url)
	soup = BeautifulSoup(html, "html5lib")
	item = 0
	item = soup.findAll("picture", attrs={"class": "v-img carousel-inner__img"})
	item = str(item)
	b = re.sub(r'<picture.*?>', "", item)
	c = re.sub(r'<source.*?', "", b)
	d = re.sub(r'<!--\[-->.*?',"", c)
	e = re.sub(r'<!--\]-->.*?', "", d)
	f = re.sub(r'\[.*?', "", e)
	g = re.sub(r'\].*?', "", f)
	h = re.sub(r'type="image/avif".*?', "", g)
	i = re.sub(r'loading="eager" onerror="typeof window.imgOnError \=\=\= \'function\' \&amp\;\&amp\; window.imgOnError\(this\)" onload="fsrCb\(\);firstSwipeLoaded\([0-9]\)"', "", h)
	j = re.sub(r'/>.*?', "", i)
	k = re.sub(r'type="image/webp".*?', "", j)
	l = re.sub(r'</picture>.*?', "", k)
	m = re.sub(r'<img alt=".*?', "", l)
	result = re.findall(r'srcset.*?avif".*?$',m)
	fin_result = result.pop(-1)
	fin_result = re.sub(r',.*?', "", fin_result)
	print(fin_result)
	fin_result = re.findall(r'srcset=(.*?)\@', fin_result)
	print("")
	print(fin_result)
	if os.path.exists("D:\\btio") is False:
		os.mkdir("D:\\btio")
	if os.path.exists("D:\\btio\\output.txt") is True:
		os.remove("D:\\btio\\output.txt")
	for inst in fin_result:
		with open("D:\\btio\\output.txt",'a') as file:
			file.write(inst)
	return ""
def main():
	print(analysisdata(baseurl))
	print("https:")
	download()
def download():
	cache = open("D:\\btio\\output.txt", 'r')
	links_lines = cache.read()
	cache.close()
	output = re.findall(r'//(.*?)//',links_lines)
	count = 0
	count = len(output)
	saved_path = 'D:\\btio\\test\\'
	for i in range(0,count-1):
		time.sleep(1.5)
		piclink = output[i]
		piclink1 = piclink[:-1]
		piclink1 = "https://"+piclink1
		filename = "banners"
		filename = str(filename)
		now = datetime.now()
		dt_string = now.strftime("%y-%m-%d--%H-%M-%S")
		filename1 = filename + dt_string + ".png"
		filename1 = saved_path + filename1
		urllib.request.urlretrieve(piclink1,filename1)
		print("file",filename1,"successfully saved!")
if __name__ == '__main__':
	main()