#-*- coding:utf-8 -*-

from __future__ import unicode_literals
from app import app
from flask import Flask, request,abort
from pymongo import *
from bson.json_util import dumps
import json,sys,os,time,requests,random,re,datetime
from lxml import etree,html
from bs4 import BeautifulSoup
from urllib import quote
#reload(sys)
#sys.setdefaultencoding("utf-8")

from linebot.exceptions import (
    InvalidSignatureError
)

from linebot.models import *

handler = app.config['HANDLER']
line_bot_api = app.config['LINEBOTAPI']

url = app.config['STOCK_URL']
db_url = app.config['DB_URL']

client =  MongoClient(db_url)
db = client['stockdb']

stat ={}
ENDTIEM = "13:30:00" # 自動結束時間

@app.route('/',methods=["GET"])
def hello():
    return "hello World!!!"

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

def Usage(event):
    push_msg(event,"add:stock_code\n ex -> add:0050 (目前只能單張增加)\
                    \ndel:stock_code\n ex -> del:0050 \
                    \ndel:* 刪除全部的股票\
                    \n/stocks  查詢已登記的股票\
                    \n/rt 目前所選的股票即時報價\
                    \n/start  啟動自動看盤功能，當漲幅超過5%下跌超過4%時會給予提醒\
                    \n預設於下午1:30分收盤時自動停止\
                    \n/end  手動結束自動看盤\
                    \ns: 查看個股新聞 ex: -> s:台積電\
                    \n--h或/help看使用說明")

# def Get_Stock(code):
#    stack_code = "TPE:{0}".format(code)
#    params = {"client":"ig", "q":stack_code}
#    try:
#        r = requests.get(url, params = params )
#        r_slipt = r.text[3:] #remove '//'
#        data = json.loads(r_slipt)
#    except ValueError as e:
#        data = 'None'
#    return data

def News_website(stock_name,flag):
    if flag == 0:
        news_url = "http://news.wearn.com/news.asp?hot=true&r=1"
    else:
        news_url = "http://news.wearn.com/searchnews.asp?qn={0}".format(quote(stock_name))
    res = requests.get(news_url)
    res.encoding='big5'
    soup = BeautifulSoup(res.text,'lxml')

    return soup

def get_news(event,soup,tag):
    news_link = "http://news.wearn.com/"
    msg=""
    nodes = soup.select(tag)
    for i in nodes[0].find_all('li',limit=15):
        if i.text !="":
            title = i.find_all('a')[0].text
            date = i.find_all('span')[0].text
            link = i.find('a').get('href')
            #push_msg(event,title+"\n"+news_link+link)
            msg+=title+"  "+date+"\n"+news_link+link+"\n"
    reply_msg(event,msg)

def TW_Bank():
    currency_list= []

    url = 'http://rate.bot.com.tw/xrt?Lang=zh-TW'
    raw_data = requests.get(url)
    root = etree.fromstring(raw_data.content,etree.HTMLParser())

    rates =  root.xpath("/html/body/div[1]/main/div[4]/table/tbody/tr")
    for rate in rates :
        currency =  rate.xpath("./td/text()")[3]
        currency_list.append(currency)

    return currency_list

def Get_Stock(idx_code):
    try:
        url = 'http://www.wantgoo.com/stock/{0}'.format(idx_code)
        raw_data = requests.get(url)
        soup = BeautifulSoup(raw_data.text,"lxml")
    except:
        print "cant connect websit 'wantgoo' "

    return soup

def Web_Analysis(soup_data):

    stock_name = soup_data.select('#container > div.idx-info.clearfix > h3')[0].get_text()
    price = soup_data.select('#ChangeInfoDiv > span.price')[0].get_text() #成交價
    idx = soup_data.select('#container > div.idx-quotes.clearfix > div.idx-data > ul > li > b')

    start = idx[0].get_text()              #開盤價
    high = idx[1].get_text()               #成交最高價
    low = idx[2].get_text()                #成交最低價
    last = idx[3].get_text()               #昨天收盤價
    chg = float(price)-float(last)         #漲跌(元)
    cp = round(chg / float(last) *100,2)   #漲跌幅度 %
    # 漲跌幅度 = (成交價-昨日收盤) / 昨日收盤 * 100 %
    stock_list= [stock_name,price,start,high,low,last,str(chg),str(cp)]
    #full={"股票":stock_name,"成交價":price,"開盤":start,"最高":high,"最低":low,"昨收":last,"漲跌":str(chg),"漲幅":str(cp)}
    #print u"股票:{0}，成交價：{1}元，開盤：{2}，最高：{3}，最低：{4}，昨收：{5}，漲跌：{6}元，漲幅：{7}%".format(stock_name,price,start,high,low,last,str(chg),str(cp))
    return stock_list
#  get realtime stocks info
#
#  stock_code => 股票代號
#  data => 股票資料
#  uid => 使用者的名字及id
#

def Stockcp(event,stock_code,data,uid,rt=False):
    stock_up = u'注意注意!!!\n{0}漲幅度超過5%了~~~'.format(data[0])
    stock_down = u'注意注意!!!\n{0}下跌幅度超過4%了~~~'.format(data[0])
    if data != 'None' :
        stock_msg = u"股票:"+data[0]+" | "+u"成交價："+data[1]+" | "+u"漲跌幅度："+data[7]+"% | "+u"漲跌："+data[6]+"元 | "+u"昨日收盤價："+data[5]
        if rt:
            push_msg(event,stock_msg)
        #print stock_msg
        if float(data[7]) > 5:
            return  stock_up+stock_msg
        elif float(data[7]) < -4:
            return  stock_down+stock_msg
        return ''
    else:
        db.users.delete_one({uid['name']:uid['uid'],'stock':stock_code})
        return stock_code+":"+"no found,remove this stock from database!!"

# add stock in database
# 依使用者id及名字各別存入要自動看盤的股票
#
def add_stock(event,uid):
    stocks = event.message.text[4:]
    if db.stocks.find({'stock_code':stocks}).count() >0:
        try:
            userid = event.source.user_id
            data = {uid['name']:uid['uid'],'stock':stocks}
            db.users.insert(data)
            reply_msg(event,'已加入:'+stocks)
        except:
            reply_msg(event,"資料庫連接失敗無法加入......")
    else:
        reply_msg(event,"無法加入股票："+stocks+'\n請確認完代號後再重新加入\nex=> add:0050' )

# get self stock from database
# 列出自已的股票
#

def find_stock(event,uid):
    lists=[]
    comma = ' , '
    try:
        for code in db.users.find({uid['name']:uid['uid']}):
            stock_code =  code['stock']
            lists.append(stock_code)
            #print lists

        push_msg(event,"目前監看的股票有:"+comma.join(lists))
    except:
        push_msg(event,"資料庫連接失敗......")

# delete self stock from database
#
#
def del_stock(event,uid):
    stocks = event.message.text[4:]
    if stocks == '*':
        print stocks
        db.users.delete_many({uid['name']:uid['uid']})
        reply_msg(event,'已刪除所有股票')
    elif db.users.find({uid['name']:uid['uid'],'stock':stocks}).count() >0:
        try:
            db.users.delete_one({uid['name']:uid['uid'],'stock':stocks})
            reply_msg(event,'已刪除'+stocks)
        except:
            push_msg(event,"資料庫連接失敗......")
    else:
        reply_msg(event,"無法刪除股票："+stocks+'\n請先輸入/stocks 確認代號後再重新刪除\nex=> del:0050' )


def push_msg(event,msg):
    try:
        user_id = event.source.user_id
        #print (user_id)
        line_bot_api.push_message(user_id,TextSendMessage(text=msg))
    except:
        room_id = event.source.room_id
        #print (room_id)
        line_bot_api.push_message(room_id,TextSendMessage(text=msg))

def reply_msg(event,msg):
    line_bot_api.reply_message(event.reply_token,messages=TextSendMessage(text=msg))

def get_user_profile(event):
    uid = {}
    profile = line_bot_api.get_profile(event.source.user_id)
    uid = {'name':profile.display_name,'uid':profile.user_id}

    return uid

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    emsg =  event.message.text
    uid = get_user_profile(event)

    if re.match("/start",emsg):
        push_msg(event,"股票漲幅背景監視中.....當漲幅大於5%或小於-4%會給予警訊!!")
        stat[uid['uid']] = 'keep'
        tmp_list = []
        for index in db.users.find({uid['name']:uid['uid']}):
            code = index['stock']
            tmp_list.append(code)
            stat[code]=0

        while True:
            now = datetime.datetime.now().strftime("%H:%M:%S")
            if ENDTIEM < now:
                push_msg(event,"今日交易已結束，自動看盤已停止~~明日請早")
                break
            try:
                for code in tmp_list:
                    data = Web_Analysis(Get_Stock(code))
                    info =  Stockcp(event,code,data,uid)
                    if info !="" and stat[code]< 5:
                        push_msg(event,info)
                        stat[code]= stat[code]+1
                        #print stat
                    time.sleep(10)
            except:
                push_msg(event,"斷線了~~~請輸入/start 重新再來一次")
                break

            if stat[uid['uid']] =='exit':
                push_msg(event,"自動看盤停止~~")
                break

    if re.match("/end",emsg):
        stat[uid['uid']] ='exit'

    if emsg=='/rt':
        push_msg(event,'------即時股價回報開始------------')
        for index in db.users.find({uid['name']:uid['uid']}):
            code = index['stock']
            data = Web_Analysis(Get_Stock(code))
            #print data
            Stockcp(event,code,data,uid,True)
            time.sleep(5)
        push_msg(event,'-------即時股價回報結束------------')

    if re.match(u'add:',emsg):
        add_stock(event,uid)
    if re.match(u'del:',emsg):
        del_stock(event,uid)


    if re.match('/help|--h|/Help|--H',emsg):
        buttons_template = TemplateSendMessage(
            alt_text='Buttons template',
            template=ButtonsTemplate(
                title='自動看盤使用說明',
                text='請選擇',
                actions=[
                    MessageTemplateAction(
                        label='使用方法',
                        text=':usage'
                    ),
                    MessageTemplateAction(
                        label='即時股票資訊',
                        text='/rt'
                    ),
                    MessageTemplateAction(
                        label='開始自動看盤',
                        text='/start'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
        Usage(event)
        return 0

    if re.match('@tw|@TW|@Tw',emsg):
        rate = TW_Bank()
        #print rate
        rate_msg = "臺銀現金賣出即時匯率：\
        \nUSD : NTD = 1 : {0}\nGBP : NTD = 1 : {1}\nJPY : NTD = 1 : {2}\nEUR : NTD = 1 : {3}\n".format(rate[0],rate[2],rate[7],rate[14])
        reply_msg(event,rate_msg)

    if re.match('/stocks|/Stocks',emsg):
        find_stock(event,uid)

    if re.match('s:|S:',emsg):
        name = emsg[2:]
        tag = '#cn_content' #個股新料
        flag = 1
        if name  == "hot":
            flag = 0
            tag ="ul.onlymain" # 三日內熱門新聞
        big5_name = name.encode('big5')
        data = News_website(big5_name,flag)
        get_news(event,data,tag)

    if re.match(':usage',emsg):
        Usage(event)

    #reply_msg(event,emsg+"沒有這個指令喔~~請輸入/help或 --h,或者:usage的指令說明喔")
