from typing import Any

import httpx

from atguigu.common.settings import get_settings


class EcommerceClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.setting = get_settings()

    async def get_json(self,
                       resource_path: str,
                       query_params: dict[str, Any] | None = None
                       ) -> dict[str, Any]:
        # 1.构建请求地址接口
        request_url = f"{self.setting.ecommerce_base_url}{resource_path}"

        # 2.构建请求头
        request_headers = {
            "Authorization": f"Bearer {self.access_token}",
        }
        # 3.构建客户端
        async with httpx.AsyncClient(
                timeout=self.setting.ecommerce_timeout_seconds,
                trust_env=False
        ) as http_client:
            responses = await http_client.get(
                request_url,
                headers=request_headers,
                params=query_params
            )
            responses.raise_for_status()

            return responses.json()
