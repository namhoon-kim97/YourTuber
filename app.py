from flask import Flask, render_template, jsonify, request, redirect, url_for
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import jwt, datetime, hashlib

app = Flask(__name__)
SECRET_KEY = "namhoon"

client = MongoClient(
    "mongodb+srv://sparta:jungle@cluster0.wvcjdwu.mongodb.net/?retryWrites=true&w=majority"
)
db = client.yourtuber


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    id_receive = data["userId"]
    nickname_receive = data["nickname"]
    pw_receive = data["password"]  # 여기서 pw받을 때 https로 받아야 안전함.

    pw_hash = hashlib.sha256(pw_receive.encode("utf-8")).hexdigest()
    db.user.insert_one(
        {"id": id_receive, "pw": pw_hash, "nickname": nickname_receive, "liked": {}}
    )
    return jsonify({"result": "success"})


@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    id_receive = data["userId"]
    pw_receive = data["password"]  # 여기서 pw받을 때 https로 받아야 안전함.

    pw_hash = hashlib.sha256(pw_receive.encode("utf-8")).hexdigest()
    result = db.user.find_one({"id": id_receive, "pw": pw_hash})

    if result is not None:
        payload = {
            "id": id_receive,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=5),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify({"result": "success", "token": token})
    else:
        return jsonify(
            {"result": "fail", "msg": "아이디/비밀번호가 일치하지 않습니다."}
        )


@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@app.route("/")
def home():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user.find_one({"id": payload["id"]})
        return render_template("index.html", nickname=user_info["nick"])
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


@app.route("/memo", methods=["POST"])
def post_article():
    # 1. 클라이언트로부터 데이터를 받기
    url_receive = request.form["url_give"]  # 클라이언트로부터 url을 받는 부분
    comment_receive = request.form[
        "comment_give"
    ]  # 클라이언트로부터 comment를 받는 부분

    # 2. meta tag를 스크래핑하기
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36"
    }
    data = requests.get(url_receive, headers=headers)
    soup = BeautifulSoup(data.text, "html.parser")

    og_image = soup.select_one('meta[property="og:image"]')
    og_title = soup.select_one('meta[property="og:title"]')
    og_description = soup.select_one('meta[property="og:description"]')

    url_title = og_title["content"]
    url_description = og_description["content"]
    url_image = og_image["content"]

    article = {
        "url": url_receive,
        "title": url_title,
        "desc": url_description,
        "image": url_image,
        "comment": comment_receive,
    }

    # 3. mongoDB에 데이터를 넣기
    db.youtuber.insert_one(article)

    return jsonify({"result": "success"})


@app.route("/memo", methods=["GET"])
def read_articles():
    # 1. mongoDB에서 _id 값을 제외한 모든 데이터 조회해오기 (Read)
    result = list(db.youtuber.find({}, {"_id": 0}))
    # 2. articles라는 키 값으로 article 정보 보내주기
    return jsonify({"result": "success", "articles": result})


if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
