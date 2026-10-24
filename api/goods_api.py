"""商品域接口封装：列表（分页/搜索/分类）与详情。"""

from api.base_api import BaseApi


class GoodsApi(BaseApi):

    def list_goods(self, page: int = None, page_size: int = None,
                   keyword: str = None, category: str = None):
        """GET /api/goods —— 全部走 query string；返回 data={list,total,page,page_size}。"""
        params = {"page": page, "page_size": page_size, "keyword": keyword, "category": category}
        params = {k: v for k, v in params.items() if v is not None}
        return self.client.get("/api/goods", params=params)

    def goods_detail(self, goods_id: int):
        """GET /api/goods/{id} —— 不存在/下架返回业务码 2001。"""
        return self.client.get(f"/api/goods/{goods_id}")
