from flask import Flask, render_template, request, redirect, session
import re
import psycopg2
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.tag import pos_tag
from goose3 import Goose

app = Flask(__name__)
app.secret_key = 'hello'  # Secret key for session management

# Database configuration
DB_NAME = "news_bder"
DB_USER = "news_bder_user"
DB_PASSWORD = "7yx2KOUu38byViLlnWXBaUIqq95GBXRZ"
DB_HOST = "dpg-cnlk5g8l6cac73a2jeh0-a"

# Function to establish database connection
def connect_to_database():
    try:
        connection = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST)
        return connection
    except psycopg2.Error as e:
        print("Error connecting to database:", e)
        return None

# Function to create 'news_data' table if not exists
def create_table_if_not_exists():
    try:
        connection = connect_to_database()
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_data (
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
    except psycopg2.Error as e:
        print("Error creating PostgreSQL table:", e)

# Call function to create table
create_table_if_not_exists()

# Function to clean text and count words without punctuation
def clear(lst):
    lst1 = ['!', ',', '.', '?', '-', '"', ':', ';', '/', '_', '(', ')', '{', '}', '[', ']']
    count = 0
    for i in lst:
        if i not in lst1:
            count += 1
    return count

@app.route('/', methods=['GET', 'POST'])  
def portal():
    if request.method == 'POST':
        url = request.form.get('url')
        g = Goose()
        article = g.extract(url=url)
        cleantext = re.sub(r'<.*?>', ' ', article.cleaned_text)

        def count_words_without_punctuation(cleantext):
            words = word_tokenize(cleantext)
            return clear(words)
        
        # Analyze text
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

        # Save to PostgreSQL
        connection = connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO news_data (input_text, url, num_sentences, num_words, num_stop_words, upos_tag_counts) VALUES (%s,%s,%s,%s,%s,%s)",
                    (cleantext, url, num_sentences, num_words, num_stop_words, upos_tag_counts))
                connection.commit()
                connection.close()
            except psycopg2.Error as e:
                print("Error inserting data into PostgreSQL:", e)
        else:
            print("Database connection not established.")

        return render_template('index.html', cleantext=cleantext, num_sentences=num_sentences, 
                               num_words=num_words, num_stop_words=num_stop_words, 
                               upos_tag_counts=upos_tag_counts)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
