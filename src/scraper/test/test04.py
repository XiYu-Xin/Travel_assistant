"""
将景点详细页的原始HTML保存下来，为后续的数据解析做准备
部分景点详情页的url如下：
雷琼海口火山群世界地质公园：https://you.ctrip.com/sight/haikou37/3175.html?poiType=3&scene=online
海南热带野生动植物园：https://you.ctrip.com/sight/haikou37/3180.html?poiType=3&scene=online
可以观察到url的形式为：https://you.ctrip.com/{class}/{districtId}/{sightID}.html?poiType=3&scene=online
故将原始HTML保存到/data/raw中，命名为Class.districtId.sightId.html的形式。
"""
