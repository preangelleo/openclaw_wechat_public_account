https://developers.weixin.qq.com/doc/subscription/api/


开发指南 /快速入门
原公众号文档（包含公众号与服务号）已升级为公众号（原订阅号）与服务号文档。公众号文档请直接参考本目录内容，服务号文档请 点击此处 前往。
快速入门
公众平台技术文档的目的是为了简明扼要的说明接口的使用，语句难免苦涩难懂，甚至对于不同的读者，有语意歧义。万事皆是入门难，对于刚入门的开发者讲，更是难上加难。

为了降低门槛，弥补不足，我们编写了《开发者指引》来讲解微信开放平台的基础常见功能，旨在帮助大家入门微信开放平台的开发者模式。

已熟知接口使用或有一定公众平台开发经验的开发者，请直接跳过本文。这篇文章不会给你带来厉害的编码技巧亦或接口的深层次讲解。对于现有接口存在的疑问，可访问 社区 发帖交流、联系腾讯客服或使用微信反馈。

1.1 申请服务器
以腾讯云服务器为示例：腾讯云服务器购买入口

如你已有小程序，并且已开通小程序云开发，则可以使用 公众号环境共享 能力，在公众号中使用云开发。

1.2 搭建服务
以web.py网络框，python，腾讯云服务器为例介绍。

1）安装/更新需要用到的软件

安装python2.7版本以上

安装web.py

安装libxml2, libxslt, lxml python

2）编辑代码，如果不懂python 语法，请到python官方文档查询说明。

vim main.py

# -*- coding: utf-8 -*-
# filename: main.py
import web

urls = (
    '/wx', 'Handle',
)

class Handle(object):
    def GET(self):
        return "hello, this is handle view"

if __name__ == '__main__':
    app = web.application(urls, globals())
    app.run()
3）如果出现“socket.error: No socket could be created“错误信息，可能为80端口号被占用，可能是没有权限，请自行查询解决办法。如果遇见其他错误信息，请到web.py官方文档，学习webpy 框架3执行命令：sudo python main.py 80 。

4）url填写：http://外网IP/wx （外网IP请到腾讯云购买成功处查询）。如下图，一个简单的web应用已搭建。


1.3 注册公众号
点此注册公众号
点此注册服务号
1.4 开发者基本配置
前往「微信开发者平台 - 我的业务与服务 - 公众号 - 开发信息」进行相关配置

3） 现在选择提交肯定是验证token失败，因为还需要完成代码逻辑。改动原先main.py文件，新增handle.py

a）vim main.py

# -*- coding: utf-8 -*-
# filename: main.py
import web
from handle import Handle

urls = (
    '/wx', 'Handle',
)

if __name__ == '__main__':
    app = web.application(urls, globals())
    app.run()
b）vim handle.py

先附加逻辑流程图


# -*- coding: utf-8 -*-
# filename: handle.py

import hashlib
import web

class Handle(object):
    def GET(self):
        try:
            data = web.input()
            if len(data) == 0:
                return "hello, this is handle view"
            signature = data.signature
            timestamp = data.timestamp
            nonce = data.nonce
            echostr = data.echostr
            token = "xxxx" #请按照公众平台官网\基本配置中信息填写

            list = [token, timestamp, nonce]
            list.sort()
            sha1 = hashlib.sha1()
            map(sha1.update, list)
            hashcode = sha1.hexdigest()
            print "handle/GET func: hashcode, signature: ", hashcode, signature
            if hashcode == signature:
                return echostr
            else:
                return ""
        except Exception, Argument:
            return Argument
4） 重新启动成功后（python main.py 80），点击提交按钮。若提示”token验证失败”, 请认真检查代码或网络链接等。若token验证成功，会自动返回基本配置的主页面，点击启动按钮 5） 为了便于开发者调试，我们提供了URL验证工具供开发者使用。 开发者需填写AccessToken、URL地址、Token，点击“检查参数并发起验证”后，调试工具会发送GET请求到URL所指的服务器，并返回相关调试信息。

1.5 重要事情提前交代
接下来，文章准备从两个简单的示例入手。

示例一：实现“你说我学”

示例二：实现“图尚往来”

两个简单的示例后，是一些基础功能的介绍：素材管理、自定义菜单、群发。所有的示例代码是为了简明的说明问题，避免代码复杂化。

在实际中搭建一个安全稳定高效的公众号，建议参考框架如下图：


主要有三个部分：负责业务逻辑部分的服务器，负责对接微信API的API-Proxy服务器，以及唯一的AccessToken中控服务器

1）AccessToken中控服务器：

负责： 提供主动刷新和被动刷新机制来刷新accessToken并存储（为了防止并发刷新，注意加并发锁），提供给业务逻辑有效的accessToken。

优点： 避免业务逻辑方并发获取access_token，避免AccessToken互相覆盖，提高业务功能的稳定性。

2）API-Proxy服务器：

负责：专一与微信API对接，不同的服务器可以负责对接不同的业务逻辑，更可进行调用频率、权限限制。

优点：某台API-proxy异常，还有其余服务器支持继续提供服务，提高稳定性，避免直接暴漏内部接口，有效防止恶意攻击，提高安全性。

2 实现“你问我答”
目的：

1）理解被动消息的含义

2）理解收\发消息机制

预实现功能：

粉丝给公众号一条文本消息，公众号立马回复一条文本消息给粉丝，不需要通过公众平台网页操作。

2.1 接受文本消息
即粉丝给公众号发送的文本消息。官方wiki链接：接收普通消息

粉丝给公众号发送文本消息：“欢迎开启公众号开发者模式”，在开发者后台，收到公众平台发送的xml 如下：（下文均隐藏了ToUserName 及 FromUserName 信息）

<xml>
 <ToUserName><![CDATA[公众号]]></ToUserName>
 <FromUserName><![CDATA[粉丝号]]></FromUserName>
 <CreateTime>1460537339</CreateTime>
 <MsgType><![CDATA[text]]></MsgType>
 <Content><![CDATA[欢迎开启公众号开发者模式]]></Content>
 <MsgId>6272960105994287618</MsgId>
</xml>
解释：

createTime 是微信公众平台记录粉丝发送该消息的具体时间

text: 用于标记该xml 是文本消息，一般用于区别判断

欢迎开启公众号开发者模式: 说明该粉丝发给公众号的具体内容是欢迎开启公众号开发者模式

MsgId: 是公众平台为记录识别该消息的一个标记数值, 微信后台系统自动产生

2.2 被动回复文本消息
即公众号给粉丝发送的文本消息，官方wiki链接: 被动回复用户消息

特别强调：

1） 被动回复消息，即发送被动响应消息，不同于客服消息接口

2） 它其实并不是一种接口，而是对微信服务器发过来消息的一次回复

3） 收到粉丝消息后不想或者不能5秒内回复时，需回复“success”字符串（下文详细介绍）

4） 客服接口在满足一定条件下随时调用

公众号想回复给粉丝一条文本消息，内容为“test”, 那么开发者发送给公众平台后台的xml 内容如下：

<xml>
 <ToUserName><![CDATA[粉丝号]]></ToUserName>
 <FromUserName><![CDATA[公众号]]></FromUserName>
 <CreateTime>1460541339</CreateTime>
 <MsgType><![CDATA[text]]></MsgType>
 <Content><![CDATA[test]]></Content>
</xml>
特别备注：

1）ToUserName（接受者）、FromUserName(发送者) 字段请实际填写。

2）createtime 只用于标记开发者回复消息的时间，微信后台发送此消息都是不受这个字段约束。

3）text : 用于标记 此次行为是发送文本消息 （当然可以是image/voice等类型）。

4）文本换行 ‘\n’。

2.3 回复success问题
查询官方wiki 开头强调： 假如服务器无法保证在五秒内处理回复，则必须回复“success”或者“”（空串），否则微信后台会发起三次重试。

解释一下为何有这么奇怪的规定。发起重试是微信后台为了尽可以保证粉丝发送的内容开发者均可以收到。如果开发者不进行回复，微信后台没办法确认开发者已收到消息，只好重试。

真的是这样子吗？尝试一下收到消息后，不做任何回复。在日志中查看到微信后台发起了三次重试操作，日志截图如下：


三次重试后，依旧没有及时回复任何内容，系统自动在粉丝会话界面出现错误提示“该公众号暂时无法提供服务，请稍后再试”。


如果回复success，微信后台可以确定开发者收到了粉丝消息，没有任何异常提示。因此请大家注意回复success的问题。

2.4 流程图

2.5 码代码
main.py文件不改变，handle.py 需要增加一下代码，增加新的文件receive.py, reply.py

1）vim handle.py


# -*- coding: utf-8 -*-# 
# filename: handle.py
import hashlib
import reply
import receive
import web
class Handle(object):
    def POST(self):
        try:
            webData = web.data()
            print "Handle Post webdata is ", webData
            #后台打日志
            recMsg = receive.parse_xml(webData)
            if isinstance(recMsg, receive.Msg) and recMsg.MsgType == 'text':
                toUser = recMsg.FromUserName
                fromUser = recMsg.ToUserName
                content = "test"
                replyMsg = reply.TextMsg(toUser, fromUser, content)
                return replyMsg.send()
            else:
                print "暂且不处理"
                return "success"
        except Exception, Argment:
            return Argment
2）vim receive.py

# -*- coding: utf-8 -*-#
# filename: receive.py
import xml.etree.ElementTree as ET


def parse_xml(web_data):
    if len(web_data) == 0:
        return None
    xmlData = ET.fromstring(web_data)
    msg_type = xmlData.find('MsgType').text
    if msg_type == 'text':
        return TextMsg(xmlData)
    elif msg_type == 'image':
        return ImageMsg(xmlData)


class Msg(object):
    def __init__(self, xmlData):
        self.ToUserName = xmlData.find('ToUserName').text
        self.FromUserName = xmlData.find('FromUserName').text
        self.CreateTime = xmlData.find('CreateTime').text
        self.MsgType = xmlData.find('MsgType').text
        self.MsgId = xmlData.find('MsgId').text


class TextMsg(Msg):
    def __init__(self, xmlData):
        Msg.__init__(self, xmlData)
        self.Content = xmlData.find('Content').text.encode("utf-8")


class ImageMsg(Msg):
    def __init__(self, xmlData):
        Msg.__init__(self, xmlData)
        self.PicUrl = xmlData.find('PicUrl').text
        self.MediaId = xmlData.find('MediaId').text

3）vim reply.py



# -*- coding: utf-8 -*-#
# filename: reply.py
import time

class Msg(object):
    def __init__(self):
        pass

    def send(self):
        return "success"

class TextMsg(Msg):
    def __init__(self, toUserName, fromUserName, content):
        self.__dict = dict()
        self.__dict['ToUserName'] = toUserName
        self.__dict['FromUserName'] = fromUserName
        self.__dict['CreateTime'] = int(time.time())
        self.__dict['Content'] = content

    def send(self):
        XmlForm = """
            <xml>
                <ToUserName><![CDATA[{ToUserName}]]></ToUserName>
                <FromUserName><![CDATA[{FromUserName}]]></FromUserName>
                <CreateTime>{CreateTime}</CreateTime>
                <MsgType><![CDATA[text]]></MsgType>
                <Content><![CDATA[{Content}]]></Content>
            </xml>
            """
        return XmlForm.format(**self.__dict)

class ImageMsg(Msg):
    def __init__(self, toUserName, fromUserName, mediaId):
        self.__dict = dict()
        self.__dict['ToUserName'] = toUserName
        self.__dict['FromUserName'] = fromUserName
        self.__dict['CreateTime'] = int(time.time())
        self.__dict['MediaId'] = mediaId

    def send(self):
        XmlForm = """
            <xml>
                <ToUserName><![CDATA[{ToUserName}]]></ToUserName>
                <FromUserName><![CDATA[{FromUserName}]]></FromUserName>
                <CreateTime>{CreateTime}</CreateTime>
                <MsgType><![CDATA[image]]></MsgType>
                <Image>
                <MediaId><![CDATA[{MediaId}]]></MediaId>
                </Image>
            </xml>
            """
        return XmlForm.format(**self.__dict)
码好代码之后，重新启动程序，sudo python main.py 80。

2.6 在线测试
微信公众平台有提供一个在线测试的平台方便开发者模拟场景测试代码逻辑。正如 2.2被动回复文本消息 交代此被动回复接口不同于客服接口，测试时也要注意区别。

在线测试目的在于测试开发者代码逻辑是否有误、是否符合预期。即便测试成功也不会发送内容给粉丝。所以可以随意测试。

 
测试结果：

1）”请求失败”，说明代码有问题，请检查代码逻辑。


2）“请求成功”，然后根据返回结果查看是否符合预期。


2.7 真实体验
拿出手机，微信扫描公众号二维码，成为自己公众号的第一个粉丝。公众号二维码位置如下图：

测试如下图：


3 实现“图”尚往来
目的：

1）引入素材管理

2）以文本消息，图片消息为基础，可自行理解剩余的语音消息、视频消息、地理消息等

预实现功能：

接受粉丝发送的图片消息，并立马回复相同的图片给粉丝。


3.1 接收图片消息
即粉丝给公众号发送的图片消息。官方wiki链接：消息管理/接收消息-接受普通消息/ 图片消息从实例讲解，粉丝给公众号发送一张图片消息，在公众号开发者后台接收到的xml如下:

<xml>
 <ToUserName><![CDATA[公众号]]></ToUserName>
 <FromUserName><![CDATA[粉丝号]]></FromUserName>
 <CreateTime>1460536575</CreateTime>
 <MsgType><![CDATA[image]]></MsgType>
 <PicUrl><![CDATA[http://mmbiz.qpic.cn/xxxxxx /0]]></PicUrl>
 <MsgId>6272956824639273066</MsgId>
 <MediaId><![CDATA[gyci5a-xxxxx-OL]]></MediaId>
</xml>
特别说明：

PicUrl: 这个参数是微信系统把“粉丝“发送的图片消息自动转化成url。 这个url可用浏览器打开查看到图片。

MediaId: 是微信系统产生的id 用于标记该图片，详情可参考wiki素材管理/获取临时素材，

3.2 被动回复图片消息
即公众号给粉丝发送的图片消息。官方wiki链接：消息管理/发送消息-被动回复用户消息/ 图片消息

特别说明：

1） 被动回复消息，即发送被动响应消息，不同于客服消息接口

2） 它其实并不是一种接口，而是对微信服务器发过来消息的一次回复

3） 收到粉丝消息后不想或者不能5秒内回复时，需回复“success”字符串（下文详细介绍）

4） 客服接口在满足一定条件下随时调用

开发者发送给微信后台的xml 如下：

<xml>
 <ToUserName><![CDATA[粉丝号]]></ToUserName>
 <FromUserName><![CDATA[公众号]]></FromUserName>
 <CreateTime>1460536576</CreateTime>
 <MsgType><![CDATA[image]]></MsgType>
 <Image>
 <MediaId><![CDATA[gyci5oxxxxxxv3cOL]]></MediaId>
 </Image>
</xml>
这里填写的MediaId的内容，其实就是粉丝的发送图片的原MediaId，所以粉丝收到了一张一模一样的原图。 如果想回复粉丝其它图片怎么呢？

1） 新增素材，请参考 新增临时素材 或者 新增永久素材

2） 获取其MediaId，请参考 获取临时素材MediaID 或者 获取永久素材MediaID

3.3 流程图

3.4 码代码
只显示更改的代码部分，其余部分参考上小节，在线测试，真实体验，回复空串，请参考 实现"你问我答"。 vim handle.py

# -*- coding: utf-8 -*-
# filename: handle.py
import hashlib
import reply
import receive
import web

class Handle(object):
    def POST(self):
        try:
            webData = web.data()
            print "Handle Post webdata is ", webData   #后台打日志
            recMsg = receive.parse_xml(webData)
            if isinstance(recMsg, receive.Msg):
                toUser = recMsg.FromUserName
                fromUser = recMsg.ToUserName
                if recMsg.MsgType == 'text':
                    content = "test"
                    replyMsg = reply.TextMsg(toUser, fromUser, content)
                    return replyMsg.send()
                if recMsg.MsgType == 'image':
                    mediaId = recMsg.MediaId
                    replyMsg = reply.ImageMsg(toUser, fromUser, mediaId)
                    return replyMsg.send()
                else:
                    return reply.Msg().send()
            else:
                print "暂且不处理"
                return reply.Msg().send()
        except Exception, Argment:
            return Argment
4 AccessToken
关于如何生成 AccessToken 以及使用建议，可查看Access_token 使用说明
特别强调：

1） 第三方需要一个access_token获取和刷新的中控服务器。

2） 并发获取access_token会导致AccessToken互相覆盖，影响具体的业务功能

4.3 码代码
再次重复说明，下面代码只是为了简单说明接口获取方式。实际中并不推荐，尤其是业务繁重的公众号，更需要中控服务器，统一的获取accessToken。

vim basic.py

# -*- coding: utf-8 -*-
# filename: basic.py
import urllib
import time
import json
class Basic:
    def __init__(self):
        self.__accessToken = ''
        self.__leftTime = 0

    def __real_get_access_token(self):
        appId = "xxxxx"
        appSecret = "xxxxx"
        postUrl = ("https://api.weixin.qq.com/cgi-bin/token?grant_type="
                   "client_credential&appid=%s&secret=%s" % (appId, appSecret))
        urlResp = urllib.urlopen(postUrl)
        urlResp = json.loads(urlResp.read())
        self.__accessToken = urlResp['access_token']
        self.__leftTime = urlResp['expires_in']

    def get_access_token(self):
        if self.__leftTime < 10:
            self.__real_get_access_token()
        return self.__accessToken

    def run(self):
        while(True):
            if self.__leftTime > 10:
                time.sleep(2)
                self.__leftTime -= 2
            else:
                self.__real_get_access_token()
5 临时素材
公众号经常有需要用到一些临时性的多媒体素材的场景，例如在使用接口特别是发送消息时，对多媒体文件、多媒体消息的获取和调用等操作，是通过MediaID来进行的。譬如实现“图”尚往来中，粉丝给公众号发送图片消息，便产生一临时素材。

因为永久素材有数量的限制，但是公众号又需要临时性使用一些素材，因而产生了临时素材。这类素材不在微信公众平台后台长期存储，所以在公众平台官网的素材管理中查询不到，但是可以通过接口对其操作。

其他详情请以公众平台官网wiki介绍为依据。

5.1 新建临时素材
点此查看接口详情，提供参考代码如何上传素材作为临时素材，供其它接口使用。
vim media.py 编写完成之后，直接运行media.py 即可上传临时素材。

# -*- coding: utf-8 -*-
# filename: media.py
from basic import Basic
import urllib2
import poster.encode
from poster.streaminghttp import register_openers


class Media(object):
    def __init__(self):
        register_openers()
    
    # 上传图片
    def upload(self, accessToken, filePath, mediaType):
        openFile = open(filePath, "rb")
        param = {'media': openFile}
        postData, postHeaders = poster.encode.multipart_encode(param)

        postUrl = "https://api.weixin.qq.com/cgi-bin/media/upload?access_token=%s&type=%s" % (
            accessToken, mediaType)
        request = urllib2.Request(postUrl, postData, postHeaders)
        urlResp = urllib2.urlopen(request)
        print urlResp.read()

if __name__ == '__main__':
    myMedia = Media()
    accessToken = Basic().get_access_token()
    filePath = "D:/code/mpGuide/media/test.jpg"  # 请按实际填写
    mediaType = "image"
    myMedia.upload(accessToken, filePath, mediaType)
5.2 获取临时素材MediaID
临时素材的MediaID 没有提供特定的接口进行统一查询，因此有俩种方式

1） 通过接口上次的临时素材，在调用成功的情况下，从返回JSON数据中提取MediaID，可临时使用

2） 粉丝互动中的临时素材，可从xml 数据提取MediaID，可临时使用

5.3 下载临时素材
点此查看接口详情
5.3.1 手工体验
开发者如何保存粉丝发送的图片呢？ 点此查看接口详情，为方便理解，从最简单浏览器获取素材的方法入手，根据实际情况，浏览器输入网址： https://api.weixin.qq.com/cgi-bin/media/get?access_token=ACCESS_TOKEN&media_id=MEDIA_ID （自行替换数据） ACCESS_TOKEN 如 "AccessToken"章节讲解 MEDIA_ID 如 图尚往来/接受图片消息xml中的MediaId 讲解 只要数据正确，则会下载图片到本地，如下图：

 
5.3.2接口获取
现在已经理解这个接口的功能了，只剩码代码了。

vim media.py

# -*- coding: utf-8 -*-
# filename: media.py
import urllib2
import json
from basic import Basic


class Media(object):
    def get(self, accessToken, mediaId):
        postUrl = "https://api.weixin.qq.com/cgi-bin/media/get?access_token=%s&media_id=%s" % (
            accessToken, mediaId)
        urlResp = urllib2.urlopen(postUrl)

        headers = urlResp.info().__dict__['headers']
        if ('Content-Type: application/json\r\n' in headers) or ('Content-Type: text/plain\r\n' in headers):
            jsonDict = json.loads(urlResp.read())
            print jsonDict
        else:
            buffer = urlResp.read()  # 素材的二进制
            mediaFile = file("test_media.jpg", "wb")
            mediaFile.write(buffer)
            print "get successful"


if __name__ == '__main__':
    myMedia = Media()
    accessToken = Basic().get_access_token()
    mediaId = "2ZsPnDj9XIQlGfws31MUfR5Iuz-rcn7F6LkX3NRCsw7nDpg2268e-dbGB67WWM-N"
    myMedia.get(accessToken, mediaId)

直接运行 media.py 即可把想要的素材下载下来，其中图文消息类型的，会直接在屏幕输出json数据段。

6 永久素材
6.1 新建永久素材的方式
6.1.1 手工体验
公众号官网的素材管理新增素材。补充一点，公众平台只以MediaID区分素材，MediaID不等于素材的文件名。MediaID只能通过接口查询，公众平台官网看到的是素材的文件名。


6.1.2 新增永久素材
新增永久素材接口（详情见wiki），跟新增临时素材的操作差不多，使用url不一样而已，这里避免重复，以新增永久图文素材接口为例，新增其他类型的素材请参考新增临时素材代码。

vim material.py

# -*- coding: utf-8 -*-
# filename: material.py
import urllib2
import json
from basic import Basic

class Material(object):
    # 上传图文
    def add_news(self, accessToken, news):
        postUrl = "https://api.weixin.qq.com/cgi-bin/material/add_news?access_token=%s" % accessToken
        urlResp = urllib2.urlopen(postUrl, news)
        print urlResp.read()

if __name__ == '__main__':
    myMaterial = Material()
    accessToken = Basic().get_access_token()
    news = (
        {
            "articles":
            [
                {
                    "title": "test",
                    "thumb_media_id": "X2UMe5WdDJSS2AS6BQkhTw9raS0pBdpv8wMZ9NnEzns",
                    "author": "vickey",
                    "digest": "",
                    "show_cover_pic": 1,
                    "content": "<p><img src=\"\" alt=\"\" data-width=\"null\" data-ratio=\"NaN\"><br  /><img src=\"\" alt=\"\" data-width=\"null\" data-ratio=\"NaN\"><br  /></p>",
                    "content_source_url": "",
                }
            ]
        })
    # news 是个dict类型，可通过下面方式修改内容
    #news['articles'][0]['title'] = u"测试".encode('utf-8')
    # print news['articles'][0]['title']
    news = json.dumps(news, ensure_ascii=False)
    myMaterial.add_news(accessToken, news)
6.2 获取永久素材MediaID
1） 通过新增永久素材接口（点此查看接口详情）新增素材时，保存MediaID

2） 通过获取永久素材列表(下文介绍) 的方式获取素材信息，从而得到MediaID

6.3 获取素材列表
获取素材列表（点此查看接口详情）特别说明：此接口只是批量拉取素材信息，不是一次性拉去所有素材的信息，所以可以理解offset字段的含义了吧。

vim material.py

# -*- coding: utf-8 -*-
# filename: material.py
import urllib2
import json
import poster.encode
from poster.streaminghttp import register_openers
from basic import Basic

class Material(object):
    def __init__(self):
        register_openers()
    #上传
    def upload(self, accessToken, filePath, mediaType):
        openFile = open(filePath, "rb")
        fileName = "hello"
        param = {'media': openFile, 'filename': fileName}
        #param = {'media': openFile}
        postData, postHeaders = poster.encode.multipart_encode(param)

        postUrl = "https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=%s&type=%s" % (accessToken, mediaType)
        request = urllib2.Request(postUrl, postData, postHeaders)
        urlResp = urllib2.urlopen(request)
        print urlResp.read()
    #下载
    def get(self, accessToken, mediaId):
        postUrl = "https://api.weixin.qq.com/cgi-bin/material/get_material?access_token=%s" % accessToken
        postData = "{ \"media_id\": \"%s\" }" % mediaId
        urlResp = urllib2.urlopen(postUrl, postData)
        headers = urlResp.info().__dict__['headers']
        if ('Content-Type: application/json\r\n' in headers) or ('Content-Type: text/plain\r\n' in headers):
            jsonDict = json.loads(urlResp.read())
            print jsonDict
        else:
            buffer = urlResp.read()  # 素材的二进制
            mediaFile = file("test_media.jpg", "wb")
            mediaFile.write(buffer)
            print "get successful"
    #删除
    def delete(self, accessToken, mediaId):
        postUrl = "https://api.weixin.qq.com/cgi-bin/material/del_material?access_token=%s" % accessToken
        postData = "{ \"media_id\": \"%s\" }" % mediaId
        urlResp = urllib2.urlopen(postUrl, postData)
        print urlResp.read()
    
    #获取素材列表
    def batch_get(self, accessToken, mediaType, offset=0, count=20):
        postUrl = ("https://api.weixin.qq.com/cgi-bin/material"
               "/batchget_material?access_token=%s" % accessToken)
        postData = ("{ \"type\": \"%s\", \"offset\": %d, \"count\": %d }"
                    % (mediaType, offset, count))
        urlResp = urllib2.urlopen(postUrl, postData)
        print urlResp.read()

if __name__ == '__main__':
    myMaterial = Material()
    accessToken = Basic().get_access_token()
    mediaType = "news"
    myMaterial.batch_get(accessToken, mediaType)
6.4 删除永久素材
如果我想删除掉 20160102.jpg 这张图片，除了官网直接操作，也可以使用【删除永久素材】接口：点此查看接口详情

首先需要知道该图片的mediaID，方法上小节已讲述。代码可参考上小节：Material().delete() 接口 调用接口成功后，在公众平台官网素材管理的图片中，查询不到已删除的图片。


7 自定义菜单
自定义菜单意义作用请参考创建接口 介绍。

目标：三个菜单栏，体验click、view、media_id 三种类型的菜单按钮，其他类型在本小节学习之后，自行请查询公众平台wiki说明领悟。

7.1 创建菜单界面
1）根据公众平台wiki 给的json 数据编写代码，其中涉及media_id部分请阅读"永久素材"章节。

vim menu.py

# -*- coding: utf-8 -*-
# filename: menu.py
import urllib
from basic import Basic

class Menu(object):
    def __init__(self):
        pass
    def create(self, postData, accessToken):
        postUrl = "https://api.weixin.qq.com/cgi-bin/menu/create?access_token=%s" % accessToken
        if isinstance(postData, unicode):
            postData = postData.encode('utf-8')
        urlResp = urllib.urlopen(url=postUrl, data=postData)
        print urlResp.read()

    def query(self, accessToken):
        postUrl = "https://api.weixin.qq.com/cgi-bin/menu/get?access_token=%s" % accessToken
        urlResp = urllib.urlopen(url=postUrl)
        print urlResp.read()

    def delete(self, accessToken):
        postUrl = "https://api.weixin.qq.com/cgi-bin/menu/delete?access_token=%s" % accessToken
        urlResp = urllib.urlopen(url=postUrl)
        print urlResp.read()
        
    #获取自定义菜单配置接口
    def get_current_selfmenu_info(self, accessToken):
        postUrl = "https://api.weixin.qq.com/cgi-bin/get_current_selfmenu_info?access_token=%s" % accessToken
        urlResp = urllib.urlopen(url=postUrl)
        print urlResp.read()

if __name__ == '__main__':
    myMenu = Menu()
    postJson = """
    {
        "button":
        [
            {
                "type": "click",
                "name": "开发指引",
                "key":  "mpGuide"
            },
            {
                "name": "公众平台",
                "sub_button":
                [
                    {
                        "type": "view",
                        "name": "更新公告",
                        "url": "http://mp.weixin.qq.com/wiki?t=resource/res_main&id=mp1418702138&token=&lang=zh_CN"
                    },
                    {
                        "type": "view",
                        "name": "接口权限说明",
                        "url": "http://mp.weixin.qq.com/wiki?t=resource/res_main&id=mp1418702138&token=&lang=zh_CN"
                    },
                    {
                        "type": "view",
                        "name": "返回码说明",
                        "url": "http://mp.weixin.qq.com/wiki?t=resource/res_main&id=mp1433747234&token=&lang=zh_CN"
                    }
                ]
            },
            {
                "type": "media_id",
                "name": "旅行",
                "media_id": "z2zOokJvlzCXXNhSjF46gdx6rSghwX2xOD5GUV9nbX4"
            }
          ]
    }
    """
    accessToken = Basic().get_access_token()
    #myMenu.delete(accessToken)
    myMenu.create(postJson, accessToken)
2）在腾讯云服务器上执行命令：python menu.py。

3）查看： 重新关注公众号后即可看到新创建菜单界面，题外话，如果不重新关注，公众号界面也会自动更改，但有时间延迟。

如下图所示，点击子菜单“更新公告“（view类型），弹出网页（pc版本）


点击旅行（media_id类型），公众号显示了一篇图文消息，如下图所示：


点击开发指引（click类型），发现公众号系统提示：“该公众号暂时无法提供服务“。


7.2 完善菜单功能
查看公众平台自定义菜单与自定义菜单事件推送 后，可知：点击click类型button，微信后台会推送一个event类型的xml 给开发者。

显然，click类型的还需要开发者进一步完善后台代码逻辑，增加对自定义菜单事件推送的响应。

7.2.1 流程图

7.2.2码代码
vim handle.py （修改）
# -*- coding: utf-8 -*-
# filename: handle.py
import reply
import receive
import web

class Handle(object):
    def POST(self):
        try:
            webData = web.data()
            print "Handle Post webdata is ", webData  # 后台打日志
            recMsg = receive.parse_xml(webData)
            if isinstance(recMsg, receive.Msg):
                toUser = recMsg.FromUserName
                fromUser = recMsg.ToUserName
                if recMsg.MsgType == 'text':
                    content = "test"
                    replyMsg = reply.TextMsg(toUser, fromUser, content)
                    return replyMsg.send()
                if recMsg.MsgType == 'image':
                    mediaId = recMsg.MediaId
                    replyMsg = reply.ImageMsg(toUser, fromUser, mediaId)
                    return replyMsg.send()
            if isinstance(recMsg, receive.EventMsg):
                toUser = recMsg.FromUserName
                fromUser = recMsg.ToUserName
                if recMsg.Event == 'CLICK':
                    if recMsg.Eventkey == 'mpGuide':
                        content = u"编写中，尚未完成".encode('utf-8')
                        replyMsg = reply.TextMsg(toUser, fromUser, content)
                        return replyMsg.send()
            print "暂且不处理"
            return reply.Msg().send()
        except Exception, Argment:
            return Argment

2）vim receive.py (修改)

# -*- coding: utf-8 -*-
# filename: receive.py
import xml.etree.ElementTree as ET

def parse_xml(web_data):
    if len(web_data) == 0:
        return None
    xmlData = ET.fromstring(web_data)
    msg_type = xmlData.find('MsgType').text
    if msg_type == 'event':
        event_type = xmlData.find('Event').text
        if event_type == 'CLICK':
            return Click(xmlData)
        #elif event_type in ('subscribe', 'unsubscribe'):
            #return Subscribe(xmlData)
        #elif event_type == 'VIEW':
            #return View(xmlData)
        #elif event_type == 'LOCATION':
            #return LocationEvent(xmlData)
        #elif event_type == 'SCAN':
            #return Scan(xmlData)
    elif msg_type == 'text':
        return TextMsg(xmlData)
    elif msg_type == 'image':
        return ImageMsg(xmlData)

class EventMsg(object):
    def __init__(self, xmlData):
        self.ToUserName = xmlData.find('ToUserName').text
        self.FromUserName = xmlData.find('FromUserName').text
        self.CreateTime = xmlData.find('CreateTime').text
        self.MsgType = xmlData.find('MsgType').text
        self.Event = xmlData.find('Event').text
class Click(EventMsg):
    def __init__(self, xmlData):
        EventMsg.__init__(self, xmlData)
        self.Eventkey = xmlData.find('EventKey').text
7.3 体验
编译好代码后，重新启动服务，（sudo python main.py 80）,view类型、media_id类型的本身就很容易实现，现在重点看一下click类型的菜单按钮。

微信扫码成为公众号的粉丝，点击菜单按钮“开发指引”。

查看后台日志，发现接收到一条xml，如截图：


公众号的后台代码设置对该事件的处理是回复一条内容为“编写之中”的文本消息，因此公众号发送了一条文本消息给我，如图：


好啦，到此，目标已实现。对于自定义菜单其他类型，均同理可操作。



开发指南 /公众号「开发接口管理」升级说明
「开发接口管理」模块升级说明
为了给开发者提供更丰富且体验更好的开发管理功能，公众号/服务号的「开发接口管理」模块现已升级并迁移至微信开发者平台，下面是迁移前后的说明。

一级入口
迁移前路径	迁移后路径
微信公众平台 - 设置与开发 - 开发接口管理	微信开发者平台 - 我的业务 - 公众号/服务号
迁移前：

迁移后：

子功能入口
功能名称	迁移前路径	迁移后路径
开发者ID(AppID)	微信公众平台 - 开发接口管理 - 基础配置	微信开发者平台 - 我的业务 - 公众号/服务号 - 基础信息
开发者密钥(AppSecret)	微信公众平台 - 开发接口管理 - 基础配置	微信开发者平台 - 我的业务 - 公众号/服务号 - 基础信息 - 开发密钥
IP 白名单	微信公众平台 - 开发接口管理 - 基础配置	微信开发者平台 - 我的业务 - 公众号/服务号 - 基础信息 - 开发密钥
服务器配置	微信公众平台 - 开发接口管理 - 基础配置	微信开发者平台 - 我的业务 - 公众号/服务号 - 基础信息 - 域名与消息推送配置
已绑定的微信开放平台账号	微信公众平台 - 开发接口管理 - 基础配置	微信开发者平台 - 我的业务 - 公众号/服务号 - 绑定关系 - 开放平台
绑定开发者微信号	微信公众平台 - 开发接口管理 - 开发者工具 - Web开发者工具	微信开发者平台 - 我的业务 - 公众号/服务号 - 基础信息 - 成员管理
在线接口调试工具	微信公众平台 - 开发接口管理 - 开发者工具 - 在线接口调试工具	微信开发者平台 - 我的业务 - 开发者平台 - 首页 - 开发工具 - 接口中心 - 更多
测试号	微信公众平台 - 开发接口管理 - 开发者工具 - 测试号	迁移后申请公众号和服务号测试号入口：https://mp.weixin.qq.com/debug/cgi-bin/sandbox?t=sandbox/login
数据监控	微信公众平台 - 开发接口管理 - 运维中心 - 数据监控	微信开发者平台 - 我的业务 - 公众号/服务号 - 接口管理 - 接口监控
接口告警	微信公众平台 - 开发接口管理 - 运维中心 - 接口告警	微信开发者平台 - 我的业务 - 公众号/服务号 - 接口管理 - 接口告警
接口告警	微信公众平台 - 开发接口管理 - 运维中心 - 日志查询	开发者平台 - 首页 - 开发工具 - 接口中心 - API 诊断
接口权限	微信公众平台 - 开发接口管理 - 接口权限	微信开发者平台 - 我的业务 - 公众号/服务号 - 接口管理 - 接口权限与额度
补充说明 1
公众号/服务号的 AppID，除了可以在开发者平台查看，也可以在公众平台查看，具体路径是：微信公众平台 - 设置与开发 - 账号设置 - 账号详情 - 注册信息，如下图

注意事项：如果输入 AppID 后出现提示「你当前输入的不是公众号AppID,请输入公众号的AppID。」，则可能是输入了服务号的 AppID，请在顶部导航栏切换到服务号后，再进行绑定操作。

平台方将尽快完善支持输入微信号以及原始id 进行绑定，如有问题可前往社区联系小助手进行反馈。
补充说明 2
注意：平台不储存和显示AppSecret，如已忘记 AppSecret，则可通过「重置」功能重新生成开发者密钥（AppSecret），并需妥善保存。


补充说明 3
必须是公众号/服务号的开发者或者管理员，才可以登录开发者平台查看公众号/服务号的账号信息，即，即使是公众号/服务号的「运营者」，也是没有权限在开发者平台查看公众号/服务号的账号信息。
如何申请绑定开发者，详情可查看申请绑定公众号或服务号开发者
补充说明 4
启用公众号/服务号 AppSecret出现提示 “该账号尚未完成主体认证，前往微信公众平台完成认证后重试” 或 该账号尚未完成实名，前往微信公众平台完成实名后重试 的原因以及解决方案如下：

原因以及解决方案 1

如果是个人主体的公众号/服务号，如果还没有完成管理员实名的，则会出现该账号尚未完成实名，前往微信公众平台完成实名后重试
如何判断自己的账号是否完成了实名？可前往「微信公众平台 - 账号详情 - 主体信息」，如果显示了管理员的姓名，则是完成了实名认证。如下截图：
如果未完成实名认证的，则可在「设置与开发 - 人员设置 - 管理员信息」修改管理员的实名信息即可

原因以及解决方案 2

如果是非个人主体的公众号/服务号，如果还没有完成管理员实名的，则会出现该账号尚未完成主体认证，前往微信公众平台完成认证后重试
如何判断自己的账号是否完成了主体认证？可前往「微信公众平台 - 账号详情 - 认证情况」，如果显示未认证，则点击“申请微信认证”进行操作即可。如下截图：

更多其他功能
除了上述功能，开发者还可以在开发者平台配置 js 安全域名以及管理公众号/服务号授权的第三方平台账号。

功能名称	公众平台路径	开发者平台路径
JS接口安全域名	微信公众平台 - 账号设置 - 功能设置	微信开发者平台 - 我的业务 - 公众号/服务号 - 基础信息 - 域名与消息推送配置
授权管理	微信公众平台 - 账号设置 - 授权管理	微信开发者平台 - 我的业务 - 公众号/服务号 - 授权关系
操作指南
1、访问开发者平台
微信开发者平台地址为：https://developers.weixin.qq.com/platform/，用户可以使用微信扫码登录。登录后即可看到自己作为管理员或者开发者的公众号/服务号的数量信息。


如该数字为 0 ，这说明当前用户不是任何公众号/服务号的管理员或者开发者。如需注册公众号/服务号或者绑定为公众号/服务号的管理员需前往微信公众平台操作，如需绑定成为公众号/服务号的开发者，则可联系公众号/服务号的管理员前往「微信开发者平台 - 右上角头像 - 账号管理 - 公众号/服务号」输入微信号添加开发者。关于添加成为公众号/服务号的开发者的规则细节可前往查看微信开发者平台成员管理介绍

2、开发管理
用户可在微信开发者平台完成公众号/服务号的开发管理，功能清单如下：

功能名称	功能描述	开发者平台路径
开发者ID(AppID)	查看公众号/服务号的开发者ID(AppID)	微信开发者平台 - 我的业务 - 公众号/服务号 - 基础信息
开发者密钥(AppSecret)	包含：启用、重置、冻结、解冻 AppSecret	微信开发者平台 - 我的业务 - 公众号/服务号 - 基础信息 - 开发密钥
API IP 白名单	调用公众号/服务号的接口时的请求IP必须添加至API IP 白名单中，否则调用接口将返回 40164 的错误码	微信开发者平台 - 我的业务 - 公众号/服务号 - 基础信息 - 开发密钥
JS接口安全域名	设置后，可在该域名下调用微信开放的 JS 接口能力	微信开发者平台 - 我的业务 - 公众号/服务号 - 基础信息 - 域名与消息推送配置
消息推送	启用后，用户发送的消息将转发至该地址，网站中设置的自动回复和自定义菜单将失效	微信开发者平台 - 我的业务 - 公众号/服务号 - 基础信息 - 域名与消息推送配置

3、接口管理
用户可在微信开发者平台查看消息与事件推送趋势以及接口的调用趋势

还可以查看接口权限以及调用额度

还可以设置告警规则

4、绑定关系与授权关系
此外，用户还可在开发者平台管理绑定关系和授权关系

 


 

开发指南 /消息与事件推送 /消息与事件推送介绍
原公众号文档（包含公众号与服务号）已升级为公众号（原订阅号）与服务号文档。公众号文档请直接参考本目录内容，服务号文档请 点击此处 前往。
消息与事件推送介绍
当公众号的用户发消息、或者发生了一些事件，微信平台需要主动推送消息给开发者的服务器，让开发者能自动完成一些动作。

配置说明
更多详细的消息加解密说明以及调试工具指引，可查看消息加解密说明

关于如何接受普通消息和事件推送，详情可查看接收普通消息以及接收事件推送

除了接受消息之外，开发者可以使用被动回复给发消息的用户回复消息，或使用发送客服消息接口 主动发消息

第一步：填写服务器配置
可在「微信开发者平台 - 我的业务 - 公众号 - 消息与事件推送」处进行配置。即，填写服务器地址（URL）、Token和EncodingAESKey，其中URL是开发者用来接收微信消息和事件的接口URL。Token可由开发者可以任意填写，用作生成签名（该Token会和接口URL中包含的Token进行比对，从而验证安全性）。EncodingAESKey由开发者手动填写或随机生成，将用作消息体加解密密钥。


具体配置说明如下：

URL服务器地址：开发者用来接收微信消息和事件的接口 URL，必须以 http:// 或 https:// 开头，分别支持 80 端口和 443 端口。
Token令牌：用于签名处理，下文会介绍相关流程。
EncodingAESKey：将用作消息体加解密密钥。
消息加解密方式：
明文模式：不使用消息加解密，明文发送，安全系数较低，不建议使用。
兼容模式：明文、密文共存，不建议使用。
安全模式：使用消息加解密，纯密文，安全系数高，强烈推荐使用。
数据格式：消息体的格式，仅支持 XML
开发者可选择消息加解密方式：明文模式、兼容模式和安全模式。

模式的选择与服务器配置在提交后都会立即生效，请开发者谨慎填写及选择。

加解密方式的默认状态为明文模式，选择兼容模式和安全模式需要提前配置好相关加解密代码，更多详细的消息加解密说明以及调试工具指引，可查看消息加解密说明

第二步：验证消息的确来自微信服务器
开发者提交信息后，微信服务器将发送GET请求到填写的服务器地址URL上，GET请求携带参数如下表所示：

参数	描述
signature	微信加密签名，signature结合了开发者填写的token参数和请求中的timestamp参数、nonce参数。
timestamp	时间戳
nonce	随机数
echostr	随机字符串
开发者通过检验signature对请求进行校验（下面有校验方式）。若确认此次GET请求来自微信服务器，请原样返回echostr参数内容，则接入生效，成为开发者成功，否则接入失败。加密/校验流程如下：

将token、timestamp、nonce三个参数进行字典序排序
将三个参数字符串拼接成一个字符串进行sha1加密
开发者获得加密后的字符串可与signature对比，标识该请求来源于微信
检验signature的PHP示例代码：

private function checkSignature()
{
    $signature = $_GET["signature"];
    $timestamp = $_GET["timestamp"];
    $nonce = $_GET["nonce"];
	
    $token = TOKEN;
    $tmpArr = array($token, $timestamp, $nonce);
    sort($tmpArr, SORT_STRING);
    $tmpStr = implode( $tmpArr );
    $tmpStr = sha1( $tmpStr );
    
    if( $tmpStr == $signature ){
        return true;
    }else{
        return false;
    }
}
PHP示例代码下载：下载

为了便于开发者调试，我们提供了URL验证工具供开发者使用。

开发者需填写AccessToken、URL地址、Token，点击“检查参数并发起验证”后，调试工具会发送GET请求到URL所指的服务器，并返回相关调试信息。

第三步：依据接口文档实现业务逻辑
验证URL有效性成功后即接入生效。开发者可以在公众平台网站中申请微信认证，认证成功后，将获得更多接口权限，满足更多业务需求。

接入成功后，用户每次向公众号发送消息、或者产生自定义菜单、或产生微信支付订单等情况时，开发者填写的服务器配置URL将得到微信服务器推送过来的消息和事件，开发者可以依据自身业务逻辑进行响应，如回复消息。

用户向公众号发送消息时，公众号方收到的消息发送者是一个OpenID，是使用用户微信号加密后的结果，每个用户对每个公众号有一个唯一的OpenID。

开发者可以通过调用微信 API 接口来实现自己的业务。

注意事项
启用后，用户发送的消息将转发至该地址，网站中设置的自动回复和自定义菜单将失效。


开发指南 /消息与事件推送 /消息加解密说明
原公众号文档（包含公众号与服务号）已升级为公众号（原订阅号）与服务号文档。公众号文档请直接参考本目录内容，服务号文档请 点击此处 前往。
消息加解密说明
公众号消息加解密是公众平台为了进一步加强公众号安全保障，提供的新机制。开发者需注意，公众号主动调用API的情况将不受影响。只有被动回复用户的消息时，才需要进行消息加解密。消息加解密的具体修改包括：

新增消息体签名验证，用于公众平台和公众号验证消息体的正确性
针对推送给微信公众号的普通消息和事件消息，以及推送给设备公众号的设备消息进行加密
公众号对密文消息的回复也要求加密
请开发者查看接入指引和开发者FAQ来接入消息体签名及加解密功能：接入指引

启用加解密功能（即选择兼容模式或安全模式）后，公众平台服务器在向公众号服务器配置地址（可在「微信开发者平台 - 我的业务 - 公众号 - 消息与事件推送」处修改）推送消息时，URL将新增加两个参数（加密类型和消息体签名），并以此来体现新功能。加密算法采用AES，具体的加解密流程和方案请看接入指引、技术方案和示例代码。


为了配合消息加密功能的上线，并帮助开发者适配新特性，公众平台提供了3种加解密的模式供开发者选择，即明文模式、兼容模式、安全模式(可在“开发者中心”选择相应模式),选择兼容模式和安全模式前，需在开发者中心填写消息加解密密钥EncodingAESKey。

明文模式
维持现有模式，没有适配加解密新特性，消息体明文收发，默认设置为明文模式
兼容模式
公众平台发送消息内容将同时包括明文和密文，消息包长度增加到原来的3倍左右；公众号回复明文或密文均可，不影响现有消息收发；开发者可在此模式下进行调试
安全模式（推荐）
公众平台发送消息体的内容只含有密文，公众号回复的消息体也为密文，建议开发者在调试成功后使用此模式收发消息
EncodingAESKey 介绍
微信公众平台采用AES对称加密算法对推送给公众号的消息体对行加密，EncodingAESKey则是加密所用的秘钥。公众号用此秘钥对收到的密文消息体进行解密，回复消息体也用此秘钥加密。

此外，微信公众平台为开发者提供了5种语言的示例代码（包括C++、php、Java、Python和C#版本，点击下载。

接入指引
消息解密方式为明文模式
假设URL配置为https://www.qq.com/revice， 数据格式为JSON，Token="AAAAA"。
推送的URL链接：https://www.qq.com/recive?signature=899cf89e464efb63f54ddac96b0a0a235f53aa78&timestamp=1714037059&nonce=486452656
推送的包体：
{
    "ToUserName": "gh_97417a04a28d",
    "FromUserName": "o9AgO5Kd5ggOC-bXrbNODIiE3bGY",
    "CreateTime": 1714037059,
    "MsgType": "event",
    "Event": "debug_demo",
    "debug_str": "hello world"
}
校验signature签名是否正确，以判断请求是否来自微信服务器。
将token、timestamp（URL参数中的）、nonce（URL参数中的）三个参数进行字典序排序，排序后结果为:["1714037059","486452656","AAAAA"]
将三个参数字符串拼接成一个字符串："1714037059486452656AAAAA"
进行sha1计算签名：899cf89e464efb63f54ddac96b0a0a235f53aa78
与URL链接中的signature参数进行对比，相等说明请求来自微信服务器，合法。
回包给微信，具体回包内容取决于特定接口文档要求，如无特定要求，回复空串或者success即可。
消息解密方式为安全模式
假设URL配置为https://www.qq.com/revice， 数据格式为JSON，Token="AAAAA"，EncodingAESKey="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"，公众号Appid="wxba5fad812f8e6fb9"。
推送的URL链接：：https://www.qq.com/recive?signature=6c5c811b55cc85e0e1b54100749188c20beb3f5d&timestamp=1714112445&nonce=415670741&openid=o9AgO5Kd5ggOC-bXrbNODIiE3bGY&encrypt_type=aes&msg_signature=046e02f8204d34f8ba5fa3b1db94908f3df2e9b3
推送的包体：
{
    "ToUserName": "gh_97417a04a28d",
    "Encrypt": "+qdx1OKCy+5JPCBFWw70tm0fJGb2Jmeia4FCB7kao+/Q5c/ohsOzQHi8khUOb05JCpj0JB4RvQMkUyus8TPxLKJGQqcvZqzDpVzazhZv6JsXUnnR8XGT740XgXZUXQ7vJVnAG+tE8NUd4yFyjPy7GgiaviNrlCTj+l5kdfMuFUPpRSrfMZuMcp3Fn2Pede2IuQrKEYwKSqFIZoNqJ4M8EajAsjLY2km32IIjdf8YL/P50F7mStwntrA2cPDrM1kb6mOcfBgRtWygb3VIYnSeOBrebufAlr7F9mFUPAJGj04="
}
校验msg_signature签名是否正确，以判断请求是否来自微信服务器。注意：不要使用signature验证！
将token、timestamp（URL参数中的）、nonce（URL参数中的）、Encrypt（包体内的字段）四个参数进行字典序排序，排序后结果为: ["+qdx1OKCy+5JPCBFWw70tm0fJGb2Jmeia4FCB7kao+/Q5c/ohsOzQHi8khUOb05JCpj0JB4RvQMkUyus8TPxLKJGQqcvZqzDpVzazhZv6JsXUnnR8XGT740XgXZUXQ7vJVnAG+tE8NUd4yFyjPy7GgiaviNrlCTj+l5kdfMuFUPpRSrfMZuMcp3Fn2Pede2IuQrKEYwKSqFIZoNqJ4M8EajAsjLY2km32IIjdf8YL/P50F7mStwntrA2cPDrM1kb6mOcfBgRtWygb3VIYnSeOBrebufAlr7F9mFUPAJGj04=", "1714112445", "415670741", "AAAAA"]。
将四个参数字符串拼接成一个字符串，然后进行sha1计算签名：046e02f8204d34f8ba5fa3b1db94908f3df2e9b3
与URL参数中的msg_signature参数进行对比，相等说明请求来自微信服务器，合法。
解密消息体"Encrypt"密文。
AESKey = Base64_Decode( EncodingAESKey + "=" )，EncodingAESKey 尾部填充一个字符的 "=", 用 Base64_Decode 生成 32 个字节的 AESKey；
将Encrypt密文进行Base64解码，得到TmpMsg， 字节长度为224
将TmpMsg使用AESKey进行AES解密，得到FullStr，字节长度为205。AES 采用 CBC 模式，秘钥长度为 32 个字节（256 位），数据采用 PKCS#7 填充； PKCS#7：K 为秘钥字节数（采用 32），Buf 为待加密的内容，N 为其字节数。Buf 需要被填充为 K 的整数倍。在 Buf 的尾部填充(K - N%K)个字节，每个字节的内容 是(K - N%K)。微信团队提供了多种语言的示例代码（包括 PHP、Java、C++、Python、C#），请开发者尽量使用示例代码，仔细阅读技术文档、示例代码及其注释后，再进行编码调试。示例下载
FullStr=random(16B) + msg_len(4B) + msg + appid，其中：
random(16B)为 16 字节的随机字符串；
msg_len 为 msg 长度，占 4 个字节(网络字节序)；
msg为解密后的明文；
appid为公众号Appid，开发者需验证此Appid是否与自身公众号相符。
在此示例中：
random(16B)="a8eedb185eb2fecf"
msg_len=167（注意：需按网络字节序，占4个字节）
msg="{"ToUserName":"gh_97417a04a28d","FromUserName":"o9AgO5Kd5ggOC-bXrbNODIiE3bGY","CreateTime":1714112445,"MsgType":"event","Event":"debug_demo","debug_str":"hello world"}"
appid="wxba5fad812f8e6fb9"
回包给微信服务器，首先需确定回包包体的明文内容，具体取决于特定接口文档要求，如无特定要求，回复空串或者success（无需加密）即可，其他回包内容需加密处理。这里假设回包包体的明文内容为"{"demo_resp":"good luck"}"，数据格式为JSON，下面介绍如何对回包进行加密：
回包格式如下，具体取决于你配置的数据格式（JSON或XML）,其中：
Encrypt：加密后的内容；
MsgSignature：签名，微信服务器会验证签名；
TimeStamp：时间戳；
Nonce：随机数
{
    "Encrypt": "${msg_encrypt}$",
    "MsgSignature": "${msg_signature}$",
    "TimeStamp": ${timestamp}$,
    "Nonce": ${nonce}$
}
<xml>
    <Encrypt><![CDATA[${msg_encrypt}$]]></Encrypt>
    <MsgSignature><![CDATA[${msg_signature}$]]></MsgSignature>
    <TimeStamp>${timestamp}$</TimeStamp>
    <Nonce><![CDATA[${nonce}$]]></Nonce>
</xml>
Encrypt的生成方法：
AESKey = Base64_Decode( EncodingAESKey + "=" )，EncodingAESKey 尾部填充一个字符的 "=", 用 Base64_Decode 生成 32 个字节的 AESKey；
构造FullStr=random(16B) + msg_len(4B) + msg + appid，其中
random(16B)为 16 字节的随机字符串；
msg_len 为 msg 长度，占 4 个字节(网络字节序)；
msg为明文；
appid为公众号Appid。
在此示例中：
random(16B)="707722b803182950"
msg_len=25（注意：需按网络字节序，占4个字节）
msg="{"demo_resp":"good luck"}"
appid="wxba5fad812f8e6fb9"
FullStr的字节大小为63
将FullStr用AESKey进行加密，得到TmpMsg，字节大小为64。AES 采用 CBC 模式，秘钥长度为 32 个字节（256 位），数据采用 PKCS#7 填充； PKCS#7：K 为秘钥字节数（采用 32），Buf 为待加密的内容，N 为其字节数。Buf 需要被填充为 K 的整数倍。在 Buf 的尾部填充(K - N%K)个字节，每个字节的内容 是(K - N%K)。微信团队提供了多种语言的示例代码（包括 PHP、Java、C++、Python、C#），请开发者尽量使用示例代码，仔细阅读技术文档、示例代码及其注释后，再进行编码调试。示例下载
对TmpMsg进行Base64编码，得到Encrypt="ELGduP2YcVatjqIS+eZbp80MNLoAUWvzzyJxgGzxZO/5sAvd070Bs6qrLARC9nVHm48Y4hyRbtzve1L32tmxSQ=="。
TimeStamp由开发者生成，使用当前时间戳即可，示例使用1713424427。
Nonce回填URL参数中的nonce参数即可，示例使用415670741。
MsgSignature的生成方法：
将token、TimeStamp（回包中的）、Nonce（回包中的）、Encrypt（回包中的）四个参数进行字典序排序，排序后结果为: ["1713424427", "415670741", "AAAAA", "ELGduP2YcVatjqIS+eZbp80MNLoAUWvzzyJxgGzxZO/5sAvd070Bs6qrLARC9nVHm48Y4hyRbtzve1L32tmxSQ=="]
将四个参数字符串拼接成一个字符串，并进行sha1计算签名：1b9339964ed2e271e7c7b6ff2b0ef902fc94dea1
最终回包为：
{
    "Encrypt": "ELGduP2YcVatjqIS+eZbp80MNLoAUWvzzyJxgGzxZO/5sAvd070Bs6qrLARC9nVHm48Y4hyRbtzve1L32tmxSQ==",
    "MsgSignature": "1b9339964ed2e271e7c7b6ff2b0ef902fc94dea1",
    "TimeStamp": 1713424427,
    "Nonce": "415670741"
}
为了便于开发者调试，我们提供了相关的调试工具（请求构造、调试工具）供开发者使用。

“请求构造”允许开发者填写相关参数后，生成debug_demo事件发包或回包的相关调试信息，供开发者使用。
“调试工具”允许开发者填写AccessToken、Body后，微信服务器会拉取你在公众号后台配置的消息推送配置，实际推送一条debug_demo事件供开发者调试。

开发指南 /服务端 API 调用 /接口调用概述
原公众号文档（包含公众号与服务号）已升级为公众号（原订阅号）与服务号文档。公众号文档请直接参考本目录内容，服务号文档请 点击此处 前往。
服务端 API 调用说明
本文档主要介绍如何调用公众号的 API。

获取 AppID 和 AppSecret
微信开发者平台已支持管理公众号的基本信息、开发信息以及绑定关系和授权关系。


操作路径为：「微信开发者平台 - 扫码登录 - 我的业务 - 公众号」，点击后即可进入到公众号的管理页面

可在此处直接修改 AppSecret 、API IP 白名单信息、JS接口安全域名以及消息推送的配置

AppSecret 管理
支持启用、重置、冻结以及解冻的操作；其中冻结与解冻的操作需 10分钟后方可生效。

如长期无AppSecret的使用需求，开发者可以前往「微信开发者平台 - 扫码登录 - 我的业务 - 公众号 - 开发密钥」对AppSeceret进行冻结，提高账号的安全性。

AppSecret冻结后，开发者无法使用AppSecret获取Access token（接口返回错误码40243），不影响账号基本功能的正常使用，不影响通过第三方授权调用后台接口，不影响云开发调用后台接口。

开发者可前往「微信开发者平台 - 扫码登录 - 我的业务 - 公众号 - 开发密钥」AppSecret进行解冻。

如果secret被冻结了调用getAccessToken 会出现 40243 错误

「微信云托管」具有「免鉴权调用微信开放服务接口」特性的能力，免密钥，全程不暴漏任何信息，开发者无需维护access_token，那对于接口请求的合法性判定，完全由与微信同链路的微信云托管参与实施，具体可前往云托管文档。（如你使用云托管的云调用，则不需要后续生成 Access Token 过程，也无需配置 IP 白名单）

注意：平台并不保存 AppSecret，如已忘记了AppSecret，需要重置。

IP 白名单
即白名单内的 IP 才可以调用获取接口调用凭据接口 或 获取稳定版接口调用凭据接口，否则会提示 61004 错误

生成 Access Token
参考获取接口调用凭据接口 或 获取稳定版接口调用凭据 传入上一步获取的 AppID 和 AppSecret 获取 Access Token，两者都可以正常获取，推荐使用稳定版接口。

获取的 Access Token 可用于服务端 API 的调用。

以下是一些注意事项：

access_token的有效期目前为2个小时，需定时刷新，重复获取将导致上次获取的access_token失效。建议公众号开发者使用中控服务器统一获取和刷新access_token，其他业务逻辑服务器所使用的access_token均来自于该中控服务器，不应该各自去刷新，否则容易造成冲突，导致access_token覆盖而影响业务；
目前access_token的有效期通过返回的expires_in来传达，目前是7200秒之内的值。中控服务器需要根据这个有效时间提前去刷新新access_token。在刷新过程中，中控服务器可对外继续输出的老access_token，此时公众平台后台会保证在5分钟内，新老access_token都可用，这保证了第三方业务的平滑过渡；
access_token的有效时间可能会在未来有调整，所以中控服务器不仅需要内部定时主动刷新，还需要提供被动刷新access_token的接口，这样便于业务服务器在API调用获知access_token已超时的情况下，可以触发access_token的刷新流程。
access_token是公众号的全局唯一接口调用凭据，公众号调用各接口时都需使用access_token。开发者需要进行妥善保存。
access_token的存储至少要保留512个字符空间。
这里提供一个较为简单的 access_token 存储和使用方案：

中控服务器定时（建议1小时）调用微信api，刷新access_token,将新的access_token 存入存储；
其他工作服务器每次调用微信api时从mysql(或其他存储)获取access_token，并可在内存缓存一段时间（建议1分钟）；
对于可能存在风险的调用，在开发者进行获取 access_token 调用时进入风险调用确认流程，需要用户管理员确认后才可以成功获取。具体流程为：

开发者通过某IP发起调用->平台返回错误码[89503]并同时下发模板消息给公众号管理员->公众号管理员确认该IP可以调用->开发者使用该IP再次发起调用->调用成功。
如公众号管理员第一次拒绝该IP调用，用户在1个小时内将无法使用该IP再次发起调用，如公众号管理员多次拒绝该IP调用，该IP将可能长期无法发起调用。平台建议开发者在发起调用前主动与管理员沟通确认调用需求，或请求管理员开启IP白名单功能并将该IP加入IP白名单列表。
公众号调用各接口时，一般会获得正确的结果，具体结果可见对应接口的说明；返回错误时，可根据返回码来查询错误原因，返回码解释一般在各个接口的文档中有描述，如无特意描述，可直接参考全局返回码

接口域名
开发者可以根据自己的服务器部署情况，选择最佳的接入域名（延时更低，稳定性更高）。

除此之外，可以将其他接入域名用作容灾用途，当网络链路发生故障时，可以考虑选择备用域名来接入。请开发者使用域名进行API接口请求，不要使用IP作为访问。若有需要开通网络策略，开发者可以从获取微信服务器IP地址接口定期获取最新的IP信息。

通用域名(api.weixin.qq.com)，使用该域名将访问官方指定就近的接入点；
通用异地容灾域名(api2.weixin.qq.com)，当上述域名不可访问时可改访问此域名；
上海域名(sh.api.weixin.qq.com)，使用该域名将访问上海的接入点；
深圳域名(sz.api.weixin.qq.com)，使用该域名将访问深圳的接入点；
香港域名(hk.api.weixin.qq.com)，使用该域名将访问香港的接入点。

接口限频
公众号调用接口并不是无限制的。为了防止公众号的程序错误而引发微信服务器负载异常，默认情况下，每个公众号调用接口都不能超过一定限制，具体可参考接口限频说明

问题排查
如果你在调用接口时遇到问题，可参考接口报警和排查指引

此外，调用接口遇到报错可前往微信开发者平台使用智能 API 诊断工具，一键精准定位和解决问题。


开发指南 /服务端 API 调用 /接口限制说明
原公众号文档（包含公众号与服务号）已升级为公众号（原订阅号）与服务号文档。公众号文档请直接参考本目录内容，服务号文档请 点击此处 前往。
接口调用额度说明
公众号调用接口并不是无限制的。为了防止公众号的程序错误而引发微信服务器负载异常，默认情况下，每个公众号调用接口都不能超过一定限制，当超过一定限制时，调用对应接口会收到如下错误返回码：

{"errcode":45009,"errmsg":"api freq out of limit"}
开发者可以登录微信公众平台，在账号后台开发者中心接口权限模板查看账号各接口当前的日调用上限和实时调用量，对于认证账号可以对实时调用量清零，说明如下：

由于指标计算方法或统计时间差异，实时调用量数据可能会出现误差，一般在1%以内。
每个账号每月共10次清零操作机会，清零生效一次即用掉一次机会（10次包括了平台上的清零和调用接口API的清零）。
第三方帮助公众号调用时，实际上是在消耗公众号自身的quota。
每个有接口调用限额的接口都可以进行清零操作。
当账号粉丝数超过10W/100W/1000W时，部分接口的日调用上限会相应提升，以公众号MP后台开发者中心页面中标明的数字为准。
接口调用额度
新注册账号各接口调用额度限制如下：

接口	每日限额
获取access_token	2000
自定义菜单创建	1000
自定义菜单查询	10000
自定义菜单删除	1000
创建分组	1000
获取分组	1000
修改分组名	1000
移动用户分组	100000
上传多媒体文件	100000
下载多媒体文件	200000
发送客服消息	500000
高级群发接口	100
上传图文消息接口	10
删除图文消息接口	10
获取带参数的二维码	100000
获取关注者列表	500
获取用户基本信息	5000000
获取网页授权access_token	无
刷新网页授权access_token	无
网页授权获取用户信息	无
设置用户备注名	10000
草稿箱 - 新建草稿	1000
草稿箱 - 获取草稿	500
草稿箱 - 删除草稿	1000
草稿箱 - 修改草稿	1000
草稿箱 - 获取草稿总数	1000
草稿箱 - 获取草稿列表	1000
发布能力 - 发布接口	100
发布能力 - 发布状态轮询接口	100
发布能力 - 删除发布	10
发布能力 - 通过 article_id 获取已发布文章	100
发布能力 - 获取成功发布列表	100
请注意，在测试号申请页中申请的测试号，接口调用额度限制如下：

接口	每日限额
获取access_token	200
自定义菜单创建	100
自定义菜单查询	1000
自定义菜单删除	100
创建分组	100
获取分组	100
修改分组名	100
移动用户分组	1000
素材管理-临时素材上传	500
素材管理-临时素材下载	1000
发送客服消息	50000
获取带参数的二维码	10000
获取关注者列表	100
获取用户基本信息	500000
获取网页授权access_token	无
刷新网页授权access_token	无
网页授权获取用户信息	无
重置 API 调用次数
我们提供重置API调用次数接口 、重置指定API调用次数以及 使用AppSecret重置API调用次数，可对 API 调用（包括第三方帮其调用）次数进行清零，详情查看对应接口文档。


开发指南 /服务端 API 调用 /接口报警和排查指引
原公众号文档（包含公众号与服务号）已升级为公众号（原订阅号）与服务号文档。公众号文档请直接参考本目录内容，服务号文档请 点击此处 前往。
接口报警和排查指引
概要说明
微信公众平台已对外开放接口报警，当微信服务器向开发者推送消息失败次数达到预定阈值时，会将报警消息发送到指定微信报警群中（设置方式：公众平台->开发-运维中心->接口报警），请开发者积极主动关注报警，即时解决故障，提高微信公众号的服务质量。

为了更好地根据报警信息尾部的实例（提供了openid及时间戳stamp）进行问题排查，开发者需要在接入层、逻辑层等每一个层级都加上包含关键信息的详细日志，以利于快速定位问题。

接口报警
报警目前有2类：

通用报警
所有开发者都需要关注。

类型	描述
DNS失败	微信服务器向公众号推送消息或事件时，解析DNS失败
DNS超时	微信服务器向公众号推送消息或事件时，解析DNS超时，超时时间为5秒
连接超时	微信服务器连接公众号开发者服务器时发生超时，超时时间为5秒
请求超时	微信服务器向公众号推送消息或事件后，开发者5秒内没有返回
回应失败	微信服务器向公众号推送消息或事件后，得到的回应不合法
MarkFail（自动屏蔽）	微信服务器向公众号推送消息或事件发生多次失败后，暂时不推送消息，一分钟后解除屏蔽
公众号第三方平台报警
只有在微信开放平台（open.weixin.qq.com）上申请成为公众号第三方平台的开发者，才需要关注此报警。

类型	描述
推送component_verify_ticket超时	推送component_verify_ticket时，开发者5S内没有返回
推送component_verify_ticket失败	推送component_verify_ticket时，开发者没有返回success
推送第三方平台消息超时	推送第三方平台消息（如取消授权消息）等，第三方平台5秒内没有返回
推送第三方平台消息失败	推送第三方平台消息（如取消授权消息）等，第三方平台没有返回success
报警内容说明
报警内容描述：

appid：公众号appid
昵称: 公众号昵称
时间：所有报警，都会提供首次发生异常的时间。（如首次发生超时的时间，首次发生回应失败的时间）
内容：错误的具体描述
次数：发生失败的次数
错误样例：错误样例里注明了一些帮助查找问题的信息。如：首次超时开发者的IP和推送消息类型。如果是回应失败，错误样例还会注明首次回应失败时开发者的回包。
一般情况下，通过报警提供的IP，时间，消息类型，能够比较快速的定位到第三方发生问题的原因。

报警类型
下面对具体的报警做示例以及排查指引说明。

超时报警
Appid: wxxxxxx
昵称: WxNickName
时间: 2014-12-01 20:12:00
内容: 微信服务器向公众号推送消息或事件后，开发者5秒内没有返回
次数: 5分钟 1272次
错误样例: [IP=203.205.140.29][Event=UnSubscribe]
该报警表示：微信服务器向开发者推送取消关注事件时，开发者没有在5秒内返回结果。在2014-12-01 20:12:00-2014-12-01 20:17:00这5分钟内发生了1272次。其中这5分钟内第一次发生超时的时间是：2014-12-01 20:12:00， 开发者的IP是：203.205.140.29，事件类型是取消关注事件。

回应失败
Appid: wxxxx
昵称: WxNickName
时间: 2014-12-01 20:12:00
内容: 微信服务器向公众号推送消息或事件后，得到的回应不合法
次数: 5分钟 1320次
错误样例: [Event=Click] [ip=58.248.9.218][response_length=10][response_content=Error 500:]
该报警表示：微信服务器向开发者推送自定义菜单点击事件时，开发者的返回结果不合法。在2014-12-01 20:12:00-2014-12-01 20:17:00这5分钟内发生了1320次。其中这5分钟内第一次发生回应失败的时间是：2014-12-01 20:12:00， 开发者的IP是：58.248.9.218，事件类型是点击菜单事件，第三方返回的内容长度为10个字节，内容为“Error 500:”。

连接超时
Appid: wxxxx
昵称: WxNickName
时间: 2015-02-04 20:13:09
内容: 微信服务器连接公众号开发者服务器时发生超时，超时时间为5秒
次数: 5分钟 7289次
错误样例: [IP=180.150.190.135][Msg=Text]
该报警表示：微信服务器向开发者推送粉丝发来的文本消息时，无法连接到开发者填写的服务器地址。在2015-02-04 20:13:09-2015-02-04 20:18:00这5分钟内发生了7289次，这5分钟内第一次发生连接超时的时间是：2015-02-04 20:13:09， 开发者的IP是：180.150.190.135，事件类型是用户推送的消息。

排查指引
DNS失败
该错误为微信服务器在推送消息给开发者时，解析dns失败。如遇到此报警，请开发者确认：

填写的url,域名是否有误；
域名是否发生变化，如过期，更新等。
如果不是以上2个问题，请联系微信公众平台。问题解决方案：

Ping测试你们MP上配置的url里的域名，确认是否能够得到正确的IP。如不能得到或者错误，请到你们的域名托管商管理系统上检查配置。
如1能够得到正确的IP，又有DNS失败的报警；请使用DNS服务器182.254.116.116 来再测试验证。Linux : dig @182.254.116.116 域名；windows 修改网络配置里的DNS服务器地址，然后再ping 域名。如果得到的IP不正确或者得不到，请联系微信团队。
DNS超时
目前不会有此错误。

连接超时
该错误是微信服务器和开发者服务器3S内未连接成功。报警消息会提供出首次发生连接失败的时间和连接的IP。如遇此报警，请开发者确认：

该IP是否有误。
该IP机器是否过载，连接过多。
如果是第三方提供服务器托管，托管商是否有故障。
网络运营商是否有故障。
是否设置了防火墙等网络策略，可为微信服务器的IP增设白名单。详细参看获取微信服务器IP地址
是否网络不通，可通过网络检测排查。
问题解决方案如下：

查看是否网络环境问题。使用获取微信推送服务器IP接口，获取微信回调服务器的IP，在你的服务上 ping 测试，检查你们服务器到微信回调用服务器的网络质量情况。如有网络问题，请联系你们的服务器提供商解决。
查看接入层服务器连接数，负载，nginx的配置，允许的连接个数。查看nginx错误日志是否有“Connection reset by peer”或“Connection timed out”错误日志，如有说明nginx连接数过超负载。
建议搭建测试工具，对系统进行心跳检查，对系统负载，连接数，处理数，处理耗时进行实时监控报警。
对于nginx配置，这里提供官方文档和一篇简单配置介绍链接，希望有帮助： http://nginx.org/en/docs/ ，重点关注连接数配置，日志配置等。nginx的一些重要配置参考例子如下：

worker_processes  16;          //CPU核数
error_log  logs/error.log  info;   //错误日志log
worker_rlimit_nofile 102400;     //打开最大句柄数
events {
   worker_connections  102400;   //允许最大连接数
}
//请求日志记录，关键字段：request_time-请求总时间，upstream_response_time后端处理时 间
log_format  main  '$remote_addr  - $remote_user [$time_local] "$request" '
                 '$status $body_bytes_sent "$http_referer" '
                  '"$http_user_agent" "$http_x_forwarded_for" "$host"  "$cookie_ssl_edition" '
                 '"$upstream_addr"   "$upstream_status"  "$request_time"  '
                 '"$upstream_response_time" ';
access_log  logs/access.log  main;
请求超时
微信服务器向开发者服务器推送消息或事件，开发者5秒内没有返回。请求超时时，报警消息会提供第一次出现请求超时的时间，开发者IP和消息类型。请开发者确认：

该IP是否有误
该IP是否接收到报警消息给出的该消息类型的请求
该请求是否处理时间过长
解决方案：

每个模块都需要有完整的日志，能够查出每个请求在每个模块的耗时信息，配合微信报警提供信息，能够很容易的定位到是哪个服务器出问题。常见的原因是：

机器负载太高，耗时增加
机器处理异常，消息丢失
机器异常，对于机器处理异常，建议尽快修复bug，对于机器异常，请尽快屏蔽有问题的机器。这里对机器负载太高，简单提供可行的解决方案。
方案一：优化性能，扩容。检查负载情况（cpu，内存，io，网络，详见附录），根据具体性能瓶颈的不同，采取不同的优化方式。

方案二：异步处理。如果微信服务器推送的消息来不及实时处理，可将消息先存储，先返回success给微信服务器，后台可后续再处理消息，如果需要回复用户消息，可通过调用客服消息接口API再回复用户消息。

回应失败
开发者没有按照文档的回复消息格式进行回复消息，或者发生网络错误，会报警回应失败，报警消息会提供第一次出现请求回应失败的时间，开发者的IP，消息类型以及回应的消息内容，请开发者确认：

该IP是否有误
该IP是否发生网络错误
该业务处理逻辑是否没有按照wiki规范回复消息，或是进入了异常逻辑。
MarkFail（自动屏蔽）
微信后台会实时统计开发者的失败次数。在推送消息给开发者发生大量失败时，微信服务器会自动屏蔽开发者，1分钟内不再推送任何消息，并会发送报警到微信群。此报警是级别最高的报警，开发者在收到此报警时请尽快处理后台故障，恢复服务。事实上，开发者在收到此报警前，必然会收到连接超时，请求超时或回应失败等报警，需要开发者即时去解决这些故障，避免被微信服务器屏蔽，严重影响公众号服务！

推送component_verify_ticket超时
只有公众号第三方平台开发者会收到，其他公众号开发者无需关注。由于公众号第三方平台承载了更多的公众号，所以公众号第三方平台的服务质量需要更严格要求和报警，所以把这4个特殊的事件单独报警。关于公众号第三方平台的具体申请与开发实现，请前往微信开放平台（open.weixin.qq.com）

推送component_verify_ticket失败
只有公众号第三方平台开发者会收到，其他公众号开发者无需关注。由于公众号第三方平台承载了更多的公众号，所以公众号第三方平台的服务质量需要更严格要求和报警，所以把这4个特殊的事件单独报警。关于公众号第三方平台的具体申请与开发实现，请前往微信开放平台（open.weixin.qq.com）

推送组件消息超时
只有公众号第三方平台开发者会收到，其他公众号开发者无需关注。由于公众号第三方平台承载了更多的公众号，所以公众号第三方平台的服务质量需要更严格要求和报警，所以把这4个特殊的事件单独报警。关于公众号第三方平台的具体申请与开发实现，请前往微信开放平台（open.weixin.qq.com）

推送组件消息失败
只有公众号第三方平台开发者会收到，其他公众号开发者无需关注。由于公众号第三方平台承载了更多的公众号，所以公众号第三方平台的服务质量需要更严格要求和报警，所以把这4个特殊的事件单独报警。关于公众号第三方平台的具体申请与开发实现，请前往微信开放平台（open.weixin.qq.com）

常用工具
下面对查看服务器性能负载的常用工具做简单介绍，详细的工具使用请另行查阅。

查看CPU的性能负载
uptime：用于观察服务器整体负载，系统负载指运行队列（1分钟、5分钟、15分钟前）的平均长度， 正常情况需要小于cpu个数。
vmstat：vmstat是Virtual Meomory Statistics（虚拟内存统计）的缩写，可对操作系统的虚拟内存、进程、CPU活动进行监控。他是对系统的整体情况进行统计，通常使用vmstat 5 5（表示每隔５秒生成一次数据，生成五次）命令测试。将得到一个数据汇总他能够反映真正的系统情况。
top：top命令是最流行Unix/Linux的性能工具之一。系统管理员可用运行top命令监视进程和Linux整体性能。
查看内存的性能负载
free：Linux下的free命令，可以用于查看当前系统内存的使用情况，它显示系统中剩余及已用的物理内存和交换内存，以及共享内存和被核心使用的缓冲区。
查看网络的性能负载
netstat：Netstat是控制台命令,是一个监控TCP/IP网络的非常有用的工具，它可以显示路由表、实际的网络连接以及每一个网络接口设备的状态信息。Netstat用于显示与IP、TCP、UDP和ICMP协议相关的统计数据，一般用于检验本机各端口的网络连接情况。
sar：sar（System Activity Reporter系统活动情况报告）是目前 Linux 上最为全面的系统性能分析工具之一，可以从多方面对系统的活动进行报告，包括：文件的读写情况、系统调用的使用情况、磁盘I/O、CPU效率、内存使用状况、进程活动及IPC有关的活动等。本文主要以CentOS 6.3 x64系统为例，介绍sar命令。
查看磁盘的性能负载
iostat：Linux下的iostat命令，可用于报告中央处理器（CPU）统计信息和整个系统、适配器、tty 设备、磁盘和 CD-ROM 的输入／输出统计信息。
nginx配置和排查指引
当出现直接超时、处理返回慢时的报警时，nginx侧的故障排查参考方法有如下： 1、检查请求日志情况， tail -f logs/access.log ，看upstream_status字段。

200：表示正常；
502/503/504：表示处理慢，或者后端down机；再看upstream_response_time返回的时间是否真的较慢，有没有上百毫秒，或更高的，有则说明是后端服务有问题。
404：表示请求的路径不存在或不对，文件不在了。需要检查你配置在公众平台上的url路径是否正确； 服务器上的文件、程序是否存在。
403：表示无权限访问。 检查一下nginx.conf 是否有特殊的访问配置。
499: 则是客户端的问题，请联系微信团队。 此错误少见。
检查错误日志情况，tail -f logs/error_log ，查看是否有connect() failed、Connection refused、 Connection reset by peer等error错误日志，有则说明有可能nginx出现的连接数超负载等情况。

查看系统的网络连接数情况确认是否有较大的链接数

netstat -n | awk '/^tcp/ {++S[$NF]} END {for(a in S) print a, S[a]}' 
CLOSED //无连接是活动的或正在进行    
LISTEN //服务器在等待进入呼叫    
SYN_RECV //一个连接请求已经到达，等待确认 
SYN_SENT //应用已经开始，打开一个连接    
ESTABLISHED //正常数据传输状态/当前并发连接数
FIN_WAIT1 //应用说它已经完成 
FIN_WAIT2 //另一边已同意释放
ITMED_WAIT //等待所有分组死掉
CLOSING //两边同时尝试关闭
TIME_WAIT //另一边已初始化一个释放
LAST_ACK //等待所有分组死掉 
查看系统的句柄配置情况，ulimit -n ，确认是否过小（小于请求数）

worker_rlimit_nofile、worker_connections配置项，是否过小（小于请求数）