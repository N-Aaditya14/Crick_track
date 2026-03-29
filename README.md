# 🏏 CricTrack — School Cricket Scoring App

A full cricket scoring and statistics tracker built with **Python Flask** + **SQLite**.

---

## Setup

### 1. Install Python dependencies
```bash
cd cricket_app
pip install -r requirements.txt
```

### 2. Run the app
```bash
python app.py
```

### 3. Open in browser
Visit: **http://127.0.0.1:5000**

---

## How to Use

### Adding Players
- Go to **Players** → **Add Player**
- Players are saved permanently — reuse them across all future matches

### Creating a Match
1. Click **New Match**
2. Enter team names and overs
3. Set toss winner and choice
4. Check players for Team A and Team B (same players can play for different teams in different games)
5. Click **Start Match**

### Live Scoring
1. Click **Score** on a live match
2. Use **Change Batsmen** to set who's at the crease (pick 2)
3. Use **Change Bowler** to set the current bowler
4. Click runs (0,1,2,3,4,6), add extras if needed, mark wickets
5. Click **Record Ball →**
6. The scoreboard updates in real time

### Player Stats
- **Players page** shows career stats across all matches
- Click any player for their full profile (batting, bowling, fielding, recent innings)

---

## Project Structure

```
cricket_app/
├── app.py              # Flask app, database models, all routes
├── requirements.txt    # Dependencies
├── cricket.db          # SQLite database (auto-created on first run)
└── templates/
    ├── base.html       # Shared nav + CSS design
    ├── index.html      # Match list
    ├── players.html    # Player roster
    ├── player_detail.html  # Individual player stats
    ├── new_match.html  # Match creation form
    ├── score.html      # Live scoring interface
    └── match_detail.html   # Final scorecard
```

---

## Learning Notes (for you!)

### What's Flask?
Flask is a "micro web framework" — it maps URLs to Python functions.
```python
@app.route('/players')      # When someone visits /players...
def players():              # ...run this Python function
    return render_template('players.html')  # ...and send back this HTML
```

### What's SQLAlchemy?
It's an ORM — lets you work with your database using Python objects instead of raw SQL.
```python
player = Player(name="Virat")    # Create a record
db.session.add(player)           # Stage it
db.session.commit()              # Save to database
Player.query.all()               # Read all players
```

### What's Jinja2 (the templates)?
Flask uses Jinja2 to put Python data into HTML:
```html
{% for player in players %}      <!-- Python loop -->
  <p>{{ player.name }}</p>       <!-- Insert variable -->
{% endfor %}
```

### What's the fetch() API?
The JavaScript `fetch()` sends requests to your Flask routes without reloading the page:
```javascript
const res = await fetch('/api/player', {
    method: 'POST',
    body: JSON.stringify({name: 'Rohit'})
});
const data = await res.json();
```
