#!/usr/bin/env python

# encoding: utf-8

'''
 * Create File Script_record_okex
 * Created by leixu on 2018/5/12
 * IDE PyCharm
'''
from MaxValue.utils import proxy

# 设置代理
# proxy.proxy = "http://192.168.2.24:1001"

from MaxValue.market import MarketClass
from MaxValue.plan import BasePlan, UpdateHandler
import asyncio
import arrow
import csv

# 加载api的key，这个变量自己设置
from token_dict import okex_api_key
from token_dict import okex_sign


class OkexUpdateHandler(UpdateHandler):

    def ticker(self, data):
        pass

    def k_line(self, data):
        pass

    def depth(self, data):
        pass


class PlanA(BasePlan):
    def __init__(self, loop):
        super(PlanA, self).__init__(loop)
        current_watch_dog = False

        def init_file_handler(self, time, loop):
            print(1111)
            fieldnames = ['timestamp', 'high', 'limitLow', 'vol', 'last', 'low', 'buy', 'hold_amount', 'sell', 'contractId',
                          'unitAmount', 'limitHigh']
            self.file1 = open(str(time.format("YYYY_MM_DD_HH_mm_ss")) + "okex.csv", "w", newline='')
            self.csv_writer = csv.DictWriter(self.file1, fieldnames=fieldnames)
            self.csv_writer.writeheader()

            self.file2 = open(str(time.format("YYYY_MM_DD_HH_mm_ss")) + 'okex_kline.csv', 'w')
            self.k_line_csv_writer = csv.writer(self.file2)
            self.k_line_csv_writer.writerow(["时间", "开盘价", "最高价", "最低价", "收盘价", "成交量(张)", "成交量(币)"])

        async def watch_dog(self, loop):
            nonlocal current_watch_dog
            while True:
                if not current_watch_dog:
                    print(1)
                    init_file_handler(self, arrow.now(), loop)
                    current_watch_dog = True
                else:
                    print(2)
                    # 每天0点
                    end_time = arrow.now().shift(days=+1).replace(hour=0, minute=0, second=0)
                    # 每一小时
                    # end_time = arrow.now().shift(hours=+1)
                    start_time = arrow.now()
                    sleep_time = (end_time - start_time).seconds
                    print(sleep_time)
                    asyncio.get_event_loop().call_later(sleep_time, init_file_handler, self, arrow.now(), loop)
                    # while arrow.now().float_timestamp < float_timestamp:
                    #     await asyncio.sleep(float_timestamp - arrow.now().float_timestamp)
                    await asyncio.sleep(sleep_time)

        asyncio.ensure_future(watch_dog(self, loop), loop=loop)

    def login_market(self):
        def okex_update_handler():
            def ticker(data):
                data_row = {"timestamp": arrow.get().float_timestamp}
                data_row.update(data["data"])
                self.csv_writer.writerow(data_row)  #:type csv
                self.file1.flush()

            def k_line(data):
                for i in data["data"]:
                    data_row = {"timestamp": arrow.get().float_timestamp}
                    data_row.update(data["data"])
                    self.k_line_csv_writer.writerow(i)
                self.file2.flush()

            def depth(data):
                pass
                # print(data)

            # 设置更新的callback
            setattr(okex_update_handler, "ticker", ticker)
            setattr(okex_update_handler, "k_line", k_line)
            setattr(okex_update_handler, "depth", depth)
            return okex_update_handler

        self.okex_market = self.login_into_market(MarketClass.OKEX, api_key=okex_api_key, sign=okex_sign, update_handler=okex_update_handler)

    async def start_rule(self):
        # 订阅频道

        await self.okex_market.api.sub_channel("ok_sub_futureusd_btc_ticker_quarter")
        await self.okex_market.api.sub_channel("ok_sub_futureusd_btc_kline_quarter_1min")
        # 如果无需订阅当前频道，可注释
        # await self.okex_market.api.sub_channel("ok_sub_futureusd_btc_depth_this_week")

        # 保持程序运行
        while True:
            await asyncio.sleep(2)


if __name__ == "__main__":
    c_loop = asyncio.get_event_loop()

    plan_a = PlanA(c_loop)
    print("开始运行计划" + str(arrow.get()))
    c_loop.run_until_complete(plan_a.start_rule())
