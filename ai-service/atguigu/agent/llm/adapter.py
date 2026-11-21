import httpx2
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI
from typesafe_sdk import AsyncTypeSafeClient

from atguigu.common.settings import get_settings


def get_llm_client():
    setting = get_settings()
    enable_thinking = 'enabled' if setting.llm_thinking_mode == "True" else "disabled"

    # llm基础参数
    model_kwargs = {
        "model": setting.llm_model,
        "api_key": setting.llm_api_key,
        "base_url": setting.llm_base_url,
        "timeout": setting.llm_timeout_seconds
    }

    if setting.llm_provider == "deepseek":
        return ChatDeepSeek(
            **model_kwargs,
            extra_body={
                "thinking": {"type": enable_thinking}
            }
        )

    return ChatOpenAI(
        **model_kwargs,
        use_responses_api=False
    )


def get_jev_client() -> AsyncTypeSafeClient:
    """获取TypeSafe JEV模型客户端实例"""
    setting = get_settings()

    # # 走允许地区的稳定代理可显著减少跨境断连(ConnectError)；未配置则沿用 trust_env(HTTPS_PROXY)
    # proxy = getattr(setting, "typesafe_proxy", "") or None
    # http_client = httpx2.AsyncClient(
    #     proxy=proxy,
    #     timeout=httpx2.Timeout(30.0, connect=10.0),
    # ) if proxy else None

    return AsyncTypeSafeClient(
        api_key=setting.typesafe_api_key,
        base_url=setting.typesafe_base_url,
        model=setting.typesafe_model
    )

    # return AsyncTypeSafeClient(
    #     api_key=setting.typesafe_api_key,
    #     base_url=setting.typesafe_base_url,
    #     model=setting.typesafe_model,
    #     http_client=http_client,
    # )
