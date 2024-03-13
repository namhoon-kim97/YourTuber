from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
    make_response,
)
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import jwt
import datetime
import hashlib
import json

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

    if search_nickname_in_db(nickname_receive) or search_userId_in_db(id_receive):
        return (
            jsonify(
                {
                    "result": "error",
                    "message": "닉네임 또는 이메일이 이미 사용 중입니다.",
                }
            ),
            400,
        )

    pw_hash = hashlib.sha256(pw_receive.encode("utf-8")).hexdigest()
    db.user.insert_one(
        {"id": id_receive, "pw": pw_hash, "nickname": nickname_receive, "liked": []}
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
            + datetime.timedelta(seconds=5000),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify({"result": "success", "token": token})
    else:
        return jsonify(
            {"result": "fail", "msg": "아이디/비밀번호가 올바르지 않습니다."}
        )


@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@app.route("/logout")
def logout():
    # 로그아웃 처리를 위해 쿠키 삭제 등의 로직을 추가
    resp = make_response(redirect(url_for("home")))
    resp.delete_cookie("mytoken")
    return resp


@app.route("/")
def home():
    token_receive = request.cookies.get("mytoken")
    # channels_info : list(dict)
    # cards : list(dict(channels_info, str, str, int))
    unsorted_cards = list(db.card.find({}, {"_id": False}))
    cards = sorted(unsorted_cards, reverse=True, key=lambda x: x["like_count"])

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        # cards = db.card.find({})
        unsorted_cards = list(db.card.find({}, {'_id': False}))
        cards = sorted(unsorted_cards, reverse=True,
                       key=lambda x: x['like_count'])

        user_info = db.user.find_one({"id": payload["id"]})
        my_like = user_info.get("liked", [])
        nickname = user_info['nickname']
    except:
        nickname = None
        my_like = []
        user_info = None

    return render_template("index.html", cards=cards, my_like=my_like, user_info=user_info, nickname=nickname)


@app.route("/post", methods=["POST"])
def post_card():
    # 1. user로 부터 데이터를 받기
    user_nickname = request.form["user_nickname"]
    card_content = request.form["card_content"]
    youtube_links = request.form.getlist("youtube_links[]")
    youtuber_comments = request.form.getlist("youtuber_comments[]")
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
        if not og_image:
            return jsonify({"result": "fail", "msg": "유효하지 않은 Youtube channel 입니다."})

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
    return jsonify({"result": "success", "msg": "카드 작성 완료!"})

# user_nick 변수 맞게 바꿔야


@app.route('/card/load', methods=['POST'])
def load_cards():
    nickname = request.form['nickname']
    corrCard = db.card.find_one({"nickname": nickname})
    return jsonify({'result': 'success', 'corrCard': corrCard})


@app.route('/card/update', methods=['POST'])
def update_cards(nickname):
    title_receive = request.form['title_give']
    content_receive = request.form['content_give']
    db.card.update_one({"nickname": nickname}, {
        '$set': {"title": title_receive, "content": content_receive}})
    return jsonify({'result': 'success', 'msg': '수정 완료'})


@app.route('/delete_card/<nickname>', methods=['POST'])
def delete_card(nickname):
    db.card.delete_one({"nickname": nickname})
    return redirect(url_for('home'))


@app.route('/card/like', methods=['POST'])
def like_cards():
    nickname = request.form['nickname']
    user_nickname = request.form['user_nickname']
    print(nickname, user_nickname)
    db.user.update_one(
        {"nickname": nickname},
        {"$push": {"liked": user_nickname}},
        upsert=True)
    # 카드의 count +=1
    db.card.update_one({"nickname": nickname},
                       {"$inc": {"like_count": +1}})
    return jsonify({'result': 'success', 'msg': '좋아요'})


@app.route('/card/unlike', methods=['POST'])
def unlike_cards():
    nickname = request.form['nickname']
    user_nickname = request.form['user_nickname']
    db.card.update_one({"nickname": user_nickname},
                       {"$inc": {"like_count": -1}})
    db.user.update_one(
        {"nickname": nickname},
        {"$pull": {"liked": user_nickname}})
    return jsonify({'result': 'success', 'msg': '이거별로네'})


def search_nickname_in_db(nickname):
    print("check nickname db")
    user = db.user.find_one({"nickname": nickname})
    return user is not None


def search_userId_in_db(userId):
    print("check userId db")
    user = db.user.find_one({"id": userId})
    return user is not None


@app.route("/check-nickname", methods=["POST"])
def check_username():
    data = request.get_json()
    nickname = data.get("nickname")

    user_exists = search_nickname_in_db(nickname)
    if user_exists:
        return jsonify({"exists": True, "message": "사용자 이름이 이미 사용 중입니다."})
    else:
        return jsonify({"exists": False, "message": "사용 가능한 닉네임입니다."})


@app.route("/check-userId", methods=["POST"])
def check_email():
    data = request.get_json()
    userId = data.get("userId")

    user_exists = search_userId_in_db(userId)
    if user_exists:
        return jsonify(
            {"exists": True, "message": "사용자 이메일이 이미 사용 중입니다."}
        )
    else:
        return jsonify({"exists": False, "message": "사용 가능한 이메일입니다."})


if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
