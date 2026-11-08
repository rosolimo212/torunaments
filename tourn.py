# coding: utf-8
import numpy as np
import pandas as pd

import random
import math

import seaborn as sns
import matplotlib.pyplot as plt

def get_data_from_team_dict(teams_dct, itm):
    """
    converter  temas dict to other datatypres
    params:
    teams_dct (dict): dict with team params
    itm (str): 'teams list' returns list, 'full data frame' returns pandas data frame
    """
    res = ''
    if itm == 'teams list':
        return list(teams_dct.keys())
    elif itm == 'full data frame':
        return pd.DataFrame.from_dict(teams_dct, orient='index')#, columns=['team_name', 'start_rating', 'is_active', 'main_value'])
    

def update_team_dict(teams_dct, column_name, values):
    """
    update data (1 param) in dict in all indexes 
    params:
    column_name (str): name of param in dict
    values (list or array): data to update
    """
    work_dct = teams_dct.copy()
    df = get_data_from_team_dict(work_dct, 'full data frame')
    df[column_name] = values

    return df.to_dict('index')


def elo_prob(rw=1600, rb=1600):
    """
    base elo propability without changing k for newcommets etc.
    returns probability in range [0;1]
    """
    rw = float(rw)
    rb = float(rb)
    res = 1 / (1 + np.power(10, (rb-rw) / 400))
    return res

def get_match(rating1=1600, rating2=1600, total=0, sigma=2.5):
    """ 
    get match result according elo rating, total scores and sigma of probability distribution
    params:
    rating1 (int or float): first team elo rating
    rating2 (int or float): second team elo rating
    total (int): measure of a number of goals
    sigma (float): measure of results dispersion

    returns typle with score, for example (1,0) means the first team won second with score 1-0
    """

    # base probability
    # based on 100 elo meand approximately win on 1 goal (1-0, 2-1 etc.)
    norm_factor = 15
    mult_factor = 100
    mu = mult_factor * (elo_prob(rating1, rating2) - 0.5) / norm_factor

    # current different between teams in this proba
    base_res = np.round(random.normalvariate(mu, sigma), 0)

    # scores from total and diffs
    if base_res > 0:
        res2 = total
        res1 = total + base_res
    else:
        res1 = total
        res2 = total - base_res

    return int(res1), int(res2)


def make_random_schedule(teams_dct, size):
    """ 
    make a ramdom schedule for future matches withought simulation 
    params:
    size: total number of ramdom pairs

    returns list of tuples
    """
    team_list = get_data_from_team_dict(teams_dct, 'teams list')
    pairs = []
    for i in range(size):
        pair = tuple(random.sample(team_list, 2))
        if pair[0] == pair[1]:
            print('+')
        pairs.append(pair)

    return pairs

def simulate_matches_by_schedule(teams_dct, schedule, total=(0,1), sigma=(2.5, 2.6), last_match_id=0, play_match=None):
    """ 
    make a simulation mathes in current schedule and prepair game log  
    params:
    teams_dct (dict): dict with team params
    schedule (list of tuples): schedule with teams ids
    total (int): measure of a number of goals
    sigma (float): measure of results dispersion
    last_match_id (int): id of a last match (from other parts of tournamnet)

    returns pandas data frame with tournament log 
    """
    id0 = []
    id1 = []
    sc0 = []
    sc1 = []
    
    # randint's upper bound is exclusive, so the passed ranges are closed on both ends:
    # total=(0, 1) is 0 or 1, sigma=(2.5, 2.6) is 2.5 or 2.6
    total_low = int(total[0])
    total_high = int(total[1])
    sigma_low = int(round(float(sigma[0]) * 10))
    sigma_high = int(round(float(sigma[1]) * 10))
    for pair in schedule:
        if len(pair) < 2:
            continue
        if play_match is None:
            match_total = np.random.randint(total_low, total_high + 1)
            match_sigma = np.random.randint(sigma_low, sigma_high + 1) / 10
            res = get_match(
                teams_dct[pair[0]]['start_rating'],
                teams_dct[pair[1]]['start_rating'],
                match_total, match_sigma
                    )
        else:
            res = play_match(pair[0], pair[1])
        id0.append(pair[0])
        id1.append(pair[1])
        sc0.append(int(res[0]))
        sc1.append(int(res[1]))
    if len(id0) == 0:
        return pd.DataFrame(columns=['id0', 'id1', 'score0', 'score1', 'match_id', 'team0_name', 'team1_name', 'overtime_case', 'penalty_case'])
    log_df = pd.DataFrame([id0, id1,sc0, sc1]).T
    log_df.columns = ['id0', 'id1', 'score0', 'score1']


    log_df['match_id'] = range(last_match_id+1, last_match_id+len(log_df)+1)
    log_df['team0_name'] = log_df['id0'].apply(lambda x: teams_dct[x]['team_name'])
    log_df['team1_name'] = log_df['id1'].apply(lambda x: teams_dct[x]['team_name'])
    log_df['overtime_case'] = np.random.choice([0,1,2], len(log_df))
    log_df['penalty_case'] = np.random.choice([0,1], len(log_df))

    return log_df

def team_table(df, teams_dct):
    # first of all tale only home teams 
    df_home=df.copy()

    df_home['team_id'] = df_home['id0']
    df_home['opponent_id'] = df_home['id1']
    df_home['team_score'] = df_home['score0']
    df_home['opponent_score'] = df_home['score1']
    df_home['venue'] = 'Home'
    df_home['penalty_result'] = np.where(df_home['penalty_case'] == 1, 'Win', 'Lose')
    
    # and away team symmetrical
    df_away=df.copy()
    
    df_away['team_id'] = df_away['id1']
    df_away['opponent_id'] = df_away['id0']
    df_away['team_score'] = df_away['score1']
    df_away['opponent_score'] = df_away['score0']
    df_away['venue'] = 'Away'
    df_away['penalty_result'] = np.where(df_away['penalty_case'] == 0, 'Win', 'Lose')

    # get all tohether
    team_df = pd.concat([df_home, df_away])
    team_df = team_df.reset_index()

    team_df = team_df[['match_id','team_id','opponent_id','team_score','opponent_score', 'venue', 'overtime_case', 'penalty_case', 'penalty_result']]

    team_df['result'] = np.where(
                                    (team_df['team_score'] > team_df['opponent_score']), 'Win', 
                                                                np.where(
                                                                    (team_df['team_score'] < team_df['opponent_score']), 'Lose', 'Draw'
                                                                        )
                                )
    team_df['full_result'] = np.where(
                                     (team_df['result'] == 'Draw'), team_df['penalty_result'], team_df['result']
                                     )

    team_df['game_number']=team_df.sort_values(['match_id'], ascending=[True]) \
                 .groupby(['team_id']) \
                 .cumcount() + 1
    team_df['id'] = team_df.index

    team_df['team_name'] = team_df['team_id'].apply(lambda x: teams_dct[x]['team_name'])
    team_df['started_rating'] = team_df['team_id'].apply(lambda x: teams_dct[x]['start_rating'])
    
    # get additional fields
    # footbal points
    team_df['points'] = np.where(
                                        team_df['result'] == 'Win', 3,
                                        np.where(
                                            team_df['result'] == 'Draw', 1, 0
                                                )
                                      )
    # chess points
    team_df['score'] = np.where(
                                        team_df['result'] == 'Win', 1,
                                        np.where(
                                            team_df['result'] == 'Draw', 0.5, 0
                                                )
                                      )
    team_df['full_score'] = np.where(
                                    team_df['full_result'] == 'Win', 1,
                                    np.where(
                                        team_df['full_result'] == 'Draw', 0.5, 0
                                            )
                                    )
    # usefull bool fields
    result_ohe = pd.get_dummies(team_df['result'], prefix='is')
    team_df = pd.concat([team_df, result_ohe], axis=1)

    # very important sorting
    team_df = team_df.sort_values(
        by=['game_number', 'venue'], 
        ascending=[True, False])

    team_df['is_dry_match'] = np.where(team_df['opponent_score'] == 0, 1, 0)

    # whole history stat
    team_df['wins'] = (team_df.groupby('team_id')['points'].transform(lambda x: (x == 3).cumsum()))
    team_df['draws'] = (team_df.groupby('team_id')['points'].transform(lambda x: (x == 1).cumsum()))
    team_df['loses'] = (team_df.groupby('team_id')['points'].transform(lambda x: (x == 0).cumsum()))

    team_df['scored'] = team_df.sort_values(by=['match_id'], ascending=True)\
                           .groupby(['team_id'])['team_score']\
                           .cumsum()
    team_df['mised'] = team_df.sort_values(by=['match_id'], ascending=True)\
                           .groupby(['team_id'])['opponent_score']\
                           .cumsum()
    
    team_df['commulative_score'] = team_df.groupby(['team_id'])['score'].cumsum()
    
    team_df['swiss_value'] = team_df['commulative_score'] * 100 + team_df['wins'] * 10 + np.random.randint(0, 100, size=len(team_df)) / 1000

    return team_df


def find_best_params_for_swiss_tourn(n_teams=50, n_prizes=3):
    """ 
    Magic formula to find number of rounds
    """
    return math.floor(math.sqrt(n_teams + (n_prizes - 1)))


def _clone_swiss_dict(swiss_dct):
    cloned = {}
    for team, info in swiss_dct.items():
        item = info.copy()
        opponents = item.get('opponents_list', [])
        item['opponents_list'] = list(opponents)
        cloned[team] = item
    return cloned


def _init_swiss_dict(teams_dct):
    swiss_dct = {}
    for team, info in teams_dct.items():
        item = info.copy()
        item['opponents_list'] = []
        item['main_value'] = info['main_value'] + info['start_rating']
        swiss_dct[team] = item
    return swiss_dct


def make_swiss_round_schedule(swiss_dct, sorted_type, allow_rematch=False):
    """ 
    One round schedule accoridng last results.
    A failed strict pairing raises ValueError. With allow_rematch, a team that
    has no fresh opponent is paired with the unpaired side it has met least often.
    """
    # list of teams in current ciclteams_dcte
    current_lst = []
    # list of pairs
    pairs = []

    keys_to_calc = sorted(swiss_dct.keys(), key=lambda x: swiss_dct[x]['main_value'], reverse=True)
    
    for i in keys_to_calc:
        if i in current_lst:
            continue
        
        # list of two id in one match
        pair = []

        # current team
        current_lst.append(i)

        # form opponents list 
        work_item = swiss_dct[i]
        item_opponent_list = list(work_item['opponents_list'])

        work_dct = swiss_dct.copy()
        # delete current teams in cicle 
        # they are ready
        for key in current_lst:
            work_dct.pop(key, None)
        # delete last opponetns
        for key in item_opponent_list:
            work_dct.pop(key, None)
        # find best opponent by main value
        target_lst = list(dict(sorted(work_dct.items(), key=lambda item: item[1]['main_value'], reverse=True)).keys())

        if len(target_lst) == 0:
            if not allow_rematch:
                raise ValueError('no legal opponent')
            candidates = []
            for key, item in swiss_dct.items():
                if key in current_lst:
                    continue
                meetings = item_opponent_list.count(key)
                candidates.append((meetings, -item['main_value'], key))
            if len(candidates) == 0:
                raise ValueError('unpaired team has nobody left')
            candidates.sort()
            target_id = candidates[0][2]
        elif sorted_type == 'half':
            target_id = target_lst[math.floor(len(target_lst) / 2)]
        elif sorted_type == 'best':
            target_id = target_lst[0]
        else:
            raise ValueError('unknown swiss sorted_type: ' + str(sorted_type))

        # update lists
        pair.append(i)
        pair.append(target_id)
        pairs.append(pair)

        current_lst.append(target_id)

    paired = [team for pair in pairs for team in pair]
    if len(paired) != len(swiss_dct) or len(paired) != len(set(paired)):
        raise ValueError('incomplete swiss round')

    return pairs


def _pair_swiss_round(swiss_dct, team_df, game_number, sorted_type, n_attempts, allow_rematch=False):
    """
    Build the next round from a copy of the standings.
    A failed attempt does not write opponents back into swiss_dct.
    """
    prev = team_df[team_df['game_number'] == game_number]
    sample_key = next(iter(swiss_dct))
    base = {}
    for team in swiss_dct:
        rows = prev[prev['team_id'] == team]
        opponent_id = rows['opponent_id'].values[0]
        if isinstance(sample_key, int):
            opponent_id = int(opponent_id)
        base[team] = {
            'swiss_value': float(rows['swiss_value'].values[0]),
            'opponent_id': opponent_id,
            'opponents': list(swiss_dct[team]['opponents_list']),
        }

    teams = list(swiss_dct.keys())
    tries = 1 if allow_rematch else n_attempts
    for attempt in range(tries):
        trial = _clone_swiss_dict(swiss_dct)
        noise = np.random.randint(0, 100, size=len(teams)) / 1000
        for idx, team in enumerate(teams):
            opponents = list(base[team]['opponents'])
            opponents.append(base[team]['opponent_id'])
            trial[team]['opponents_list'] = opponents
            trial[team]['main_value'] = base[team]['swiss_value'] + float(noise[idx])
        try:
            schedule = make_swiss_round_schedule(trial, sorted_type=sorted_type, allow_rematch=allow_rematch)
        except Exception:
            continue
        return schedule, trial
    return None, None


def _play_swiss_tournament(teams_dct, n_rounds, n_attempts, is_verbose, total, sigma, allow_rematch, play_match=None):
    if len(teams_dct) % 2 != 0:
        raise ValueError('swiss tournament needs an even number of teams')

    swiss_dct = _init_swiss_dict(teams_dct)
    log_df = pd.DataFrame()
    team_df = None

    for round in range(1, n_rounds + 1):
        if is_verbose == True:
            print('round: ', round)

        if round == 1:
            try:
                round_schedule = make_swiss_round_schedule(swiss_dct, sorted_type='half', allow_rematch=allow_rematch)
            except Exception as e:
                if is_verbose == True:
                    print(f"Error in function make_swiss_round_schedule: {e}")
                return None
        else:
            round_schedule, trial = _pair_swiss_round(
                swiss_dct, team_df, game_number=round - 1,
                sorted_type='best', n_attempts=n_attempts, allow_rematch=allow_rematch,
            )
            if round_schedule is None:
                if is_verbose == True:
                    print(f"Function make_swiss_round_schedule failed after {n_attempts} attempts")
                return None
            swiss_dct = trial

        round_log_df = simulate_matches_by_schedule(
            teams_dct, round_schedule, last_match_id=len(log_df), total=total, sigma=sigma, play_match=play_match,
        )
        round_log_df['round'] = round
        log_df = pd.concat([log_df, round_log_df])
        team_df = team_table(log_df, teams_dct)

    return log_df, swiss_dct


def _begin_attempt(play_match):
    begin = getattr(play_match, "begin_attempt", None)
    if begin is not None:
        begin()


def _abort_attempt(play_match):
    abort = getattr(play_match, "abort_attempt", None)
    if abort is not None:
        abort()


def simulate_swiss_tourn(teams_dct, n_rounds=9, n_attempts=50, is_verbose=False, total=(0,1), sigma=(2.5, 2.6), play_match=None):
    """ 
    The whole tournament.
    A round that cannot be paired is thrown away and the tournament is generated again.
    If fresh draws still cannot avoid a repeat, the last attempt allows a rematch
    with the opponent met least often.
    """
    restarts = min(n_attempts, 10)
    for tournament_try in range(restarts):
        _begin_attempt(play_match)
        played = _play_swiss_tournament(
            teams_dct, n_rounds, n_attempts, is_verbose, total, sigma, allow_rematch=False, play_match=play_match,
        )
        if played is not None:
            return played
        _abort_attempt(play_match)
        if is_verbose == True:
            print(f"Swiss draw failed. Regenerating tournament, try {tournament_try + 1} of {restarts}")

    _begin_attempt(play_match)
    played = _play_swiss_tournament(
        teams_dct, n_rounds, n_attempts, is_verbose, total, sigma, allow_rematch=True, play_match=play_match,
    )
    if played is None:
        _abort_attempt(play_match)
        raise RuntimeError('swiss tournament could not be paired')
    return played
    

def get_round_robin_schedule(teams_dct, num_cycles=2):
    """ 
    get round robin schedule for teams
    """ 
    teams = get_data_from_team_dict(teams_dct, 'teams list')
    if len(teams) % 2 != 0:
        teams.append(None)
    
    num_rounds = len(teams) - 1
    schedule = []
    
    for cycle in range(num_cycles):
        matches = []
        for round in range(num_rounds):
            for i in range(len(teams)//2):
                if teams[i] is None or teams[len(teams)-1-i] is None:
                    continue
                matches.append((teams[i], teams[len(teams)-1-i]))
            
            teams = [teams[0]] + [teams[-1]] + teams[1:len(teams)-1]
        
        if cycle != 0:
            invert_m = []
            for m in matches:
                invert_m.append((m[1], m[0]))
            matches = invert_m
        
        schedule.append(matches)
    
    # and get flat list after all of it
    import itertools
    flat_schedule = list(itertools.chain.from_iterable(schedule))
    
    return flat_schedule


def make_playoff_round_schedule(teams_dct, seed_mode):
    playoff_dct = teams_dct.copy()
    
    if seed_mode == 'random':
        teams_lst = get_data_from_team_dict(playoff_dct, 'teams list')
        random.shuffle(teams_lst)

        return [tuple(teams_lst[i:i + 2]) for i in range(0, len(teams_lst), 2)]
    elif seed_mode == 'half':
        teams_df = get_data_from_team_dict(playoff_dct, 'full data frame')
        teams_lst = teams_df.sort_values(by='start_rating', ascending=False).index

        pairs = []
        pair = []

        for i in range(math.floor(len(teams_lst)/2)):
            pair = []
            pair.append(teams_lst[i])
            pair.append(teams_lst[i + math.floor(len(teams_lst)/2)])
            pairs.append(pair)

        return pairs
    

def simulate_playoff_tourn(teams_dct, seed_mode, total=(0,1), sigma=(2.5, 2.6), play_match=None):
    playoff_dct = teams_dct.copy()

    playoff_df = get_data_from_team_dict(teams_dct, 'full data frame')
    
    round = 1 
    log_df = pd.DataFrame()
    while len(playoff_df[playoff_df['is_active'] == 1]) > 1:
        schedule = make_playoff_round_schedule(playoff_dct, seed_mode)
        
        round_log_df = simulate_matches_by_schedule(
            playoff_dct, schedule, last_match_id=len(log_df), total=total, sigma=sigma, play_match=play_match,
        )
        round_log_df['round'] = round

        log_df = pd.concat([log_df, round_log_df])
        round_df = team_table(round_log_df, teams_dct)
        team_df = team_table(log_df, teams_dct)

        teams_for_delete = round_df[round_df['full_result'] != 'Win']['team_id'].values
        for team in teams_for_delete:
            del playoff_dct[team]
        playoff_df = get_data_from_team_dict(playoff_dct, 'full data frame')

        round = round + 1
    return log_df



def simulatate_combine_tournament(
    teams_dct, 
    total=(0,1), sigma=(2.5, 2.6),
    first_step_tourn_mode='round_robin',
    first_step_number_param=0,
    first_step_string_param='',
    first_step_groups=4,
    first_step_teams_to_promote=2,
    second_step_tourn_mode='playoff',
    second_step_number_param=0,
    second_step_string_param='', 
    is_verbose=False,
    play_match=None,
                            ):
    team_list = get_data_from_team_dict(teams_dct, 'teams list')
    np.random.shuffle(team_list)

    log_df = pd.DataFrame()
    next_stage_teams_list = []
    
    teams_in_group = math.ceil(len(team_list) / first_step_groups)
    for group_num in range(first_step_groups):
        group_lst = team_list[(group_num*teams_in_group):((group_num+1)*teams_in_group)]
        if len(group_lst) == 0:
            continue
        group_df = get_data_from_team_dict(teams_dct, 'full data frame')
        group_df = group_df[group_df.index.isin(group_lst)]
        group_dct = group_df.to_dict('index')
        
        if first_step_tourn_mode == 'round_robin':
            group_schedule = get_round_robin_schedule(group_dct, num_cycles=first_step_number_param)
            group_log_df = simulate_matches_by_schedule(group_dct, group_schedule, total=total, sigma=sigma, last_match_id=len(log_df), play_match=play_match)

        elif first_step_tourn_mode == 'random':
            group_schedule = make_random_schedule(group_dct, size=first_step_number_param)
            group_log_df = simulate_matches_by_schedule(group_dct, group_schedule, last_match_id=len(log_df), total=total, sigma=sigma, play_match=play_match)

        elif first_step_tourn_mode == 'swiss':
            group_log_df, swiss_dct  = simulate_swiss_tourn(group_dct, n_rounds=first_step_number_param, is_verbose=False, total=total, sigma=sigma, play_match=play_match)

        group_log_df['stage'] = 'first_stage'
        group_results_df = make_res_table(group_log_df, group_dct)
        place_col = 'swiss_place' if first_step_tourn_mode == 'swiss' else 'roundrobin_place'
        group_results_df['place'] = group_results_df[place_col]

        for team in group_results_df[group_results_df[place_col] <= first_step_teams_to_promote]['team_id'].values:
            next_stage_teams_list.append(team)
        
        log_df = pd.concat([log_df, group_log_df])

    teams_df = get_data_from_team_dict(teams_dct, 'full data frame')
    teams_df = teams_df[teams_df.index.isin(next_stage_teams_list)]
    final_dct = teams_df.to_dict('index')

    final_log_df = simulate_playoff_tourn(final_dct, seed_mode=second_step_string_param, total=total, sigma=sigma, play_match=play_match)
    final_log_df['stage'] = 'second_stage'
    final_results_df = make_res_table(final_log_df, teams_dct)
    final_results_df['place'] = final_results_df['playoff_place']

    group_standings = make_res_table(log_df, teams_dct)
    log_df = pd.concat([log_df, final_log_df])
    results_df = make_res_table(log_df, teams_dct)
    results_df = results_df.merge(final_results_df[['team_id', 'playoff_place']], 'left', on='team_id', suffixes=('', '_final'))

    # Playoff teams take places 1..K. Everyone else is ranked after them
    # by the group table, so a group place and a playoff place cannot collide.
    qual_ids = set(next_stage_teams_list)
    qual = final_results_df.sort_values(['playoff_value', 'team_id'], ascending=[False, True]).copy()
    qual['combined_place'] = np.arange(1, len(qual) + 1)
    non = group_standings[~group_standings['team_id'].isin(qual_ids)].sort_values(
        ['roundrobin_value', 'team_id'], ascending=[False, True]
    ).copy()
    non['combined_place'] = np.arange(len(qual) + 1, len(qual) + len(non) + 1)
    place_map = pd.concat([
        qual[['team_id', 'combined_place']],
        non[['team_id', 'combined_place']],
    ], ignore_index=True)
    results_df = results_df.merge(place_map, on='team_id', how='left')

    return log_df, results_df.sort_values(by='combined_place')



def make_res_table(log_df, teams_dct):
    team_df = team_table(log_df, teams_dct)
    res_df = team_df.groupby(['team_id', 'team_name', 'started_rating']).agg(
                                        games = ('game_number', 'max'),
                                        chess_points = ('score', 'sum'),
                                        footbal_points = ('points', 'sum'),
                                        scored = ('team_score', 'sum'),
                                        mised = ('opponent_score', 'sum'),
                                        wins = ('wins', lambda x: x[team_df.loc[x.index]['game_number'].idxmax()]),
                                        draws = ('draws', lambda x: x[team_df.loc[x.index]['game_number'].idxmax()]),
                                        loses = ('loses', lambda x: x[team_df.loc[x.index]['game_number'].idxmax()]),
                                        dry_matches = ('is_dry_match', 'sum'),
                                        swiss_value=('swiss_value', lambda x: x[team_df.loc[x.index]['game_number'].idxmax()]),
                                        playoff_value=('full_score', lambda x: (x * team_df.loc[x.index, 'game_number']).sum())
                                                                    ).reset_index().sort_values('swiss_value', ascending=False)
    res_df['goals_difference'] = res_df['scored'] - res_df['mised']
    res_df['points_per_game'] = res_df['footbal_points'] / res_df['games']
    # Tie-break is smaller than one scored goal, so it only splits exact ties.
    res_df['roundrobin_value'] = (
        res_df['footbal_points'] * 1000
        + res_df['goals_difference'] * 100
        + res_df['wins'] * 10
        + res_df['scored']
        + np.random.randint(0, 100, size=len(res_df)) / 10000
    )
    res_df['roundrobin_place'] = res_df['roundrobin_value'].rank(method='dense', ascending=False).astype('int')
    res_df['swiss_place'] = res_df['swiss_value'].rank(method='dense', ascending=False).astype('int')
    # One goal of difference (0.01) outweighs the tie-break (at most 0.0099).
    res_df['playoff_value'] = res_df['playoff_value'] + (res_df['goals_difference'] / 100) + (np.random.randint(0, 100, size=len(res_df)) / 10000)
    res_df['playoff_place'] = res_df['playoff_value'].rank(method='dense', ascending=False).astype('int')

    return res_df



def make_multuverse_simulation(
                            teams_dct, 
                            total=(0,1), sigma=(2.5, 2.6),
                            tourn_mode='round_robin',
                            tourn_number_param=0,
                            tourn_string_param='',  
                            n_iters=1000,
                            first_step_number_param=2,
                            first_step_teams_to_promote=2,
                            second_step_string_param='half',
                            ):
    """
    get full simulation in n_iters iteration to know the best results and metrics

    combine mode: tourn_string_param is the group format, tourn_number_param is
    the number of groups. first_step_number_param, first_step_teams_to_promote
    and second_step_string_param are the old hardcoded knobs (cycles or swiss
    rounds, how many advance, playoff seeding).
    """
    tournament_results_df = pd.DataFrame()
    for iter in range(n_iters):
        if tourn_mode == 'round_robin':
            iter_schedule = get_round_robin_schedule(teams_dct, num_cycles=tourn_number_param)
            iter_log_df = simulate_matches_by_schedule(teams_dct, iter_schedule, total=total, sigma=sigma, last_match_id=0)
            tournament_results_df_iter = make_res_table(iter_log_df, teams_dct)
            tournament_results_df_iter['place'] = tournament_results_df_iter['roundrobin_place']
            
        elif tourn_mode == 'random':
            iter_schedule = make_random_schedule(teams_dct, size=tourn_number_param)
            iter_log_df = simulate_matches_by_schedule(teams_dct, iter_schedule, last_match_id=0, total=total, sigma=sigma)
            tournament_results_df_iter = make_res_table(iter_log_df, teams_dct)
            tournament_results_df_iter['place'] = tournament_results_df_iter['roundrobin_place']

        elif tourn_mode == 'swiss':
            iter_log_df, swiss_dct  = simulate_swiss_tourn(teams_dct, n_rounds=tourn_number_param, is_verbose=False, total=total, sigma=sigma)
            tournament_results_df_iter = make_res_table(iter_log_df, teams_dct)
            tournament_results_df_iter['place'] = tournament_results_df_iter['swiss_place']

        elif tourn_mode == 'playoff':
            iter_log_df = simulate_playoff_tourn(teams_dct, seed_mode=tourn_string_param, total=total, sigma=sigma)
            tournament_results_df_iter = make_res_table(iter_log_df, teams_dct)
            tournament_results_df_iter['place'] = tournament_results_df_iter['playoff_place']

        elif tourn_mode == 'combine':
            iter_log_df, tournament_results_df_iter = simulatate_combine_tournament(    
                                                    teams_dct, 
                                                    total=total, sigma=sigma,
                                                    first_step_tourn_mode=tourn_string_param,
                                                    first_step_number_param=first_step_number_param,
                                                    first_step_string_param='',
                                                    first_step_groups=tourn_number_param,
                                                    first_step_teams_to_promote=first_step_teams_to_promote,
                                                    second_step_tourn_mode='playoff',
                                                    second_step_number_param=0,
                                                    second_step_string_param=second_step_string_param, 
                                                    is_verbose=False
                                                    )
            tournament_results_df_iter['place'] = tournament_results_df_iter['combined_place']
        
        tournament_results_df_iter['iteration_id'] = iter
        tournament_results_df = pd.concat([tournament_results_df, tournament_results_df_iter])

    return tournament_results_df[['iteration_id', 'team_id', 'team_name', 'started_rating', 'place']]

def get_multiverse_stat(multiverse_stat, place, normalize=1):
    """
    print multiverse heat map
    """

    normalized_value = np.max(multiverse_stat['iteration_id'] + 1)

    teams_ranks = multiverse_stat[['team_id', 'started_rating']].drop_duplicates()
    teams_ranks['true_place'] = teams_ranks['started_rating'].rank(method='dense', ascending=False).astype('int')
    teams_ranks = teams_ranks.sort_values(by='started_rating', ascending=False)

    multiverse_group = multiverse_stat.groupby(['team_id', 'team_name', 'started_rating', place]).agg(
        iterations = ('iteration_id', 'nunique'),
    ).reset_index()

    multiverse_pivot = multiverse_group.pivot_table(
                    index=['team_id', 'team_name', 'started_rating'], 
                    columns=place, 
                    values='iterations', 
                    fill_value=0
                                                     )#.reset_index()
    multiverse_pivot = multiverse_pivot.sort_values(by=['started_rating'], ascending=False)
    if normalize == 1:
        multiverse_pivot = multiverse_pivot / normalized_value
        font_style = ".0%"
    else:
        font_style = ".0f"

    plt.figure(figsize=(20, 20))
    sns.heatmap(multiverse_pivot, annot=True, fmt=font_style, cmap="crest") #, vmin=0, vmax=1)

    multiverse_group = multiverse_group.merge(teams_ranks[['team_id', 'true_place']], 'left', on='team_id')
    multiverse_group['weight'] = np.exp(1 / multiverse_group['true_place'])

    jystice_df = multiverse_group[multiverse_group[place] == multiverse_group['true_place']]
    jystice_df['value'] = jystice_df['iterations'] / normalized_value
    jystice_value = np.sum(jystice_df['value'] * jystice_df['weight']) / np.sum(jystice_df['weight'])
    print(jystice_value)

    return jystice_value, multiverse_pivot