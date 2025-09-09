import os
from flask import Flask, redirect, request, session, url_for
from google_auth_oauthlib.flow import Flow
from database import get_db_connection

app = Flask(__name__)
# In production, use a more secure secret key and manage it properly
app.secret_key = 'super-secret-key-for-flask-session'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # For local development only

CLIENT_SECRETS_FILE = 'client_secret.json'
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/userinfo.email' 
]

# --- MODIFIED SECTION ---
@app.route('/')
def index():
    """
    Main page that now lists connected accounts and provides a disconnect option.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_email FROM connected_accounts ORDER BY user_email;")
    accounts = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    # Build the HTML for the page
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Email Support Agent</title>
        <style>
            body { font-family: sans-serif; margin: 2em; }
            h1, h2 { color: #333; }
            .container { max-width: 800px; margin: auto; }
            .account-list { list-style: none; padding: 0; }
            .account-item { display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid #ccc; }
            .connect-button { background-color: #4285F4; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px; border: none; font-size: 16px; cursor: pointer; }
            .disconnect-button { background-color: #db4437; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px; border: none; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Email Support Agent Management</h1>
            <hr>
            <h2>Connected Accounts</h2>
    """

    if not accounts:
        html += "<p>No accounts have been connected yet.</p>"
    else:
        html += '<ul class="account-list">'
        for account_email in accounts:
            html += f"""
            <li class="account-item">
                <span>{account_email}</span>
                <form action="/disconnect" method="post" style="margin: 0;">
                    <input type="hidden" name="email" value="{account_email}">
                    <button type="submit" class="disconnect-button">Disconnect</button>
                </form>
            </li>
            """
        html += '</ul>'

    html += """
            <hr style="margin-top: 2em;">
            <p>Connect a new Gmail account:</p>
            <a href="/connect-gmail"><button class="connect-button">Connect a Gmail Account</button></a>
        </div>
    </body>
    </html>
    """
    return html

# --- NEW SECTION ---
@app.route('/disconnect', methods=['POST'])
def disconnect():
    """
    Handles the disconnection of an account by deleting it from the database.
    """
    email_to_delete = request.form['email']
    if email_to_delete:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM connected_accounts WHERE user_email = %s;", (email_to_delete,))
        conn.commit()
        cur.close()
        conn.close()
        print(f"Successfully disconnected account: {email_to_delete}")
    return redirect(url_for('index'))


@app.route('/connect-gmail')
def connect_gmail():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    
    # Get user's email address
    # This requires an authorized session, so we create one from the flow
    user_info_service = flow.authorized_session()
    user_info = user_info_service.get('https://www.googleapis.com/oauth2/v2/userinfo').json()
    user_email = user_info['email']

    # Save credentials to the database
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Use UPSERT to handle both new and existing accounts (re-connecting updates tokens)
    cur.execute(
        """
        INSERT INTO connected_accounts (user_email, access_token, refresh_token, token_expiry)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_email) DO UPDATE SET
            access_token = EXCLUDED.access_token,
            refresh_token = EXCLUDED.refresh_token,
            token_expiry = EXCLUDED.token_expiry;
        """,
        (user_email, credentials.token, credentials.refresh_token, credentials.expiry)
    )
    
    conn.commit()
    cur.close()
    conn.close()

    # Instead of a plain message, redirect back to the main page to see the updated list
    return redirect(url_for('index'))


if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(port=5000, debug=True)