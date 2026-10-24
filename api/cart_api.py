"""购物车域接口封装：查 / 加 / 改 / 删。全部需要登录（token 关联核心场景）。"""

from api.base_api import BaseApi


class CartApi(BaseApi):

    def get_cart(self):
        """GET /api/cart —— data={items:[...], total_amount, count}。"""
        return self.client.get("/api/cart")

    def add_cart(self, goods_id: int = None, quantity: int = None):
        """POST /api/cart/items —— 重复加购同商品数量累加；库存不足 2002。"""
        body = {"goods_id": goods_id, "quantity": quantity}
        body = {k: v for k, v in body.items() if v is not None}
        return self.client.post("/api/cart/items", json_body=body)

    def update_cart_item(self, item_id: int, quantity: int = None):
        """PUT /api/cart/items/{item_id} —— item 不存在 3002。"""
        body = {"quantity": quantity}
        body = {k: v for k, v in body.items() if v is not None}
        return self.client.put(f"/api/cart/items/{item_id}", json_body=body)

    def delete_cart_item(self, item_id: int):
        """DELETE /api/cart/items/{item_id}。"""
        return self.client.delete(f"/api/cart/items/{item_id}")
