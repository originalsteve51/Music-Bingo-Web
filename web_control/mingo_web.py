# on branch web-view-2

from flask import Flask, render_template, render_template_string, request, jsonify, session, redirect, url_for, make_response
import os, json
import time



# Create the Flask application
app = Flask(__name__)

# NOTE: The secret key is used to cryptographically-sign the cookies used for storing
#       the session data.
app.secret_key = 'MINGO_SECRET_KEY'

stop_requests = []

run_on_host = os.environ.get('RUN_ON_HOST') 
using_port = os.environ.get('USING_PORT')
update_interval = os.environ.get('MINGO_UPDATE_INTERVAL')
debug_mode = os.environ.get('MINGO_DEBUG_MODE')

print(f"run_on_host: {run_on_host}, Using Port: {using_port}, Update interval: {update_interval}, Debug: {debug_mode}")

songs = []
cards = {}
votes_required = None
number_of_players = 0
refresh_screen = []

# List of card numbers that have claimed a win. Kept as a list
# to provide for the case where more than one card is claimed to be a winner.
win_claims = []
playlist_name = None

active_player_ids = set()
inactive_player_ids = set([0,1,2,3,4,5,6,7,8,9])

# The tapped/untapped state of a player's game is kept in JavaScript persistent storage
# on the browser. This allows state to persist between screen refreshes in the case where
# a twitchy user refreshes the screen during game play. Without saved state, the state 
# of the game is lost when the page refresh occurs. 
# In JavaScript the localStorage feature is uses to store the state.
#
# reset_player_storage is an array of boolean that tells for each player/card number whether
# a GET request needs to reset the browser-side state for the user. This state is initially all
# untapped except for the center square. When a GET is issued for the card page, the flag 
# determines whether to use saved state or to wipe the board (and the state) to its starting
# untapped status.
reset_player_storage = [False for _ in range(len(inactive_player_ids))]
invalid_login = [True for _ in range(len(inactive_player_ids))]


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin']='*'
    response.headers['Access-Control-Allow-Methods']='GET,POST,OPTIONS'
    response.headers['Access-Control-Allow-Headers']='Content-Type'
    return response

@app.route('/<int:player_id>', methods=['GET'])
def assign_player_id(player_id):
    global active_player_ids
    global inactive_player_ids

    # session.permanent = True

    if not player_id in active_player_ids and player_id in inactive_player_ids:
        print('Assigning player id', player_id)
        active_player_ids.add(player_id)
        inactive_player_ids.remove(player_id)

        return activate_player(player_id)

        """
        session['player_id'] = player_id

        if len(cards) != 0:
            return redirect(url_for('card'))
        else:
            return render_template('game_not_ready.html', 
                                    player_id=player_id, 
                                    run_on_host=run_on_host, 
                                    using_port=using_port)
        """

    else:
        return render_template('invalid_id.html', 
                              player_id=player_id,
                              run_on_host=run_on_host, 
                              using_port=using_port)

@app.route('/rel', methods=['GET'])
def release_player_id():
    global active_player_ids
    global inactive_player_ids
    global reset_player_storage
    
    release_id = 'Unknown Id'
    print ('Active player_ids: ', active_player_ids)
    if 'player_id' in session:
        release_id = session['player_id']
        if release_id in active_player_ids:
            active_player_ids.remove(release_id)
            inactive_player_ids.add(release_id)
            
        session.pop('player_id', None)

        if 'player_id' in session:
            print('I thought player_id was removed from session, but NO!')
        else:
            print('Player id is not in session anymore')

        reset_player_storage[release_id] = True

        print(f'Released {release_id} for reuse and removed player_id from session')

    return render_template('released.html',
                            player_id=release_id,
                            run_on_host=run_on_host, 
                            using_port=using_port)
    


"""
@app.route('/', methods=['GET'])
def index():
    global cards
    global player_ids
    
    print ('Player_ids: ', player_ids)
    if 'player_id' in session:
        # Already have a player id, just make sure it is not available
        # to anyone else.
        player_id = session['player_id']
        print(f'player id {player_id} is in session ')
        if player_id in player_ids:
            player_ids.remove(player_id)
            print(f'removed {player_id} from available ids')
    else:
        # Get an available player id and assign it, popping it
        # to remove it from available ids
        template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>No More Mingo Cards</title>
    </head>
    <body>
        <h1>Sorry! All Music Bingo cards have been assigned.</h1>
    </body>
    </html>
    '''
        try:
            player_id = player_ids.pop()
            session['player_id'] = player_id
            print(f'obtained {player_id} from {player_ids} and assigned it')
        except KeyError:
            return render_template_string(template)

    if len(cards) != 0:
        return redirect(url_for('card'))
    else:
        return render_template('game_not_ready.html', 
                                player_id=player_id, 
                                run_on_host=run_on_host, 
                                using_port=using_port)
"""
  
@app.route('/card', methods=['GET'])
def card():
    global cards
    global playlist_name
    global invalid_login

    if len(cards) == 0:
        return redirect(url_for('not_ready'))

    try:
        card_number = session['player_id']
        if invalid_login[card_number]:
            session.pop('player_id', None)
            return key_error(card_number)

        reset_storage = reset_player_storage[card_number]
        reset_player_storage[card_number] = False

        try:
            titles = cards[str(card_number)]
        except KeyError:
            return key_error(999) 

        print('========> ', playlist_name)
        return render_template('card_view.html', 
                                card_number=card_number, 
                                titles=titles,
                                stop_requests=stop_requests, 
                                run_on_host=run_on_host, 
                                using_port=using_port,
                                update_interval=update_interval,
                                playlist_name=playlist_name,
                                reset_storage=reset_storage)
    except KeyError:
        return key_error(999)

@app.route('/not_ready', methods=['GET'])
def not_ready():
    player_id = session['player_id']
    return render_template('game_not_ready.html', 
                            player_id=player_id,
                            run_on_host=run_on_host, 
                            using_port=using_port)


def key_error(player_id):
    return render_template('invalid_id.html', 
                            player_id=player_id,
                            run_on_host=run_on_host, 
                            using_port=using_port)


@app.route('/claimWinner', methods=['POST'])
def claimWinner():
    global win_claims
    data = request.get_json()
    card_claiming_win = data["card_claiming_win"]
    print("winner claim received from card number: ", card_claiming_win)
    # Add card claiming win to win_claims, the list of cards that need to be checked 
    # by the game engine.
    # The game engine polls this list to see if a check should be made
    # Duplicates are not allowed...
    if card_claiming_win not in win_claims:
        win_claims.append(card_claiming_win)
        print('win_claims: ', win_claims)
    return jsonify({"status": "success", "received": card_claiming_win})

@app.route('/win_claims', methods=['GET', 'POST'])
def get_win_claims():
    global win_claims
    ret_json = jsonify({'win_claims': win_claims})
    # time.sleep(1)
    print ("Returning win_claims: ", win_claims)

    # Clear the claims list
    win_claims.clear()
    return ret_json

@app.route('/game_misc_data', methods=['POST'])
def game_misc_data():
    global playlist_name
    global number_of_players
    global refresh_screen
    json_string = request.get_json()
    data = json.loads(json_string)
    playlist_name = data["playlist_name"]
    print(f'Loaded cards for {playlist_name}')
    number_of_players = int(data["number_of_players"])
    refresh_flag = data["refresh_flag"]
    refresh_screen.clear()
    for _ in range(number_of_players):
        refresh_screen.append(refresh_flag)

    print(f'Number of players is {str(number_of_players)}')

    # Respond to the client
    return jsonify({"status": "success", "received": data})

@app.route('/clear_refresh', methods=['POST'])
def clear_refresh():
    global refresh_screen
    json_str = request.get_json()
    print('==================================>>>> ', json_str)
    # data = json.loads(json_str)
    print('==================================>>>> ', json_str["player_nbr"])
    # print("clear_refresh: ", json_string)
    player_nbr = json_str["player_nbr"]
    refresh_screen[int(player_nbr)] = False
    # print(f'Cleared refresh flag for: ', player_nbr)
    return jsonify({"status": "success", "received": "OK"})


@app.route('/admin', methods=['GET'])
def admin():
    global active_player_ids
    global inactive_player_ids
    global invalid_login
    
    response = make_response( render_template('admin.html',
                            active_player_ids=active_player_ids,
                            inactive_player_ids=inactive_player_ids,
                            invalid_login=invalid_login,
                            run_on_host=run_on_host, 
                            using_port=using_port))

    # Set Cache-Control headers
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/signOffAll', methods=['GET','POST'])
def sign_off_all():
    global active_player_ids
    global inactive_player_ids
    global reset_player_storage
    global invalid_login

    reset_player_storage = [True for _ in range(len(reset_player_storage))]
    invalid_login = [True for _ in range(len(invalid_login))]
    

    for _ in range (len(active_player_ids)):
        player_id = active_player_ids.pop()
        inactive_player_ids.add(player_id)


    return redirect(url_for('admin'))



# !!! TODO If the session already has 'player_id' in it then do not
#     permit rejoin with another id. First id must be released! Then join again.
@app.route('/join', methods=['GET'])
def join_game():
    global active_player_ids
    global inactive_player_ids
    global invalid_login

    if 'player_id' in session:
        # This user already has a player id. Handle an attempt to join again
        # by starting the player over with a new id. Return the current id to
        # the pool of available ids.
        player_id = session['player_id']

        new_player_id = min(inactive_player_ids)
        inactive_player_ids.remove(new_player_id)
        inactive_player_ids.add(player_id)
        if player_id in active_player_ids:
            active_player_ids.remove(player_id)
            inactive_player_ids.add(player_id)
    
        return activate_player(new_player_id)
        """
        return render_template('already_have_id.html', 
                            player_id=player_id, 
                            run_on_host=run_on_host, 
                            using_port=using_port)
        """
    
    elif len(inactive_player_ids) > 0:
        # player_id = inactive_player_ids.pop()
        player_id = min(inactive_player_ids)
        inactive_player_ids.remove(player_id)
        return activate_player(player_id)
    



def activate_player(player_id):        
    global active_player_ids
    global inactive_player_ids
    global invalid_login
    global reset_player_storage

    session['player_id'] = player_id
    reset_player_storage[player_id] = True
    invalid_login[player_id] = False

    active_player_ids.add(player_id)
    if player_id in inactive_player_ids:
        inactive_player_ids.remove(player_id)


    if len(cards) != 0:
        return redirect(url_for('card'))
    else:
        return render_template('game_not_ready.html', 
                                player_id=player_id, 
                                run_on_host=run_on_host, 
                                using_port=using_port)




@app.route('/card_load', methods=['POST'])
def card_load():
    global cards
    global reset_player_storage

    reset_player_storage = [True for _ in range(len(reset_player_storage))]

    # Get the JSON data from the request
    json_string = request.get_json()
    # print("Received data:", data)
    # print (json_to_songs(data))
    # Parse the JSON string into a Python dictionary
    data = json.loads(json_string)

    # Get the card number
    card_nbr = data["card_nbr"]
    print("Loading card number", card_nbr)

    # Extract the list of song titles
    # Start with an empty list
    songs.append([])
    songs_temp = [song["title"] for song in data["songs"]]
    for song in songs_temp:
        print('adding ', song, ' ', card_nbr)
        songs[len(songs)-1].append(song)
    
    cards.update({str(card_nbr): songs[len(songs)-1]})

    print('\n\n\n========= Loaded: ',str(card_nbr),'\n',cards[str(card_nbr)])

    if card_nbr == 1:
        card_debug()

    # Respond to the client
    return jsonify({"status": "success", "received": data})

@app.route('/set_votes_required', methods=['POST'])
def set_votes_required():
    global votes_required
    if request.method == 'POST':
        json_string = request.get_json()
        data = json.loads(json_string)
        print("Received votes_required data:", data)
        votes_required = data["votes_required"]
        return jsonify({'votes_required': 'OK'})    



@app.route('/clear', methods=['GET'])
def clear_stop_requests():
    if request.method == 'GET':
        stop_requests.clear()
        return render_template_string("""
            <h1>Stop requests have been cleared</h1>
        """)

@app.route('/check', methods=['GET'])
def check_status():
    if request.method == 'GET':
        player_id = session['player_id']
        print('player id: ', player_id)
        return render_template_string("""
            <h1>Player id: {{player_id}}</h1>
        """, player_id=player_id)        

@app.route('/requeststop', methods=['POST'])
def add_stop_request():
    if request.method == 'POST':
        # Record the player's request to stop playing
        if (session['player_id'] not in stop_requests):
            stop_requests.append(session['player_id'])
        else:
            print('not recording a repeated request')
        return jsonify({'stoprequests': stop_requests})

@app.route('/stopdata', methods=['GET', 'POST'])
def get_stop_data():
    return jsonify({'stoprequests': stop_requests, 
                    'votes_required': votes_required, 
                    'refresh_screen': refresh_screen})

@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()
    if 'text' in data:
        text_value = data['text']
        return jsonify({'message': f'Text received: {text_value}'})
    else:
        return jsonify({'error': 'no text received'})

@app.route('/get_stop_count', methods=['GET'])
def get_stop_count():
    return str(len(stop_requests))

@app.route('/get_player_count', methods=['GET'])
def get_player_count():
    return str(len(active_player_ids))


@app.route('/debug', methods=['GET'])
def card_debug():
    return render_template('timeout.html')

"""
def json_to_songs(json_string):
    # Parse the JSON string into a Python dictionary
    data = json.loads(json_string)

    # Get the card number
    card_nbr = data["card_nbr"]
    print("Loading card number", card_nbr)

    # Extract the list of song titles
    songs_temp = [song["title"] for song in data["songs"]]
    songs.clear()
    for song in songs_temp:
        songs.append(song)
    
    cards[str(card_nbr)] = songs;
    print('\n\n\n========= Loaded: ',str(card_nbr),'\n',cards[str(card_nbr)])
    return songs
"""

if __name__ == '__main__':
    app.run(debug=True, threaded=True, port=using_port, host='0.0.0.0')
#    app.run(debug=False, threaded=True, port=8080, host='127.0.0.1')
