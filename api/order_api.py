"""订单域接口封装：创建（直购/购物车）、列表、详情、支付、取消。

create_order 是"上下游关联"的关键接口：
返回 data.order_id / order_no，由链路执行器 JSONPath 提取后传给后续步骤。
"""

from api.base_api import BaseApi


class OrderApi(BaseApi):

    def create_order(self, items: list = None, from_cart: bool = None):
        """POST /api/orders
        items=[{"goods_id":1,"quantity":2}] 直购 / from_cart=true 购物车结算。
        成功: data={order_id, order_no, total_amount, status="pending"}
        失败: 3001 购物车空 / 2001 商品不存在 / 2002 库存不足 / 1004 参数
        """
        body = {}
        if items is not None:
            body["items"] = items
        if from_cart is not None:
            body["from_cart"] = from_cart
        return self.client.post("/api/orders", json_body=body or None)

    def list_orders(self, status: str = None):
        """GET /api/orders?status=pending —— 按 id 倒序。"""
        params = {"status": status} if status else None
        return self.client.get("/api/orders", params=params)

    def get_order(self, order_id: int):
        """GET /api/orders/{id} —— 查别人的订单也返回 4001（不泄露存在性）。"""
        return self.client.get(f"/api/orders/{order_id}")

    def pay_order(self, order_id: int):
        """POST /api/orders/{id}/pay —— pending→paid；重复支付 4002。"""
        return self.client.post(f"/api/orders/{order_id}/pay")

    def cancel_order(self, order_id: int):
        """POST /api/orders/{id}/cancel —— pending→cancelled 并回补库存；非 pending 4002。"""
        return self.client.post(f"/api/orders/{order_id}/cancel")
