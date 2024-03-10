from flask import Flask, render_template, request, url_for, redirect, session
import requests
import re
import psycopg2
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.tag import pos_tag
import nltk
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger')
from authlib.integrations.flask_client import OAuth
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from goose3 import Goose



app = Flask(__name__)

app.secret_key = 'hello'  #google

oauth = OAuth(app)
app.config['SECRET_KEY'] = "THIS SHOULD BE SECRET"
app.config['GITHUB_CLIENT_ID'] = "4896bd6520656fa38424"
app.config['GITHUB_CLIENT_SECRET'] = "d97e99a8d420770058b84482e3957bfc8d035d68"
#google
# Path to the client secrets file   
client_secrets_file = 'client_secret_2_126959989022-htfd7knd8jbv2englh276fnkq75i2lgd.apps.googleusercontent.com.json'

scopes = ['https://www.googleapis.com/auth/userinfo.profile',
          'https://www.googleapis.com/auth/userinfo.email',
          'openid']
redirect_uri = 'http://127.0.0.1:5000/callback'
# Create the OAuth flow object
flow = Flow.from_client_secrets_file(client_secrets_file, scopes=scopes, redirect_uri=redirect_uri)

github = oauth.register(
    name='github',
    client_id=app.config["GITHUB_CLIENT_ID"],
    client_secret=app.config["GITHUB_CLIENT_SECRET"],
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

DB_NAME = "news_bder"
DB_USER = "news_bder_user"
DB_PASSWORD = "7yx2KOUu38byViLlnWXBaUIqq95GBXRZ"
DB_HOST = "dpg-cnlk5g8l6cac73a2jeh0-a"

VIEW_DATA_PASSWORD = "Hamma"

def connect_to_database():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST)


def create_table_if_not_exists():
    try:
        connection = connect_to_database()
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_form (
                username TEXT,
                input_text TEXT,
                url TEXT,
                num_sentences INTEGER,
                num_words INTEGER,
                num_stop_words INTEGER,
                upos_tag_counts INTEGER
            )
        """)
        connection.commit()
        connection.close()
    except (Exception, psycopg2.Error) as error:
        print("Error while creating PostgreSQL table:", error)

# Call this function to create the table if it doesn't exist
create_table_if_not_exists()

def clear(lst):
    lst1 = ['!', ',', '.', '?', '-', '"', ':', ';', '/', '_', '(', ')', '{', '}', '[', ']']
    count = 0
    for i in lst:
        if i not in lst1:
            count += 1
    return count

@app.route('/', methods=['GET','POST'])  
def portal():
    if request.method == 'POST':
        name= request.form['name']
        url = request.form['url']
        g = Goose()
        article = g.extract(url=url)
        news_title = article.title
        cleantext = re.sub(r'<.*?>', ' ', article.cleaned_text)

        def count_words_without_punctuation(cleantext):
            words = word_tokenize(cleantext)
            return clear(words)
        
        # Task 1: Analyze text
        sentences = sent_tokenize(cleantext)
        words = word_tokenize(cleantext)
        stop_words = set(stopwords.words('english'))

        # UPOS tags
        pos_tags = pos_tag(words)
        upos_tag_count = {}
        for tag in pos_tags:
            upos_tag_count[tag[1]] = upos_tag_count.get(tag[1], 0) + 1

        num_sentences = len(sentences)
        num_words = count_words_without_punctuation(cleantext)
        num_stop_words = len([word for word in words if word.lower() in stop_words])
        upos_tag_counts = len(upos_tag_count)


        # Task 2: Save to PostgreSQL
        connection = connect_to_database()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO news_form (username,input_text, url, num_sentences, num_words, num_stop_words, upos_tag_counts) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (name,cleantext, url, num_sentences, num_words, num_stop_words, upos_tag_counts))

        connection.commit()
        connection.close()
        return render_template('index.html', news_title=news_title, cleantext=cleantext, num_sentences=num_sentences, 
                               num_words=num_words, num_stop_words=num_stop_words, 
                               upos_tag_counts=upos_tag_counts)


    return render_template('index.html')
    


@app.route('/view_data',methods=['POST','GET'])
def view_data():
    if request.method == 'POST':
        if request.form['password'] != VIEW_DATA_PASSWORD:
            return 'Incorrect Password'
        else:
            connection = connect_to_database()
            cursor = connection.cursor()

            cursor.execute("SELECT * FROM news_form")
            data = cursor.fetchall()

            connection.close()
            return render_template('login_page.html', data=data)
    return render_template('index.html')

github_admin_usernames = ["mayank-singh-tomar", "atmabodha"]
@app.route('/login/github')
def github_login():
    github = oauth.create_client('github')
    redirect_uri = url_for('github_authorize', _external=True)
    return github.authorize_redirect(redirect_uri)

@app.route('/login/github/authorize')
def github_authorize():
    try:
        github = oauth.create_client('github')
        token = github.authorize_access_token()
        session['github_token'] = token
        resp = github.get('user').json()
        print(f"\n{resp}\n")
        logged_in_username = resp.get('login')
        if logged_in_username in github_admin_usernames:
            connection = connect_to_database()
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM news_form")
            data = cursor.fetchall()
            connection.close()
            return render_template("login_page.html", data=data)
        else:
            return redirect(url_for('portal'))
    except:
        return redirect(url_for('portal'))

@app.route('/logout/github')
def github_logout():
    session.clear()
    print("logout")
    return redirect(url_for('portal'))


@app.route('/index')
def index():
    if 'google_token' in session:
        # User is already authenticated, redirect to a protected route
        return redirect(url_for('protected'))
    else:
        # User is not authenticated, render the ggl.html template
        authorization_url, _ = flow.authorization_url(prompt='consent')
        return redirect(authorization_url)

@app.route('/callback')
def callback():
    # Handle the callback from the Google OAuth flow
    flow.fetch_token(code=request.args.get('code'))
    session['google_token'] = flow.credentials.token

    # Redirect to the protected route or another page
    return redirect(url_for('index'))

# Protected route accessible only to authenticated users
# Define the allowed email addresses
allowed_emails = ['su-23020@sitare.org','kushal@sitare.org']

@app.route('/protected')
def protected():
    if 'google_token' in session:
        # User is authenticated
         # Get the user's email from the Google API
        userinfo = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers={'Authorization': f'Bearer {session["google_token"]}'})
        email = userinfo.json().get('email')

        if email in allowed_emails:
            connection = connect_to_database()
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM news_form")
            data = cursor.fetchall()
            connection.close()

            return render_template("login_page.html", data=data)
        else:
            email=None
              # User is not authorize
            return redirect(url_for('portal'))

    else:
        # User is not authenticated, redirect to the portal page
        return redirect(url_for('portal'))
    
@app.route('/logout')
def logout_google():
    session.clear()
    return redirect(url_for('portal'))

if __name__ == '__main__':
    app.run(debug=True)
