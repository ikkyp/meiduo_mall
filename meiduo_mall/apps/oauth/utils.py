# 加密数据
def generic_openid(token):
    openid = token.encode()
    return openid


# 解密数据
def check_access_token(token):
    openid = token.decode()
    return openid
