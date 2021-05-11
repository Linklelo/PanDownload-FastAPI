import re
import json
import urllib
import requests
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from SVIPInfo import *

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
templates = Jinja2Templates(directory="templates")

index_url = "http://127.0.0.1:8000/"

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "index_url": index_url})

@app.post("/", response_class=HTMLResponse)
async def main(request: Request, surl: str=Form(...), pwd: str=Form(None), dir: str=Form(None), randsk: str=Form(None)):
    # print(surl, pwd)
    if None == randsk:
        if None != pwd:
            randsk = verifyPwd(surl, pwd)
        else:
            randsk = verifyPwd(surl)
    signJson = getSign(surl, randsk)
    if signJson != True:
        # print(signJson)
        fesign = fetchSign(surl, randsk)
        # print(fesign)
        sign = fesign["sign"]
        timestamp = fesign["timestamp"]
        shareid = str(signJson["shareid"])
        uk = str(signJson.get("share_uk")) if signJson.get("visitor_uk", None) == None else str(signJson.get("uk"))
        # uk = str(signJson["uk"])
        filejson = getFileList(shareid,uk,randsk,dir)
        if filejson["errno"] == 0:
            return templates.TemplateResponse("file.html", {"request": request, "index_url": index_url, "file_list": filejson["list"],
                                                    "surl": surl, "pwd": pwd, "randsk": randsk, "timestamp": timestamp, "sign": sign, "shareid": shareid, "uk": uk})
        else:
            return templates.TemplateResponse("error.html", {"request": request, "index_url": index_url})
    else:
        return templates.TemplateResponse("error.html", {"request": request, "index_url": index_url})
    
@app.post("/download", response_class=HTMLResponse)
async def download(request: Request, fs_id: str=Form(...), time: str=Form(...), sign: str=Form(...), randsk: str=Form(...), share_id: str=Form(...), uk: str=Form(...)):
    dlink = getDlink(fs_id, time, sign, randsk, share_id, uk)
    if dlink["errno"] == 0:
        reallink = getRealLink(dlink["list"][0]["dlink"])
        filename = dlink["list"][0]['server_filename']
        return templates.TemplateResponse("download.html", {"request": request, "index_url": index_url, "download": True, "realLink": reallink[7:], "filename": filename})
    else:
        return templates.TemplateResponse("download.html", {"request": request, "index_url": index_url, "download": False})
    
@app.get("/help", response_class=HTMLResponse)
async def help(request: Request):
    return templates.TemplateResponse("help.html", {"request": request, "index_url": index_url})

def verifyPwd(surl, pwd=None):
    if pwd :
        try:
            headers = {
            'User-Agent':'netdisk',
            'Referer':'https://pan.baidu.com/disk/home'
            }
            data = {
                    "pwd": pwd
                    }
            res = requests.post("https://pan.baidu.com/share/verify?channel=chunlei&clienttype=0&web=1&app_id=250528&surl={}".format(surl[1:]), data=data, headers=headers, timeout=10)
            if res.json()["errno"] == 0:
                return res.json()["randsk"]
            else:
                return True
        except Exception as ex:
            print("verifyPwd1: ", ex)
            return True   
    else:
        try:
            res = requests.head("https://pan.baidu.com/s/" + surl, headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.514.1919.810 Safari/537.36'}, timeout=10)
            if res.status_code == 302:
                return True
            if "BDCLND" in res.headers:
                return res.headers["Set-Cookie"].split("BDCLND=")[1].split(";")[0]
            else:
                return res.headers["Yme"]
        except Exception as e:
            print("verifyPwd2: ", e)
            return True
def fetchSign(surl, randsk):
    try:
        headers = {
            'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.514.1919.810 Safari/537.36',
            'Cookie':'BDUSS=' + BDUSS + '; ' +  'STOKEN=' + STOKEN + '; BDCLND=' + randsk
        }
        res = requests.get("https://pan.baidu.com/share/tplconfig?surl=" + surl + "&fields=sign,timestamp&channel=chunlei&web=1&app_id=250528&clienttype=0", headers=headers, timeout=10)
        # print(res.json())
        return res.json().get("data")
    except Exception as e:
        print("fetchSign: ", e)
        return True

def getSign(surl, randsk):
    if randsk == True:
        return True
    try:
        headers = {
            'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.514.1919.810 Safari/537.36',
            'Cookie':'BDUSS=' + BDUSS + '; ' +  'STOKEN=' + STOKEN + '; BDCLND=' + randsk
        }
        res = requests.get("https://pan.baidu.com/s/" + surl, headers=headers, timeout=10)
        # print(res.text)
        re_1 = re.findall(re.compile(r'yunData.setData\(({.+)\);'), res.text)
        if re_1:
            return json.loads(re_1[0])
        else:
            return json.loads(re.findall(re.compile(r'locals.mset\(({.+)\);'), res.text)[0])
    except Exception as e:
        print("getSign: ", e)
        return True

def getFileList(shareid, uk, randsk, dir):
    try:
        if dir:
            url = 'https://pan.baidu.com/share/list?app_id=250528&channel=' + 'chunlei&clienttype=0&desc=0&num=100&order=name&page=1&root=' + str(int((not dir))) + '&shareid=' + shareid + '&showempty=0&uk=' + uk + '&dir=' + urllib.parse.quote(dir) + '&web=1'
        else:
            url = 'https://pan.baidu.com/share/list?app_id=250528&channel=' + 'chunlei&clienttype=0&desc=0&num=100&order=name&page=1&root=' + str(int((not dir)))+ '&shareid=' + shareid + '&showempty=0&uk=' + uk + '&web=1'
        headers = {
            'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.514.1919.810 Safari/537.36',
            'Cookie':'BDUSS=' + BDUSS + ';' +  'STOKEN=' + STOKEN + '; BDCLND=' + randsk
        }
        res = requests.get(url, headers=headers, timeout=10)
        return res.json()
    except Exception as e:
        print("getFileList: ", e)
        return True

def getDlink(fs_id,timestamp,sign,randsk,share_id,uk):
    try:
        headers = {
            'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.514.1919.810 Safari/537.36',
            'Cookie':'BDUSS=' + BDUSS + ';' +  'STOKEN=' + STOKEN + '; BDCLND=' + randsk
        }
        data = {
            "encrypt": 0,
            "extra" : '{"sekey":"' + urllib.parse.unquote(randsk) + '"}',
            "fid_list": '[' + fs_id + ']',
            "primaryid": share_id,
            "uk": uk,
            'product': 'share',
            'type': 'nolimit'
        }
        res = requests.post('https://pan.baidu.com/api/sharedownload?app_id=250528&channel=chunlei&clienttype=12&sign='+sign+'&timestamp='+timestamp+'&web=1', data=data, headers=headers, timeout=10)
        return res.json()
    except Exception as e:
        print("getDlink: ", e)
        return True
    
def getRealLink(url):
    try:
        headers = {
        'user-agent': 'LogStatistic',
        'Cookie': 'BDUSS=' + SVIPBDUSS + ';'
        }
        res = requests.head(url, headers=headers, timeout=10)
        return res.headers["Location"]
    except Exception as e:
        print("getRealLink: ", e)
        return True