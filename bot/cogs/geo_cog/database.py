import sqlite3

CREATE_TABLE_QUERY = "CREATE TABLE IF NOT EXISTS leaderboard (id INTEGER PRIMARY_KEY, name TEXT, user_id INTEGER, rank INTEGER, score INTEGER);"

INSERT_QUERY = "INSERT INTO leaderboard (name, user_id, rank, score) values (?, ?, ?, ?);"

GET_ALL_MEMBERS = "SELECT * FROM leaderboard;"
GET_MEMBERS_BY_NAME = "SELECT * FROM leaderboard WHERE name = ?;"
GET_BEST_PREPARATION_FOR_MEMBER = """
                                    SELECT * FROM leaderboard
                                    WHERE user_id = ? 
                                    ORDER BY score DESC
                                    LIMIT 1;
                                  """

SORT_TOP10_BY_SCORE = """
                        SELECT * FROM leaderboard
                        ORDER BY score DESC
                        LIMIT 10;
                      """

UPDATE_SCORE = """
                UPDATE leaderboard
                SET score = ?
                WHERE user_id = ?;
               """

GET_USER_SCORE = """
                    SELECT score FROM leaderboard
                    WHERE user_id = ? 
                    LIMIT 1;
                """

def connect():
    return sqlite3.connect("bot/cogs/geo_cog/database.db")

def update_score(connection, score, user_id):
    with connection:
        return connection.execute(UPDATE_SCORE, (score, user_id,)).fetchone()

def sort_and_return(connection):
    with connection:
        return connection.execute(SORT_TOP10_BY_SCORE).fetchall()

def get_existing_score(connection, user_id):
    with connection:
        return connection.execute(GET_USER_SCORE, (user_id,)).fetchone()

def check_if_user_exists(connection, user_id):
    with connection:
        return connection.execute("SELECT COUNT(*) FROM leaderboard WHERE user_id = :userid", {"userid": user_id}).fetchall()

def create_tables(connection):
    with connection:
        connection.execute(CREATE_TABLE_QUERY)

def add_into(connection, name, user_id, rank, score):
    with connection:
        connection.execute(INSERT_QUERY, (name, user_id, rank, score))

def reset(connection, user_id):
    with connection:
        connection.execute('DELETE FROM leaderboard WHERE id = :uuu', {"uuu": user_id})

def get_all_members(connection):
    with connection:
        return connection.execute(GET_ALL_MEMBERS).fetchall()

def get_members_by_name(connection, name):
    with connection:
        return connection.execute(GET_MEMBERS_BY_NAME, (name,)).fetchall()

def get_best_preparation_for_member(connection, user_id):
    with connection:
        return connection.execute(GET_BEST_PREPARATION_FOR_MEMBER, (user_id,)).fetchone()