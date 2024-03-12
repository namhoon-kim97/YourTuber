from flask import Flask, render_template, jsonify, request
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient  # pymongo를 임포트 하기(패키지 인스톨 먼저 해야겠죠?)

app = Flask(__name__)

client = MongoClient('mongodb+srv://sparta:jungle@cluster0.wvcjdwu.mongodb.net/?retryWrites=true&w=majority')
db = client.yourtuber

# @app.route('/register', methods=['POST'])
# def register():

@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

@app.route('/')
def home():
    channels_info = [{'url_link':"https://www.youtube.com/@syukaworld", 'channel_image': "https://yt3.googleusercontent.com/8w2Z1ha57Ya10dqanJzwbYWYfVIOclw7ib3hXKJx9Xa3PlBGZDBRkyMtN83cHmnv78hlEo8tSg=s176-c-k-c0x00ffffff-no-rj-mo", 
                              'channel_title': "syukaworld", 'youtuber_comment': "economics communicator"},
                     {'url_link':"https://www.youtube.com/@ChimChakMan_Official", 'channel_image': "https://yt3.googleusercontent.com/C7bTHnoo1S_MRbJXn4VwncNpB87C2aioJC_sKvgM-CGw_xgdxwiz0EFEqzj0SRVz6An2h81T4Q=s176-c-k-c0x00ffffff-no-rj", 
                              'channel_title': "calm-down-man", 'youtuber_comment': "storyteller who makes audience recieve king"},
                     {'url_link':"https://www.youtube.com/@syukaworld", 'channel_image': "https://yt3.googleusercontent.com/8w2Z1ha57Ya10dqanJzwbYWYfVIOclw7ib3hXKJx9Xa3PlBGZDBRkyMtN83cHmnv78hlEo8tSg=s176-c-k-c0x00ffffff-no-rj-mo", 
                              'channel_title': "syukaworld", 'youtuber_comment': "economics communicator"},
                     {'url_link':"https://www.youtube.com/@ChimChakMan_Official", 'channel_image': "https://yt3.googleusercontent.com/C7bTHnoo1S_MRbJXn4VwncNpB87C2aioJC_sKvgM-CGw_xgdxwiz0EFEqzj0SRVz6An2h81T4Q=s176-c-k-c0x00ffffff-no-rj", 
                              'channel_title': "calm-down-man", 'youtuber_comment': "storyteller who makes audience recieve king"}]
    cards = [{'channels_info': channels_info , 
            'user_nickname': "jungler123",
            'card_content': "hi I'm eunsik ", 
            'like_count': 99}, 
             {'channels_info': channels_info , 
            'user_nickname': "jungler123",
            'card_content': "hi I'm eunsik ", 
            'like_count': 99}]
    return render_template('index.html', cards = cards)

@app.route('/get', methods=['GET'])
def read_articles():
    # 1. mongoDB에서 _id 값을 제외한 모든 데이터 조회해오기 (Read)
    result = list(db.youtuber.find({}, {'_id': 0}))
    # 2. articles라는 키 값으로 article 정보 보내주기
    return jsonify({'result': 'success', 'articles': result})

@app.route('/post', methods=['POST'])
def post_card():
    # 1. user로 부터 데이터를 받기
    user_nickname = request.form['user_nickname']
    card_content = request.form['card_content']
    youtube_links = request.form['youtube_links']  
    youtuber_comments = request.form['youtuber_comments']
    
    channels_info = []
    # 2. meta tag를 스크래핑하기
    for url_link, youtuber_comment in zip(youtube_links, youtuber_comments):    
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
        data = requests.get(url_link, headers=headers)
        soup = BeautifulSoup(data.text, 'html.parser')

        og_image = soup.select_one('meta[property="og:image"]')
        og_title = soup.select_one('meta[property="og:title"]')

        channels_info.append({'url_link':url_link, 'channel_image': og_image['content'], 
                              'channel_title' :og_title['content'], 'youtuber_comment': youtuber_comment})

    card = {'channels_info': channels_info, 
            'user_nickname': user_nickname,
            'card_content': card_content, 
            'like_count': 0}

    # 3. mongoDB에 데이터를 넣기
    db.card.insert_one(card)

    return jsonify({'result': 'success'})


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)