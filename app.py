from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cricket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ─────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    batting_innings = db.relationship('BattingPerformance', backref='player', lazy=True)
    bowling_innings = db.relationship('BowlingPerformance', backref='player', lazy=True)
    fielding_innings = db.relationship('FieldingPerformance', backref='player', lazy=True)

    def career_batting(self):
        innings = [b for b in self.batting_innings if b.balls_faced > 0]
        runs = sum(b.runs for b in innings)
        balls = sum(b.balls_faced for b in innings)
        fours = sum(b.fours for b in innings)
        sixes = sum(b.sixes for b in innings)
        dismissals = sum(1 for b in innings if b.dismissed)
        highest = max((b.runs for b in innings), default=0)
        avg = runs / dismissals if dismissals > 0 else runs
        sr = (runs / balls * 100) if balls > 0 else 0
        return {
            'innings': len(innings), 'runs': runs, 'balls': balls,
            'fours': fours, 'sixes': sixes, 'average': round(avg, 2),
            'strike_rate': round(sr, 2), 'highest': highest, 'dismissals': dismissals
        }

    def career_bowling(self):
        innings = [b for b in self.bowling_innings if b.balls_bowled > 0]
        wickets = sum(b.wickets for b in innings)
        runs = sum(b.runs_conceded for b in innings)
        balls = sum(b.balls_bowled for b in innings)
        overs = balls // 6 + (balls % 6) / 10
        economy = (runs / (balls / 6)) if balls > 0 else 0
        avg = runs / wickets if wickets > 0 else None
        return {
            'innings': len(innings), 'wickets': wickets, 'runs': runs,
            'overs': round(overs, 1), 'economy': round(economy, 2),
            'average': round(avg, 2) if avg else '-'
        }

    def career_fielding(self):
        catches = sum(f.catches for f in self.fielding_innings)
        run_outs = sum(f.run_outs for f in self.fielding_innings)
        return {'catches': catches, 'run_outs': run_outs}

    def matches_played(self):
        match_ids = set()
        for b in self.batting_innings:
            match_ids.add(b.match_id)
        for b in self.bowling_innings:
            match_ids.add(b.match_id)
        return len(match_ids)


class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_a_name = db.Column(db.String(100), nullable=False)
    team_b_name = db.Column(db.String(100), nullable=False)
    overs = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='setup')  # setup, innings1, innings2, complete
    current_innings = db.Column(db.Integer, default=1)
    batting_team = db.Column(db.String(100))
    bowling_team = db.Column(db.String(100))
    winner = db.Column(db.String(100))
    result_text = db.Column(db.String(200))
    toss_winner = db.Column(db.String(100))
    toss_choice = db.Column(db.String(10))

    innings = db.relationship('Innings', backref='match', lazy=True, order_by='Innings.innings_number')
    team_a_players = db.relationship('MatchPlayer', foreign_keys='MatchPlayer.match_id',
                                      primaryjoin="and_(MatchPlayer.match_id==Match.id, MatchPlayer.team=='A')",
                                      lazy=True)
    team_b_players = db.relationship('MatchPlayer', foreign_keys='MatchPlayer.match_id',
                                      primaryjoin="and_(MatchPlayer.match_id==Match.id, MatchPlayer.team=='B')",
                                      lazy=True)


class MatchPlayer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    team = db.Column(db.String(1), nullable=False)  # 'A' or 'B'
    batting_order = db.Column(db.Integer)

    player = db.relationship('Player')


class Innings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    innings_number = db.Column(db.Integer, nullable=False)
    batting_team = db.Column(db.String(100))
    bowling_team = db.Column(db.String(100))
    total_runs = db.Column(db.Integer, default=0)
    total_wickets = db.Column(db.Integer, default=0)
    total_balls = db.Column(db.Integer, default=0)
    extras = db.Column(db.Integer, default=0)
    is_complete = db.Column(db.Boolean, default=False)
    target = db.Column(db.Integer)

    balls = db.relationship('Ball', backref='innings', lazy=True, order_by='Ball.id')
    batting_performances = db.relationship('BattingPerformance', backref='innings', lazy=True)
    bowling_performances = db.relationship('BowlingPerformance', backref='innings', lazy=True)
    fielding_performances = db.relationship('FieldingPerformance', backref='innings', lazy=True)

    def current_over(self):
        return self.total_balls // 6

    def current_ball_in_over(self):
        return self.total_balls % 6

    def over_display(self):
        return f"{self.current_over()}.{self.current_ball_in_over()}"


class Ball(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    innings_id = db.Column(db.Integer, db.ForeignKey('innings.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    over_number = db.Column(db.Integer, nullable=False)
    ball_number = db.Column(db.Integer, nullable=False)
    batsman_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    bowler_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    runs = db.Column(db.Integer, default=0)
    extra_type = db.Column(db.String(10))  # wide, no_ball, bye, leg_bye, None
    extra_runs = db.Column(db.Integer, default=0)
    wicket = db.Column(db.Boolean, default=False)
    wicket_type = db.Column(db.String(20))  # bowled, caught, lbw, run_out, stumped, hit_wicket
    fielder_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    commentary = db.Column(db.String(200))

    batsman = db.relationship('Player', foreign_keys=[batsman_id])
    bowler = db.relationship('Player', foreign_keys=[bowler_id])
    fielder = db.relationship('Player', foreign_keys=[fielder_id])


class BattingPerformance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    innings_id = db.Column(db.Integer, db.ForeignKey('innings.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    runs = db.Column(db.Integer, default=0)
    balls_faced = db.Column(db.Integer, default=0)
    fours = db.Column(db.Integer, default=0)
    sixes = db.Column(db.Integer, default=0)
    dismissed = db.Column(db.Boolean, default=False)
    dismissal_type = db.Column(db.String(50))
    batting_position = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=False)


class BowlingPerformance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    innings_id = db.Column(db.Integer, db.ForeignKey('innings.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    balls_bowled = db.Column(db.Integer, default=0)
    runs_conceded = db.Column(db.Integer, default=0)
    wickets = db.Column(db.Integer, default=0)
    wides = db.Column(db.Integer, default=0)
    no_balls = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=False)


class FieldingPerformance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    innings_id = db.Column(db.Integer, db.ForeignKey('innings.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    catches = db.Column(db.Integer, default=0)
    run_outs = db.Column(db.Integer, default=0)


# ─────────────────────────────────────────────
# ROUTES - PAGES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    matches = Match.query.order_by(Match.date.desc()).all()
    players = Player.query.order_by(Player.name).all()
    return render_template('index.html', matches=matches, players=players)


@app.route('/players')
def players():
    players = Player.query.order_by(Player.name).all()
    return render_template('players.html', players=players)


@app.route('/player/<int:player_id>')
def player_detail(player_id):
    player = Player.query.get_or_404(player_id)
    batting = player.career_batting()
    bowling = player.career_bowling()
    fielding = player.career_fielding()
    matches = player.matches_played()

    recent_innings = BattingPerformance.query.filter_by(player_id=player_id)\
        .order_by(BattingPerformance.id.desc()).limit(10).all()

    return render_template('player_detail.html', player=player, batting=batting,
                           bowling=bowling, fielding=fielding, matches=matches,
                           recent_innings=recent_innings)


@app.route('/new_match', methods=['GET', 'POST'])
def new_match():
    players = Player.query.order_by(Player.name).all()
    return render_template('new_match.html', players=players)


@app.route('/match/<int:match_id>')
def match_detail(match_id):
    match = Match.query.get_or_404(match_id)
    innings_list = Innings.query.filter_by(match_id=match_id).all()
    return render_template('match_detail.html', match=match, innings_list=innings_list)


@app.route('/score/<int:match_id>')
def score(match_id):
    match = Match.query.get_or_404(match_id)
    if match.status == 'complete':
        return redirect(url_for('match_detail', match_id=match_id))

    current_innings = Innings.query.filter_by(
        match_id=match_id, innings_number=match.current_innings
    ).first()

    all_players = Player.query.order_by(Player.name).all()
    match_players_a = MatchPlayer.query.filter_by(match_id=match_id, team='A').all()
    match_players_b = MatchPlayer.query.filter_by(match_id=match_id, team='B').all()

    batting_team_players = match_players_a if match.batting_team == match.team_a_name else match_players_b
    bowling_team_players = match_players_b if match.batting_team == match.team_a_name else match_players_a

    active_batting = BattingPerformance.query.filter_by(innings_id=current_innings.id if current_innings else None, is_active=True).all() if current_innings else []
    active_bowling = BowlingPerformance.query.filter_by(innings_id=current_innings.id if current_innings else None, is_active=True).first() if current_innings else None

    recent_balls = Ball.query.filter_by(innings_id=current_innings.id if current_innings else None)\
        .order_by(Ball.id.desc()).limit(12).all() if current_innings else []

    batting_scorecard = BattingPerformance.query.filter_by(
        innings_id=current_innings.id if current_innings else None
    ).all() if current_innings else []

    bowling_scorecard = BowlingPerformance.query.filter_by(
        innings_id=current_innings.id if current_innings else None
    ).all() if current_innings else []

    return render_template('score.html',
        match=match,
        innings=current_innings,
        batting_team_players=batting_team_players,
        bowling_team_players=bowling_team_players,
        active_batting=active_batting,
        active_bowling=active_bowling,
        recent_balls=recent_balls,
        batting_scorecard=batting_scorecard,
        bowling_scorecard=bowling_scorecard,
        all_players=all_players
    )


# ─────────────────────────────────────────────
# API ROUTES
# ─────────────────────────────────────────────

@app.route('/api/player', methods=['POST'])
def create_player():
    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400
    if Player.query.filter_by(name=name).first():
        return jsonify({'error': 'Player already exists'}), 400
    player = Player(name=name)
    db.session.add(player)
    db.session.commit()
    return jsonify({'id': player.id, 'name': player.name})


@app.route('/api/match', methods=['POST'])
def create_match():
    data = request.json
    match = Match(
        team_a_name=data['team_a_name'],
        team_b_name=data['team_b_name'],
        overs=int(data['overs']),
        toss_winner=data.get('toss_winner'),
        toss_choice=data.get('toss_choice'),
        status='setup'
    )

    if data.get('toss_winner') and data.get('toss_choice'):
        if data['toss_choice'] == 'bat':
            match.batting_team = data['toss_winner']
            match.bowling_team = data['team_b_name'] if data['toss_winner'] == data['team_a_name'] else data['team_a_name']
        else:
            match.bowling_team = data['toss_winner']
            match.batting_team = data['team_b_name'] if data['toss_winner'] == data['team_a_name'] else data['team_a_name']

    db.session.add(match)
    db.session.flush()

    for pid in data.get('team_a_players', []):
        mp = MatchPlayer(match_id=match.id, player_id=int(pid), team='A')
        db.session.add(mp)
    for pid in data.get('team_b_players', []):
        mp = MatchPlayer(match_id=match.id, player_id=int(pid), team='B')
        db.session.add(mp)

    db.session.commit()
    return jsonify({'match_id': match.id})


@app.route('/api/match/<int:match_id>/start_innings', methods=['POST'])
def start_innings(match_id):
    match = Match.query.get_or_404(match_id)
    data = request.json

    innings = Innings(
        match_id=match_id,
        innings_number=match.current_innings,
        batting_team=match.batting_team,
        bowling_team=match.bowling_team,
        target=data.get('target')
    )
    db.session.add(innings)
    db.session.flush()

    # Create batting/bowling/fielding perf stubs for all players
    batting_team = 'A' if match.batting_team == match.team_a_name else 'B'
    bowling_team = 'B' if batting_team == 'A' else 'A'

    bat_players = MatchPlayer.query.filter_by(match_id=match_id, team=batting_team).all()
    bowl_players = MatchPlayer.query.filter_by(match_id=match_id, team=bowling_team).all()

    for mp in bat_players:
        bp = BattingPerformance(match_id=match_id, innings_id=innings.id, player_id=mp.player_id)
        db.session.add(bp)
        fp = FieldingPerformance(match_id=match_id, innings_id=innings.id, player_id=mp.player_id)
        db.session.add(fp)

    for mp in bowl_players:
        bp = BowlingPerformance(match_id=match_id, innings_id=innings.id, player_id=mp.player_id)
        db.session.add(bp)
        fp = FieldingPerformance(match_id=match_id, innings_id=innings.id, player_id=mp.player_id)
        db.session.add(fp)

    match.status = f'innings{match.current_innings}'
    db.session.commit()

    return jsonify({'innings_id': innings.id})


@app.route('/api/innings/<int:innings_id>/set_batsmen', methods=['POST'])
def set_batsmen(innings_id):
    data = request.json
    innings = Innings.query.get_or_404(innings_id)

    BattingPerformance.query.filter_by(innings_id=innings_id, is_active=True).update({'is_active': False})

    for pid in data['player_ids']:
        perf = BattingPerformance.query.filter_by(innings_id=innings_id, player_id=int(pid)).first()
        if perf:
            perf.is_active = True

    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/innings/<int:innings_id>/set_bowler', methods=['POST'])
def set_bowler(innings_id):
    data = request.json
    innings = Innings.query.get_or_404(innings_id)

    BowlingPerformance.query.filter_by(innings_id=innings_id, is_active=True).update({'is_active': False})
    perf = BowlingPerformance.query.filter_by(innings_id=innings_id, player_id=int(data['player_id'])).first()
    if perf:
        perf.is_active = True

    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/innings/<int:innings_id>/ball', methods=['POST'])
def record_ball(innings_id):
    innings = Innings.query.get_or_404(innings_id)
    match = Match.query.get(innings.match_id)
    data = request.json

    runs = int(data.get('runs', 0))
    extra_type = data.get('extra_type')  # wide, no_ball, bye, leg_bye
    extra_runs = int(data.get('extra_runs', 0))
    wicket = data.get('wicket', False)
    wicket_type = data.get('wicket_type')
    batsman_id = data.get('batsman_id')
    bowler_id = data.get('bowler_id')
    fielder_id = data.get('fielder_id')

    # Wides and no-balls don't count as a legal delivery
    is_legal = extra_type not in ('wide', 'no_ball')

    ball = Ball(
        innings_id=innings_id,
        match_id=innings.match_id,
        over_number=innings.total_balls // 6,
        ball_number=(innings.total_balls % 6) + 1,
        batsman_id=batsman_id,
        bowler_id=bowler_id,
        runs=runs,
        extra_type=extra_type,
        extra_runs=extra_runs,
        wicket=wicket,
        wicket_type=wicket_type,
        fielder_id=fielder_id
    )
    db.session.add(ball)

    # Update innings totals
    total_added = runs + extra_runs
    innings.total_runs += total_added
    innings.extras += extra_runs
    if wicket:
        innings.total_wickets += 1
    if is_legal:
        innings.total_balls += 1

    # Update batsman performance
    if batsman_id and is_legal and extra_type not in ('bye', 'leg_bye'):
        bp = BattingPerformance.query.filter_by(innings_id=innings_id, player_id=batsman_id).first()
        if bp:
            if extra_type is None:
                bp.runs += runs
                bp.balls_faced += 1
                if runs == 4:
                    bp.fours += 1
                elif runs == 6:
                    bp.sixes += 1
            if wicket and wicket_type != 'run_out':
                bp.dismissed = True
                bp.dismissal_type = wicket_type
                bp.is_active = False

    elif batsman_id and is_legal:
        bp = BattingPerformance.query.filter_by(innings_id=innings_id, player_id=batsman_id).first()
        if bp:
            bp.balls_faced += 1
            if wicket and wicket_type != 'run_out':
                bp.dismissed = True
                bp.dismissal_type = wicket_type
                bp.is_active = False

    # Handle run outs separately
    if wicket and wicket_type == 'run_out':
        out_batsman_id = data.get('run_out_batsman_id', batsman_id)
        bp = BattingPerformance.query.filter_by(innings_id=innings_id, player_id=out_batsman_id).first()
        if bp:
            bp.dismissed = True
            bp.dismissal_type = 'run_out'
            bp.is_active = False

    # Update bowler performance
    if bowler_id:
        bowling = BowlingPerformance.query.filter_by(innings_id=innings_id, player_id=bowler_id).first()
        if bowling:
            if is_legal:
                bowling.balls_bowled += 1
            if extra_type == 'wide':
                bowling.wides += 1
                bowling.runs_conceded += extra_runs + 1
            elif extra_type == 'no_ball':
                bowling.no_balls += 1
                bowling.runs_conceded += runs + extra_runs + 1
            elif extra_type in ('bye', 'leg_bye'):
                pass  # byes don't count against bowler
            else:
                bowling.runs_conceded += runs
            if wicket and wicket_type not in ('run_out',):
                bowling.wickets += 1

    # Update fielder stats
    if fielder_id:
        fp = FieldingPerformance.query.filter_by(innings_id=innings_id, player_id=fielder_id).first()
        if fp:
            if wicket_type in ('caught', 'stumped'):
                fp.catches += 1
            elif wicket_type == 'run_out':
                fp.run_outs += 1

    # Check innings end
    innings_over = False
    legal_overs = innings.total_balls // 6
    if legal_overs >= match.overs or innings.total_wickets >= 10:
        innings_over = True
        innings.is_complete = True

        if match.current_innings == 1:
            match.current_innings = 2
            match.batting_team, match.bowling_team = match.bowling_team, match.batting_team
            match.status = 'innings2'
        else:
            match.status = 'complete'
            # Determine winner
            inn1 = Innings.query.filter_by(match_id=match.id, innings_number=1).first()
            inn2 = innings
            if inn2.total_runs > inn1.total_runs:
                match.winner = inn2.batting_team
                wickets_left = 10 - inn2.total_wickets
                match.result_text = f"{inn2.batting_team} won by {wickets_left} wicket{'s' if wickets_left != 1 else ''}"
            elif inn1.total_runs > inn2.total_runs:
                match.winner = inn1.batting_team
                margin = inn1.total_runs - inn2.total_runs
                match.result_text = f"{inn1.batting_team} won by {margin} run{'s' if margin != 1 else ''}"
            else:
                match.winner = 'Tie'
                match.result_text = "Match tied!"

    db.session.commit()

    return jsonify({
        'ok': True,
        'innings_over': innings_over,
        'total_runs': innings.total_runs,
        'total_wickets': innings.total_wickets,
        'total_balls': innings.total_balls,
        'over_display': innings.over_display(),
        'match_status': match.status,
        'result_text': match.result_text if innings_over and match.status == 'complete' else None
    })


@app.route('/api/innings/<int:innings_id>/state')
def innings_state(innings_id):
    innings = Innings.query.get_or_404(innings_id)
    match = Match.query.get(innings.match_id)

    active_batting = BattingPerformance.query.filter_by(innings_id=innings_id, is_active=True).all()
    active_bowling = BowlingPerformance.query.filter_by(innings_id=innings_id, is_active=True).first()

    recent_balls = Ball.query.filter_by(innings_id=innings_id).order_by(Ball.id.desc()).limit(12).all()

    batting_scorecard = BattingPerformance.query.filter_by(innings_id=innings_id).all()
    bowling_scorecard = BowlingPerformance.query.filter_by(innings_id=innings_id).all()

    def ball_icon(b):
        if b.wicket:
            return 'W'
        if b.extra_type == 'wide':
            return 'Wd'
        if b.extra_type == 'no_ball':
            return 'Nb'
        if b.extra_type in ('bye', 'leg_bye'):
            return f'{b.extra_runs}b'
        return str(b.runs)

    return jsonify({
        'total_runs': innings.total_runs,
        'total_wickets': innings.total_wickets,
        'total_balls': innings.total_balls,
        'over_display': innings.over_display(),
        'extras': innings.extras,
        'target': innings.target,
        'required': (innings.target - innings.total_runs) if innings.target else None,
        'match_status': match.status,
        'batting_team': innings.batting_team,
        'bowling_team': innings.bowling_team,
        'active_batsmen': [
            {
                'id': b.player_id,
                'name': b.player.name,
                'runs': b.runs,
                'balls': b.balls_faced,
                'fours': b.fours,
                'sixes': b.sixes,
                'sr': round(b.runs / b.balls_faced * 100, 1) if b.balls_faced > 0 else 0
            } for b in active_batting
        ],
        'active_bowler': {
            'id': active_bowling.player_id,
            'name': active_bowling.player.name,
            'overs': f"{active_bowling.balls_bowled // 6}.{active_bowling.balls_bowled % 6}",
            'wickets': active_bowling.wickets,
            'runs': active_bowling.runs_conceded
        } if active_bowling else None,
        'recent_balls': [ball_icon(b) for b in reversed(recent_balls)],
        'batting_scorecard': [
            {
                'name': b.player.name,
                'runs': b.runs,
                'balls': b.balls_faced,
                'fours': b.fours,
                'sixes': b.sixes,
                'sr': round(b.runs / b.balls_faced * 100, 1) if b.balls_faced > 0 else 0,
                'dismissed': b.dismissed,
                'dismissal': b.dismissal_type or ('not out' if b.balls_faced > 0 else '-'),
                'is_active': b.is_active
            } for b in batting_scorecard if b.balls_faced > 0 or b.is_active
        ],
        'bowling_scorecard': [
            {
                'name': b.player.name,
                'overs': f"{b.balls_bowled // 6}.{b.balls_bowled % 6}",
                'wickets': b.wickets,
                'runs': b.runs_conceded,
                'economy': round(b.runs_conceded / (b.balls_bowled / 6), 2) if b.balls_bowled >= 6 else '-',
                'is_active': b.is_active
            } for b in bowling_scorecard if b.balls_bowled > 0 or b.is_active
        ]
    })


@app.route('/api/match/<int:match_id>/delete', methods=['POST'])
def delete_match(match_id):
    match = Match.query.get_or_404(match_id)
    # Delete cascading data
    for innings in match.innings:
        Ball.query.filter_by(innings_id=innings.id).delete()
        BattingPerformance.query.filter_by(innings_id=innings.id).delete()
        BowlingPerformance.query.filter_by(innings_id=innings.id).delete()
        FieldingPerformance.query.filter_by(innings_id=innings.id).delete()
    Innings.query.filter_by(match_id=match_id).delete()
    MatchPlayer.query.filter_by(match_id=match_id).delete()
    db.session.delete(match)
    db.session.commit()
    return jsonify({'ok': True})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
