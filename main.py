import pandas as pd
import plotly.express as px

def group_by_unique_column(df: pd.DataFrame, column_name: str) -> list[pd.DataFrame]:
    """Return a list of DataFrames, one per unique column value.

    Each returned DataFrame contains all rows for a given column value and has its
    index reset. Groups are returned in ascending order of the column value.
    """
    if column_name not in df.columns:
        raise KeyError(f"Column '{column_name}' not found in dataframe")

    column_groups: list[pd.DataFrame] = []
    for _, group in df.groupby(column_name, sort=True, dropna=False):
        column_groups.append(group.reset_index(drop=True))

    return column_groups



def count_unique_sessions(user_df: pd.DataFrame) -> int:
    return len(set(user_df['session_id']))

def has_multiple_sessions(user_df: pd.DataFrame) -> bool:
    return count_unique_sessions(user_df) > 1


def partition(iterable, condition) -> tuple[list, list]:
    true_list, false_list = [], []
    for item in iterable:
        (true_list if condition(item) else false_list).append(item)
    return true_list, false_list


def print_extensive_user_stats(user_df: pd.DataFrame) -> None:
    print(f"User {user_df['user_id'].iloc[0]} has {len(user_df)} sessions")
    print(user_df[['user_id', 'session_id', 'path', 'css', 'text', 'value', 'event_time']])

def print_user_session(user_df: pd.DataFrame) -> None:
    print(f"User {user_df['user_id'].iloc[0]} has {len(user_df)} events")
    print(user_df[['path', 'css', 'text', 'value', 'event_time']])


def generate_cart_funnel(df: pd.DataFrame, output_html: str = "funnel.html") -> None:
    """Generate a cart funnel visualization across sessions and save as HTML.

    Stages are computed on unique sessions and constrained cumulatively to form a
    monotonically decreasing funnel.
    """
    sessions_with_product_view = set(
        df[df["path"].str.startswith("/products", na=False)]["session_id"].astype(str)
    )
    sessions_with_add_to_cart = set(
        df[df["css"] == "button.add-to-cart"]["session_id"].astype(str)
    )
    sessions_with_view_cart = set(
        df[(df["path"] == "/cart") & (df["css"] == "button.checkout")]["session_id"].astype(str)
    )
    sessions_with_checkout = set(
        df[df["path"] == "/checkout"]["session_id"].astype(str)
    )
    sessions_with_order_placed = set(
        df[(df["path"] == "/checkout") & (df["css"] == "button.place-order")]["session_id"].astype(str)
    )

    viewed = sessions_with_product_view
    added = viewed & sessions_with_add_to_cart
    cart = added & sessions_with_view_cart
    checkout = cart & sessions_with_checkout
    placed = checkout & sessions_with_order_placed

    funnel_df = pd.DataFrame(
        {
            "stage": [
                "Viewed Product",
                "Added to Cart",
                "Viewed Cart",
                "Checkout Started",
                "Order Placed",
            ],
            "count": [
                len(viewed),
                len(added),
                len(cart),
                len(checkout),
                len(placed),
            ],
        }
    )

    fig = px.funnel(funnel_df, y="stage", x="count", title="Cart Funnel")
    fig.write_html(output_html, include_plotlyjs="cdn")
    print(f"Funnel visualization saved to {output_html}")


def _classify_checkout_drop_reason(session_df: pd.DataFrame) -> str:
    """Return a single primary reason for dropping at checkout for a session.

    Priority order: Cancelled > Payment error > Out of stock > Empty cart > Other error
    """
    # Normalize helper columns
    text_values = (session_df["text"].dropna().astype(str).str.lower().tolist())
    css_values = (session_df["css"].dropna().astype(str).str.lower().tolist())

    if any("button.cancel-order" in css for css in css_values) or any("cancel order" in t for t in text_values):
        return "Cancelled"

    if any("payment" in t and ("error" in t or "declined" in t or "unavailable" in t or "timeout" in t)
           for t in text_values):
        return "Payment error"

    if any("out of stock" in t for t in text_values):
        return "Out of stock"

    if any("no items in cart" in t or "cart is empty" in t for t in text_values):
        return "Empty cart"

    if any("error" in t for t in text_values):
        return "Other error"

    return "Unknown"


def generate_funnel_loss_reason_chart(df: pd.DataFrame, output_html: str = "funnel_loss_reasons.html") -> None:
    """Generate a stacked bar chart of primary loss reasons per funnel transition.

    Transitions:
      - Product → Add to Cart
      - Add to Cart → View Cart
      - Checkout Started → Order Placed
    """
    # Compute session cohorts for each stage
    sessions_with_product_view = set(
        df[df["path"].str.startswith("/products", na=False)]["session_id"].astype(str)
    )
    sessions_with_add_to_cart = set(
        df[df["css"] == "button.add-to-cart"]["session_id"].astype(str)
    )
    sessions_with_view_cart = set(
        df[(df["path"] == "/cart") & (df["css"] == "button.checkout")]["session_id"].astype(str)
    )
    sessions_with_checkout = set(
        df[df["path"] == "/checkout"]["session_id"].astype(str)
    )
    sessions_with_order_placed = set(
        df[(df["path"] == "/checkout") & (df["css"] == "button.place-order")]["session_id"].astype(str)
    )

    # Transitions and drop sets
    drop_prod_to_cart = sessions_with_product_view - sessions_with_add_to_cart
    drop_cart_to_view = sessions_with_add_to_cart - sessions_with_view_cart
    drop_checkout_to_order = sessions_with_checkout - sessions_with_order_placed

    # Build reason counts
    records: list[dict] = []

    # Product → Cart: no explicit signals in data; mark generic
    if drop_prod_to_cart:
        records.append({
            "transition": "Product → Cart",
            "reason": "No add to cart",
            "count": len(drop_prod_to_cart),
        })

    # Add to Cart → View Cart: generic
    if drop_cart_to_view:
        records.append({
            "transition": "Cart → Checkout",
            "reason": "No cart view",
            "count": len(drop_cart_to_view),
        })

    # Checkout → Order Placed: classify by session events
    if drop_checkout_to_order:
        for session_id in drop_checkout_to_order:
            session_df = df[df["session_id"].astype(str) == session_id]
            reason = _classify_checkout_drop_reason(session_df)
            records.append({
                "transition": "Checkout → Order",
                "reason": reason,
                "count": 1,
            })

    if not records:
        print("No drop-offs detected; skipping loss reason chart.")
        return

    reasons_df = pd.DataFrame.from_records(records)
    agg_df = reasons_df.groupby(["transition", "reason"], as_index=False)["count"].sum()

    fig = px.bar(
        agg_df,
        x="transition",
        y="count",
        color="reason",
        barmode="stack",
        title="Funnel Drop-off Reasons by Transition",
    )
    fig.write_html(output_html, include_plotlyjs="cdn")
    print(f"Loss reasons chart saved to {output_html}")

def main():
    df = pd.read_json('sessions.json', lines=True)
    user_groups = group_by_unique_column(df, 'user_id')
    print(f"Number of users: {len(user_groups)}")
    # for i, user_df in enumerate(user_groups, 1):
    #     print(f"\nUser {i} ({len(user_df)} events):")
    #     print(user_df[['user_id', 'session_id', 'path', 'css', 'text', 'value', 'event_time']])

    users_with_multiple_sessions, users_with_single_session = partition(user_groups, has_multiple_sessions)
    print(f"Number of users with multiple sessions: {len(users_with_multiple_sessions)}")
    print(f"Number of users with single session: {len(users_with_single_session)}")

    for user_df in users_with_multiple_sessions[0:1]:
        sessions = group_by_unique_column(user_df, 'session_id')
        for session in sessions:
            print_user_session(session)

    # Generate overall cart funnel across all sessions
    generate_cart_funnel(df, output_html="funnel.html")
    generate_funnel_loss_reason_chart(df, output_html="funnel_loss_reasons.html")



if __name__ == "__main__":
    main()

