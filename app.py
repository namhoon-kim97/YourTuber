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
            "exp": datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(seconds=50),
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
        return render_template("index.html", nickname=user_info["nickname"])
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


@app.route("/post", methods=["POST"])
def post_card():
    # 1. user로 부터 데이터를 받기
    user_nickname = request.form["user_nickname"]
    card_content = request.form["card_content"]
    youtube_links = request.form["youtube_links"]
    youtuber_comments = request.form["youtuber_comments"]

    channels_info = []
    # 2. meta tag를 스크래핑하기
    for url_link, youtuber_comment in zip(youtube_links, youtuber_comments):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36"
        }
        data = requests.get(url_link, headers=headers)
        soup = BeautifulSoup(data.text, "html.parser")

        og_image = soup.select_one('meta[property="og:image"]')
        og_title = soup.select_one('meta[property="og:title"]')

        channels_info.append(
            {
                "url_link": url_link,
                "channel_image": og_image["content"],
                "channel_title": og_title["content"],
                "youtuber_comment": youtuber_comment,
            }
        )

    card = {
        "channels_info": channels_info,
        "user_nickname": user_nickname,
        "card_content": card_content,
        "like_count": 0,
    }

    # 3. mongoDB에 데이터를 넣기
    db.card.insert_one(card)

    return jsonify({"result": "success"})


if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
