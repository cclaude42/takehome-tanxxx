import pandas as pd


# Utils
def count_unique_sessions(user_df: pd.DataFrame) -> int:
    """Count unique session_id values in a user dataframe."""
    return len(set(user_df['session_id']))


def has_multiple_sessions(user_df: pd.DataFrame) -> bool:
    """Whether a user dataframe contains more than one unique session."""
    return count_unique_sessions(user_df) > 1


def partition(iterable, condition) -> tuple[list, list]:
    """Split an iterable into two lists based on a predicate.

    Returns (true_list, false_list).
    """
    true_list, false_list = [], []
    for item in iterable:
        (true_list if condition(item) else false_list).append(item)
    return true_list, false_list


def group_by_unique_column(df: pd.DataFrame, column_name: str) -> list[pd.DataFrame]:
    """Return list of dataframes, one per unique value in column_name (sorted)."""
    if column_name not in df.columns:
        raise KeyError(f"Column '{column_name}' not found in dataframe")

    column_groups: list[pd.DataFrame] = []
    for _, group in df.groupby(column_name, sort=True, dropna=False):
        column_groups.append(group.reset_index(drop=True))

    return column_groups


# Displaying data
def print_extensive_user_stats(user_df: pd.DataFrame) -> None:
    print(f"User {user_df['user_id'].iloc[0]} has {len(user_df)} sessions")
    print(user_df[['user_id', 'session_id', 'path', 'css', 'text', 'value', 'event_time']])


def print_user_session(user_df: pd.DataFrame) -> None:
    print(f"Session has {len(user_df)} events")
    print(user_df[['path', 'css', 'text', 'value', 'event_time']])
    print()


def main():
    df = pd.read_json('sessions.json', lines=True)
    user_groups = group_by_unique_column(df, 'user_id')
    print(f"Number of users: {len(user_groups)}")
    print()

    users_with_multiple_sessions, users_with_single_session = partition(user_groups, has_multiple_sessions)
    print(f"Number of users with multiple sessions: {len(users_with_multiple_sessions)}")
    print(f"Number of users with single session: {len(users_with_single_session)}")
    print()

    for user_df in users_with_multiple_sessions[0:1]:
        sessions = group_by_unique_column(user_df, 'session_id')
        for session in sessions:
            print_user_session(session)




if __name__ == "__main__":
    main()

