import time
import jwt, datetime, hashlib
import requests

from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
    make_response,
)

from bs4 import BeautifulSoup
from pymongo import MongoClient
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

app = Flask(__name__)
SECRET_KEY = "namhoon"

client = MongoClient(
    "mongodb+srv://sparta:jungle@cluster0.wvcjdwu.mongodb.net/?retryWrites=true&w=majority"
)
db = client.yourtuber

## scraping driver
chrome_options = Options()
chrome_options.add_experimental_option("detach", True)

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    id_receive = data["userId"]
    nickname_receive = data["nickname"]
    pw_receive = data["password"]  # 여기서 pw받을 때 https로 받아야 안전함.
    
    if pw_receive.strip() != pw_receive or ' ' in pw_receive:
        return (jsonify(
            {
                "result": "error",
                'msg': '비밀번호에 공백을 포함할 수 없습니다.',
            },
            ),400,)

    if search_nickname_in_db(nickname_receive) or search_userId_in_db(id_receive):
        return (
            jsonify(
                {
                    "result": "error",
                    "msg": "닉네임 또는 이메일이 이미 사용 중입니다.",
                }
            ),
            400,
        )

    pw_hash = hashlib.sha256(pw_receive.encode("utf-8")).hexdigest()
    db.user.insert_one(
        {"id": id_receive, "pw": pw_hash, "nickname": nickname_receive, "liked": []}
    )
    return jsonify({"result": "success"})

def check_token_and_redirect():
    token_receive = request.cookies.get("mytoken")
    if token_receive:
        try:
            # 토큰이 유효하면 True 반환
            jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
            return True
        except:
            # 토큰이 유효하지 않으면 False 반환
            return False
    else:
        # 토큰이 없으면 False 반환
        return False
    
@app.route("/register", methods=["GET"])
def register():
    # 토큰 검사 후 리다이렉션 또는 회원가입 페이지 렌더링
    if check_token_and_redirect():
        return redirect(url_for("home"))
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET"])
def login():
    # 토큰 검사 후 리다이렉션 또는 로그인 페이지 렌더링
    if check_token_and_redirect():
        return redirect(url_for("home"))
    else:
        return render_template("login.html")

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

@app.route("/logout")
def logout():
    # 로그아웃 처리를 위해 쿠키 삭제 로직을 추가
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
        nickname = user_info['nickname']
        
        for card in cards:
            card_user = db.user.find_one({"nickname" : card["user_nickname"]})
            my_like = card_user.get("liked", [])
            card["is_liked_by_user"] = nickname in my_like
        
    except:
        nickname = None
        user_info = None

    return render_template("index.html", cards=cards, user_info=user_info, nickname=nickname)



@app.route("/get", methods=["POST"])
def get_card_detail():
    data = request.get_json()
    card_nickname = data["card_nickname"]
    
    card_detail = db.card.find_one({"user_nickname" : card_nickname}, {'_id':False})
    return jsonify({"result": "success", "msg": "카드정보 및 썸네일 전송 완료!", "card_detail": card_detail})


@app.route("/post", methods=["POST"])
def post_card():
    # 1. user로 부터 데이터를 받기
    user_nickname = request.form["user_nickname"]
    if db.card.find_one({'user_nickname' : user_nickname}):
        return jsonify({"result": "fail", "msg": "이미 저장된 카드가 있습니다!"})
     
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
        if not og_image: return jsonify({"result": "fail", "msg": "유효하지 않은 Youtube channel 입니다."})
        
        driver = webdriver.Chrome()
        driver.get(url_link)
        SCROLL_PAUSE_TIME = 3
        # Get scroll height
        last_height = driver.execute_script("return document.documentElement.scrollHeight")
        while True:
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, arguments[0]);", last_height)
            # Wait to load page
            time.sleep(SCROLL_PAUSE_TIME)
            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            
        thumbnails = []
        images = driver.find_elements(By.CSS_SELECTOR, 'img.yt-core-image')
        for image in images:
            if image.get_attribute('src'):
                thumbnails.append(image.get_attribute('src'))
            if len(thumbnails) >= 4: break
        driver.quit()
        channels_info.append(
            {   
                "thumbnails": thumbnails,
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
        "is_liked_by_user" : False
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

def check_liked(nickname, card_nickname):
    card_user = db.user.find_one({"nickname" : card_nickname})
    my_like = card_user.get("liked", [])
    if nickname in my_like:
        return True
    else:
        return False

@app.route('/card/like', methods=['POST'])
def like_cards():
    nickname = request.form['nickname']
    card_nickname = request.form['card_nickname']
        
    if check_token_and_redirect() and not check_liked(nickname, card_nickname):
        db.user.update_one(
            {"nickname": card_nickname},
            {"$push": {"liked": nickname}},
            upsert=True)
        # 카드의 count +=1
        db.card.update_one({"user_nickname": card_nickname},
                        {"$inc": {"like_count": +1}})
        return jsonify({'result': 'success', 'msg': '좋아요'})
    else:
        return jsonify({'result' : 'fail', 'msg' : "로그인을 해주세요"})


@app.route('/card/unlike', methods=['POST'])
def unlike_cards():
    nickname = request.form['nickname']
    card_nickname = request.form['card_nickname']
    if check_token_and_redirect() and check_liked(nickname, card_nickname):
        db.card.update_one({"user_nickname": card_nickname},
                        {"$inc": {"like_count": -1}})
        db.user.update_one(
            {"nickname": card_nickname},
            {"$pull": {"liked": nickname}})
        return jsonify({'result': 'success', 'msg': '이거별로네'})
    else:
        return jsonify({'result' : 'fail', 'msg' : "로그인을 해주세요"})


def search_nickname_in_db(nickname):
    user = db.user.find_one({"nickname": nickname})
    return user is not None


def search_userId_in_db(userId):
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
