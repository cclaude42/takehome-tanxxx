import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go

from main import generate_cart_funnel, generate_funnel_loss_reason_chart


def _get_funnel_sessions(df: pd.DataFrame):
    """Return session data for each funnel stage."""
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

    return {
        "viewed": viewed,
        "added": added,
        "cart": cart,
        "checkout": checkout,
        "placed": placed
    }


def _compute_funnel_fig(df: pd.DataFrame):
    """Return a Plotly funnel figure computed from the dataframe.

    This mirrors the logic inside generate_cart_funnel but returns the fig for Streamlit.
    """
    sessions = _get_funnel_sessions(df)
    
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
                len(sessions["viewed"]),
                len(sessions["added"]),
                len(sessions["cart"]),
                len(sessions["checkout"]),
                len(sessions["placed"]),
            ],
        }
    )

    fig = px.funnel(funnel_df, y="stage", x="count", title="Cart Funnel")
    
    # Make text black and remove hover tooltips
    fig.update_traces(
        textfont_color="black",
        hovertemplate=None,
        hoverinfo="skip"
    )
    
    return fig


def _display_stage_details(df: pd.DataFrame, stage_name: str, sessions_in_stage: set, sessions_moved_next: set):
    """Display detailed information for a funnel stage in language suited for product review."""
    total = len(sessions_in_stage)
    moved_next = len(sessions_moved_next)
    dropped = total - moved_next
    
    st.subheader(f"📊 {stage_name}: what happened here?")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total sessions at this step", total)
    with col2:
        st.metric("Moved forward", moved_next)
    with col3:
        st.metric("Dropped here", dropped)
    
    if dropped > 0:
        st.subheader("🔍 Who dropped and what they did")
        dropped_sessions = sessions_in_stage - sessions_moved_next
        
        # Show session IDs that dropped
        st.write(f"**Session IDs that did not move forward ({len(dropped_sessions)}):**")
        session_list = list(dropped_sessions)[:10]  # Show first 10
        for session_id in session_list:
            st.write(f"- {session_id}")
        
        if len(dropped_sessions) > 10:
            st.write(f"... and {len(dropped_sessions) - 10} more")
        
        # Show detailed events for dropped sessions (toggleable, single-table with navigation)
        key_base = f"peek_{stage_name.replace(' ', '_').lower()}"
        show_key = f"{key_base}_show"
        index_key = f"{key_base}_idx"

        if show_key not in st.session_state:
            st.session_state[show_key] = False
        if index_key not in st.session_state:
            st.session_state[index_key] = 0

        if st.button("📋 Peek at events for dropped sessions", key=f"btn_{key_base}"):
            st.session_state[show_key] = not st.session_state[show_key]

        if st.session_state[show_key]:
            ordered_sessions = sorted(list(dropped_sessions))
            total_sessions = len(ordered_sessions)
            # Clamp index in range
            if total_sessions == 0:
                st.info("No dropped sessions to show.")
            else:
                st.subheader("Event details for dropped sessions")
                nav_cols = st.columns([1, 4, 1])
                with nav_cols[0]:
                    if st.button("←", key=f"prev_{key_base}"):
                        st.session_state[index_key] = (st.session_state[index_key] - 1) % total_sessions
                with nav_cols[2]:
                    if st.button("→", key=f"next_{key_base}"):
                        st.session_state[index_key] = (st.session_state[index_key] + 1) % total_sessions

                current_idx = st.session_state[index_key] % total_sessions
                current_session_id = ordered_sessions[current_idx]
                with nav_cols[1]:
                    st.markdown(f"**Session {current_idx + 1} of {total_sessions}** — `{current_session_id}`")

                session_events = df[df["session_id"].astype(str) == current_session_id]
                st.dataframe(
                    session_events[["path", "css", "text", "value", "event_time"]].head(50),
                    use_container_width=True
                )


def _handle_stage_selection(df: pd.DataFrame, stage_name: str, sessions: dict):
    """Handle stage selection and display details."""
    # Map stage names to session sets
    stage_mapping = {
        "Viewed Product": ("viewed", "added"),
        "Added to Cart": ("added", "cart"),
        "Viewed Cart": ("cart", "checkout"),
        "Checkout Started": ("checkout", "placed"),
        "Order Placed": ("placed", set())  # No next stage
    }
    
    if stage_name in stage_mapping:
        current_stage, next_stage = stage_mapping[stage_name]
        sessions_in_stage = sessions[current_stage]
        sessions_moved_next = sessions[next_stage] if next_stage else set()
        
        _display_stage_details(df, stage_name, sessions_in_stage, sessions_moved_next)


def main():
    st.set_page_config(page_title="Shopping journey funnel", layout="wide")
    st.title("Shopping journey funnel")
    st.caption("A quick read on where shoppers move forward and where they drop.")

    # Styling: make the selector feel clickable and on-brand (blue), pointer cursor on hover
    st.markdown(
        """
        <style>
        /* Pointer cursor for the select control */
        div[data-baseweb="select"] > div { cursor: pointer; }
        /* Hover/focus ring in brand blue */
        div[data-baseweb="select"] > div:hover { border-color: #636efa !important; }
        div[data-baseweb="select"] > div:focus, div[data-baseweb="select"] > div:focus-within {
            box-shadow: 0 0 0 2px rgba(99,110,250,0.3) !important;
            border-color: #636efa !important;
        }
        /* Selected option and hover inside dropdown */
        ul[role="listbox"] li[aria-selected="true"] { background-color: rgba(99,110,250,0.12) !important; color: #1f1f1f !important; }
        ul[role="listbox"] li:hover { background-color: rgba(99,110,250,0.18) !important; cursor: pointer; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar controls
    st.sidebar.header("Controls")
    data_file = st.sidebar.text_input("Data file", value="sessions.json")
    lines_json = st.sidebar.checkbox("File is JSON Lines (one JSON per line)", value=True)

    # Load data
    try:
        if lines_json:
            df = pd.read_json(data_file, lines=True)
        else:
            df = pd.read_json(data_file)
    except Exception as e:
        st.error(f"Failed to load data from '{data_file}': {e}")
        return

    # Base view: Funnel first
    st.subheader("Cart funnel")
    funnel_fig = _compute_funnel_fig(df)
    st.plotly_chart(funnel_fig, use_container_width=True)

    # Then: stage selection menu
    st.subheader("Dig into a step")
    st.caption("Pick a step to see who moved forward and who didn’t.")
    sessions = _get_funnel_sessions(df)
    stage_options = [
        "Viewed Product",
        "Added to Cart",
        "Viewed Cart",
        "Checkout Started",
        "Order Placed",
    ]
    selected_stage = st.selectbox("Which step do you want to inspect?", stage_options)

    # Finally: details for the chosen step
    if selected_stage:
        st.divider()
        _handle_stage_selection(df, selected_stage, sessions)



if __name__ == "__main__":
    main()


