import jwt
from fastapi import HTTPException, status
from atguigu.app.schemas import CurrentUser
from atguigu.common.settings import get_settings


def authorized_user(authorization: str | None, *role: str) -> CurrentUser:
    # 校验是否携带令牌 否则报错
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="认证失败")
    # 获取access_token
    access_token = authorization.split(" ", 1)[1]
    # jwt解码
    current_user = decode_access_token(access_token)
    # 判断角色是否符合
    if current_user.role not in role:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权访问")

    return current_user


def decode_access_token(access_token: str) -> CurrentUser:
    payload = jwt.decode(access_token, key=get_settings().jwt_secret, algorithms=[get_settings().jwt_algorithm])
    return CurrentUser.model_validate(payload)

def encode_access_token(user_id: str) -> str:
    current_user = CurrentUser(user_id=user_id)
    access_token = jwt.encode(current_user.model_dump(), key=get_settings().jwt_secret, algorithm=get_settings().jwt_algorithm)
    return access_token


if __name__ == '__main__':
    token='Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidXNlcl8wMDIiLCJyb2xlIjoidXNlciIsImV4cCI6MTc5NDEzODc2Nn0.cQTNp3hUr6cYnr-yCL3r2wMd_OVL-P8Sr90VieHYFk4'

    # print(authorized_user(token))
    token = token.split(" ", 1)[1]
    payload = jwt.decode(token, key=get_settings().jwt_secret, algorithms=[get_settings().jwt_algorithm])
    print(payload)