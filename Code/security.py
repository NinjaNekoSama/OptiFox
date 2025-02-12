import time
import json
import jwt
from werkzeug.exceptions import Unauthorized
from tinydb import TinyDB
from utils import logger

JWT_ISSUER = "com.optifox.connexion"
JWT_SECRET = "OPTIFOX"
JWT_LIFETIME_SECONDS = 600
JWT_ALGORITHM = "HS256"

db = TinyDB("db.json")
my_db = db.all()
true_user = my_db[0].get("user_id")
secret_password = my_db[0].get("secret_password")


def generate_token(user_id, password):
    logger.info("Generating token attempted!")
    if (user_id == true_user) and (password == secret_password):
        timestamp = _current_timestamp()
        payload = {
            "iss": JWT_ISSUER,
            "iat": int(timestamp),
            "exp": int(timestamp + JWT_LIFETIME_SECONDS),
            "sub": str(user_id),
        }

        logger.info("Token generation for authentication succesful!")
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    response = {"message": "The user id or password given is not correct. Try again loser <3."}
    json_response = json.dumps(response)
    return json_response, 401


def decode_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError as e:
        raise Unauthorized from e


def _current_timestamp() -> int:
    return int(time.time())


generate_token("fddf", "Fdfdf")
