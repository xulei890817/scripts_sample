#!/usr/bin/env python

# encoding: utf-8

'''
 * Create File Script_record_bitmex
 * Created by leixu on 2018/5/31
 * IDE PyCharm
'''
from MaxValue.utils import proxy

proxy.proxy = "http://192.168.2.24:1001"

from MaxValue.market import MarketClass
from MaxValue.plan import BasePlan, UpdateHandler
import asyncio
import arrow
import csv


class PlanA(BasePlan):
    def __init__(self, loop):
        super(PlanA, self).__init__(loop)
        fieldnames = ['timestamp', 'symbol', 'bidSize', 'bidPrice', 'askPrice', 'askSize']
        self.file1 = open("bitmex_quote.csv", "w", newline='')
        self.csv_writer = csv.DictWriter(self.file1, fieldnames=fieldnames)
        self.csv_writer.writeheader()

    def login_market(self):
        def bitmex_update_handler():
            def ticker(data):
                for i in data["data"]:
                    self.csv_writer.writerow(i)
                self.file1.flush()

            def k_line(data):
                pass

            def depth(data):
                pass
                # print(data)

            # 设置更新的callback
            setattr(bitmex_update_handler, "ticker", ticker)
            setattr(bitmex_update_handler, "k_line", k_line)
            setattr(bitmex_update_handler, "depth", depth)
            return bitmex_update_handler

        self.bitmex_market = self.login_into_market(MarketClass.BITMEX, update_handler=bitmex_update_handler)

    async def start_rule(self):
        # 订阅频道

        await self.bitmex_market.api.sub_channel("quote")
        # await self.bitmex_market.api.sub_channel("quote")
        # await self.bitmex_market.api.sub_channel("orderBook10 ")

        # 保持程序运行
        while True:
            await asyncio.sleep(2)


if __name__ == "__main__":
    c_loop = asyncio.get_event_loop()

    plan_a = PlanA(c_loop)
    print("开始运行计划" + str(arrow.get()))
    c_loop.run_until_complete(plan_a.start_rule())
