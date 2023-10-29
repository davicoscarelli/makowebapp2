from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, abort
from . import db
import openai
from .models import History
from flask_cors import CORS
from flask_login import current_user, login_required
from datetime import datetime


main = Blueprint('main', __name__)
# app = Flask(__name__)

# Define OpenAI API key
OPENAI_API_KEY = "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"
openai.api_key = OPENAI_API_KEY

# Enable CORS
# CORS(app)


def recommend_song(entry):

    # Building the OpenAI API prompt based on the request body
    prompt = f"Empathize this diary entry with a song: {entry} . Return the song title and artist only."

    # Adding genre information to the prompt if available
    genre = request.json.get('genre')
    if genre:
        prompt += f" Pick from the genre = '{genre}'"
    print(prompt)

    # Calling the OpenAI API to generate a song recommendation based on the prompt
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        temperature=0.4,
        max_tokens=64,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stop=["."]
    )

    # Building a new OpenAI API prompt based on the song recommendation
    print('song recommendation', response)
    song_title = response.choices[0].text.strip()
    prompt2 = f"What is the lyric part that resonates with {entry} in {song_title}? Respond in the form: lyrics from song by artist"
    print('lyrics prompt', prompt2)

    # Calling the OpenAI API to generate a response based on the new prompt
    response2 = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt2,
        temperature=0.4,
        max_tokens=64,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    # Logging the response generated by the second OpenAI API call
    response_text = response2.choices[0].text.strip()
    print('lyrics response', response_text)

    return response_text


def create_prompt(entry):
    prompt1 = f"Here is a diary entry: {entry}. Imagine a response story to this diary entry that will give a new perspective to the writer, and describe it with three words which can be plugged into image generativeAI: object or location, color, and emotion. Only return the three words"

    # Use the GPT API to create a prompt designated for DALL-E
    response1 = openai.Completion.create(
        engine="text-davinci-003",  # use GPT 3 engine
        prompt=prompt1,
        max_tokens=100  # Adjust the desired length of the generated text
    )
    print('full_response', response1)
    res1 = response1.choices[0].text.strip()
    print('chatGPT prompt: ', res1, 'end')
    
    """
    prompt2 = f"Let's make a three-word prompt that will allow an image generation AI to Make a list of the most essential three words from this: {res1}"
    response2 = openai.Completion.create(
        engine="text-davinci-003",  # use GPT 3 engine
        prompt=prompt2,
        max_tokens=100  # Adjust the desired length of the generated text
    )
    res2 = response2.choices[0].text.strip()
    print('cleaned prompt: ', res2)
    """
    
    return res1


def generate_image_url(prompt):
    # Use the GPT API to create a prompt designated for DALL-E
    dalle_prompt = prompt + ' ,artistic'
    print('final dalle prompt:', dalle_prompt)
    response = openai.Image.create(
        prompt=(dalle_prompt),
        n=1,
        size="256x256",
    )

    img_url = response["data"][0]["url"]
    print(img_url)
    return img_url


def app_main(request):
    try:
        data = {}
        print('main')
        entry = request.json.get('mood')
        data['song'] = recommend_song(entry)
        data['img_url'] = generate_image_url(create_prompt(entry))
        return data

    except Exception as e:
        # Handling errors by sending an error response
        return jsonify({'error': str(e)}), 500


@main.route('/', methods=['POST', 'GET'])
@login_required
def home():
    if request.method == 'POST':
        data = app_main(request)
        
        # Store history
        new_history = History(
            date_time=datetime.utcnow(),
            diary_entry=request.json.get('mood'),
            generated_image=data['img_url'],
            song_snippet=data['song'],
            user_id=current_user.id  # assuming your User model has an id field
        )
        db.session.add(new_history)
        db.session.commit()
        
        return jsonify(data)
    return render_template('index.html', data=None)

'''
@main.route('/')
def index():
    return render_template('index.html')


@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', username=current_user.name)
'''


@main.route('/profile')
@login_required
def profile():
    user_history = History.query.filter_by(user_id=current_user.id).order_by(History.date_time.desc()).all()
    return render_template('profile.html', user_name=current_user.name, history=user_history)


@main.route('/delete_history/<int:history_id>')
@login_required
def delete_history(history_id):
    record = History.query.get_or_404(history_id)
    if record.user_id != current_user.id:
        abort(403)  # Forbidden access
    db.session.delete(record)
    db.session.commit()
    flash('Record deleted.', 'success')
    return redirect(url_for('main.profile'))
