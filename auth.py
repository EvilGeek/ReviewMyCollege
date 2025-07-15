from flask import Blueprint, redirect, request
import requests, os, jwt
from urllib.parse import urlencode

linkedin_blueprint = Blueprint("linkedin", __name__)

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")

@linkedin_blueprint.route("/linkedin")
def start_linkedin_login():
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid profile email"
    }
    url = "https://www.linkedin.com/oauth/v2/authorization"
    return redirect(f"{url}?{urlencode(params)}")

def get_tokens(code):
    res = requests.post("https://www.linkedin.com/oauth/v2/accessToken", data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    return res.json()

def fetch_linkedin_data(code):
    tokens = get_tokens(code)
    access_token = tokens["access_token"]
    id_token = tokens["id_token"]
    decoded = jwt.decode(id_token, options={"verify_signature": False})
    userinfo = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()
    #print(userinfo)
    linkedin_id = userinfo.get("sub")
    name = userinfo.get("name")
    email = userinfo.get("email")
    photo = userinfo.get("picture", "")

    return {"id": linkedin_id, "name": name, "photo": photo}, email, []


