#-*- coding:utf-8 -*-
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.gen
import random
import asyncio
import aioredis
import json
from tornado.options import define,options,parse_command_line
define("port",default=9000,type=int)

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        print("hhhhhhhh")
        self.render("index.html")


class AsyncRequestHandler(tornado.websocket.WebSocketHandler):
    @tornado.gen.coroutine
    def on_message(self,*args,**kwargs):
        print("in get!")
        yield self._run_method("on_message",*args)

    @asyncio.coroutine
    def _run_async(self,coroutine,future_,*args,**kwargs):
        try:
            result = yield from coroutine(*args,**kwargs)
            future_.set_result(result)
        except Exception as e:
            future_.set_exception(e)
            print(traceback.format_exc())

    def _run_method(self,method_,message):
        coroutine = getattr(self,'%s_async' % method_,None)
        if not coroutine:
            raise tornado.websocket.WebSocketError(102)
        
        future_ = tornado.concurrent.Future()
        asyncio.async(
            self._run_async(coroutine,future_,message)
        )
        return future_

class WebSocketHandler(AsyncRequestHandler):
    def open(self, *args):
        print("New connection")
        a=random.randint(0,9)
        print(a)
        self.write_message("Welcome"+a*'xx')

    @asyncio.coroutine
    def on_message_async(self, message):
        #json的基准xlsx文档，加修改的xlsx元素，然后成为最后的xlsx文档
        print(message)
        recievejson=json.loads(message)
        print(recievejson)
        sendjson = [{"xlsxid":"111"},
                    [{"C":"0"},{"R":"2"}],
                    [{"C":"0"},{"R":"6"}],
                    ["0|2|first","0|3|second","0|4|third","0|5|forth","0|6|fifth"]
        ]
        xlsxid = int(sendjson[0]["xlsxid"])
        firstsendjsoncol=int(sendjson[1][0]['C'])
        firstsendjsonrow=int(sendjson[1][1]['R'])
        secondsendjsoncol=int(sendjson[2][0]['C'])
        secondsendjsonrow=int(sendjson[2][1]['R'])
        sendjson_redis=json.dumps(sendjson)
        #根据xlsxid 来从redis中筛选出保存的xls的json副本,然后根据范围对比查看元素是否冲突
        redis = self.application.redis
        redis_id=str(sendjson[0]["xlsxid"])
        yield from redis.set(redis_id,sendjson_redis)
        a= yield from redis.get(redis_id)
        myrandint=random.randint(1,10)
        print(myrandint)
        #
        #进行传递json对应的xlsx文档的范围与id匹配，如果相交就进行协商（为新建一个workspace或者载入一个workspace）
        print("xlsxid")
        print(a)
        #msgjson = [{"xlsxid":"111"},
        #            [{"C":"0"},{"R":"2"}],
        #            [{"C":"0"},{"R":"3"}],
        #            ["0|2|first","0|3|second"],
        #            '1'
        #    ]
        #msgjson = [{"xlsxid":"111"},
        #            [{"C":"0"},{"R":"2"}],
        #            [{"C":"2"},{"R":"19"}],
        #            ["0|2|first","0|3|second"],
        #            '1'
        #    ]
        msgjson = recievejson
        firstmsgjsoncol=int(msgjson[1][0]['C'])
        firstmsgjsonrow=int(msgjson[1][1]['R'])
        secondmsgjsoncol=int(msgjson[2][0]['C'])
        secondmsgjsonrow=int(msgjson[2][1]['R'])
        #在row上如果 r1side >= l2side and l1side <= r2side，
        #在col上如果 u2side >= d1side and d2side <=u1side,
        #flag   = msgjson[4]
        #先要判断是新建xlsx,还是追加修改xlsx,还有带function的修改
        #设置一个标志位
        #如果flag为1,就是追加修改当前xlsx,如果flag为0,就是新建一个xlsx，
        #如果 flag 为 3,就是带function的处理，function需要作用对象的范围，作用的函数
        #如果flag为4,就是用pandas导出xlsx
        #关于在func的依赖求值，用redis stack来记录操作顺序，然后按序实现这个函数
        #默认后面一块比前面一块要大点，这是不符合题意的
        #加上序列依赖的话，就需要保持顺序，也许还要处理粘包
        if   firstmsgjsoncol <= secondsendjsoncol and firstsendjsoncol <= secondmsgjsoncol and  secondsendjsonrow >= firstmsgjsonrow and  firstsendjsonrow <= secondmsgjsonrow :
            print("有交集！")
            #要协商确定写什么
        else:
            print("没交集！")
            #没交集直接写
        print("xlsxid")
        if a!='':
            #update redis里面的内容
            result=a+str(myrandint).encode('utf-8')
            self.write_message(str(result))
        #如果要导出xls,那么从redis读出json,然后用pandas导出xls


    #从redis里面拿出当前的json
    @asyncio.coroutine
    def getjsonfromredis(self,xlsxid):
        redis = self.application.redis
        #redis_id=str(sendjson[0]["xlsxid"])
        #yield from redis.set(redis_id,sendjson_redis)
        a= yield from redis.get(xlsxid)
        myrandint=random.randint(1,10)
        print(myrandint)
        return a


    def on_close(self):
        print("Connection closed")

#Application类的实现
#------------------------------------
class Application1(tornado.web.Application):
    def __init__(self):
        tornado.ioloop.IOLoop.configure('tornado.platform.asyncio.AsyncIOMainLoop')
        handlers = [
            (r"/index",IndexHandler),
            (r"/ws/", WebSocketHandler),
        ]
        print("hi world")
        super().__init__(handlers,debug=True)
    def init_with_loop(self,loop):
        self.redis = loop.run_until_complete(
            aioredis.create_redis(('localhost',6379),loop=loop)
        )
#------------------------------------

#app = tornado.web.Application([
#    (r'/', IndexHandler),
#    (r'/ws/', WebSocketHandler),
#])


if __name__ == '__main__':
    application = Application1()
    application.listen(options.port)
    loop = asyncio.get_event_loop()
    application.init_with_loop(loop)
    loop.run_forever()
