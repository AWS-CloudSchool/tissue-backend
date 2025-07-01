import boto3
import hmac
import hashlib
import base64
from botocore.exceptions import ClientError
from app.auth.core.config import settings

client = boto3.client("cognito-idp", region_name=settings.AWS_REGION)

def get_secret_hash(email: str) -> str:
    message = email + settings.COGNITO_CLIENT_ID
    dig = hmac.new(
        settings.COGNITO_CLIENT_SECRET.encode('utf-8'),
        msg=message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()

def sign_up_user(email: str, password: str):
    try:
        secret_hash = get_secret_hash(email)
        client.sign_up(
            ClientId=settings.COGNITO_CLIENT_ID,
            SecretHash=secret_hash,
            Username=email,  
            Password=password,
            UserAttributes=[
                {"Name": "email", "Value": email}
            ]
        )
        return {"message": "회원가입 성공. 이메일 인증 코드를 확인하세요."}
    except ClientError as e:
        raise e

def confirm_user_signup(email: str, code: str):
    try:
        secret_hash = get_secret_hash(email)
        client.confirm_sign_up(
            ClientId=settings.COGNITO_CLIENT_ID,
            SecretHash=secret_hash,
            Username=email,
            ConfirmationCode=code,
        )
        return {"message": "이메일 인증이 완료되었습니다."}
    except ClientError as e:
        raise e

def sign_in_user(email: str, password: str):
    secret_hash = get_secret_hash(email)
    try:
        response = client.initiate_auth(
            ClientId=settings.COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": email,
                "PASSWORD": password,
                "SECRET_HASH": secret_hash
            }
        )
        return {
            "access_token": response["AuthenticationResult"]["AccessToken"],
            "id_token": response["AuthenticationResult"]["IdToken"],
            "refresh_token": response["AuthenticationResult"]["RefreshToken"]
        }
    except ClientError as e:
        raise e

def refresh_user_token(refresh_token: str, email: str):
    secret_hash = get_secret_hash(email)
    try:
        response = client.initiate_auth(
            ClientId=settings.COGNITO_CLIENT_ID,
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={
                "REFRESH_TOKEN": refresh_token,
                "SECRET_HASH": secret_hash
            }
        )
        return {
            "access_token": response["AuthenticationResult"]["AccessToken"],
            "id_token": response["AuthenticationResult"]["IdToken"]
        }
    except ClientError as e:
        raise e

def get_user_info(access_token: str):
    try:
        response = client.get_user(AccessToken=access_token)
        user_attributes = {}
        for attr in response['UserAttributes']:
            user_attributes[attr['Name']] = attr['Value']
        return {
            "username": response['Username'],
            "attributes": user_attributes,
            "user_status": response.get('UserStatus')
        }
    except ClientError as e:
        raise e

def verify_access_token(access_token: str):
    try:
        response = client.get_user(AccessToken=access_token)
        return {"valid": True, "username": response['Username']}
    except ClientError as e:
        return {"valid": False, "error": e.response["Error"]["Message"]} 