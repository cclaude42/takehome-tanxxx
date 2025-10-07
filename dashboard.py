import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go


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

    fig = px.funnel(funnel_df, y="stage", x="count", title="User funnel")

    # Make text black and remove hover tooltips
    fig.update_traces(
        textfont_color="black",
        hovertemplate=None,
        hoverinfo="skip"
    )
    
    return fig


def _display_stage_details(df: pd.DataFrame, stage_name: str, sessions_in_stage: set, sessions_moved_next: set):
    """Display detailed information for a funnel stage."""
    total = len(sessions_in_stage)
    moved_next = len(sessions_moved_next)
    dropped = total - moved_next
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total sessions at this step", total)
    with col2:
        st.metric("Moved forward", moved_next)
    with col3:
        st.metric("Dropped here", dropped)
    
    if dropped > 0:
        dropped_sessions = sessions_in_stage - sessions_moved_next

        key_base = f"peek_{stage_name.replace(' ', '_').lower()}"
        index_key = f"{key_base}_idx"
        if index_key not in st.session_state:
            st.session_state[index_key] = 0

        ordered_sessions = sorted(list(dropped_sessions))
        total_sessions = len(ordered_sessions)
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
    st.set_page_config(page_title="User journey dashboard", layout="wide")
    st.title("User journey dashboard")
    st.caption("A quick read on where shoppers move forward and where they drop out.")

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

    # Pages (tabs) for top-level navigation
    tabs = st.tabs(["User funnel", "Step details", "Customer insights"])

    # Precompute sessions once
    sessions = _get_funnel_sessions(df)

    # Page 1: Funnel
    with tabs[0]:
        st.subheader("How many users move through each step?")
        funnel_fig = _compute_funnel_fig(df)
        st.plotly_chart(funnel_fig)

    # Page 2: Step details
    with tabs[1]:
        st.subheader("Who moved forward and who didn't?")
        stage_options = [
            "Viewed Product",
            "Added to Cart",
            "Viewed Cart",
            "Checkout Started",
        ]
        selected_stage = st.selectbox("Which step do you want to inspect?", stage_options)
        if selected_stage:
            st.divider()
            _handle_stage_selection(df, selected_stage, sessions)

    # Page 3: Customer insights
    with tabs[2]:
        st.subheader("Why shoppers didn't complete their order")

        # Cohorts
        sessions_with_product_view = set(
            df[df["path"].str.startswith("/products", na=False)]["session_id"].astype(str)
        )
        sessions_with_order_placed = set(
            df[(df["path"] == "/checkout") & (df["css"] == "button.place-order")]["session_id"].astype(str)
        )
        viewed_not_placed = sessions_with_product_view - sessions_with_order_placed

        # Reason classifier per spec:
        # - Has error if ANY css contains 'div.error-message'
        # - Error uniqueness = combination of path and error message -> "/path - Error message"
        def classify_loss_reason(session_df: pd.DataFrame) -> str:
            # Ensure string dtype for checks
            session_df = session_df.copy()
            session_df["css"] = session_df["css"].astype(str)
            session_df["path"] = session_df["path"].astype(str)
            session_df["text"] = session_df["text"].astype(str)

            # Filter rows that display an error message
            error_rows = session_df[session_df["css"].str.contains("div.error-message", na=False)]

            if error_rows.empty:
                return "No error"

            # Use first occurrence (ordered by event_time if present)
            if "event_time" in error_rows.columns:
                try:
                    ordered = error_rows.sort_values("event_time")
                except Exception:
                    ordered = error_rows
            else:
                ordered = error_rows

            first = ordered.iloc[0]
            path = first.get("path", "/") or "/"
            message = first.get("text", "Error") or "Error"
            return f"{path} - {message}"

        records: list[dict] = []
        for session_id in viewed_not_placed:
            session_df = df[df["session_id"].astype(str) == session_id]
            reason = classify_loss_reason(session_df)
            records.append({"session_id": session_id, "reason": reason})

        if records:
            reasons_df = pd.DataFrame.from_records(records)
            agg_df = reasons_df.groupby("reason", as_index=False).size().rename(columns={"size": "count"})

            # Hoverable pie chart
            fig = px.pie(agg_df, values="count", names="reason", title="What stopped shoppers from completing checkout")
            fig.update_traces(textfont_color="black")
            st.plotly_chart(fig)

            # Selectable menu to explore a reason (including "No error") like in details page
            all_reasons_sorted = agg_df.sort_values("count", ascending=False)
            st.subheader("Explore a specific reason")
            if not all_reasons_sorted.empty:
                error_options = all_reasons_sorted["reason"].tolist()
                chosen_error = st.selectbox("Which reason do you want to inspect?", error_options, key="insights_error_select")
                if chosen_error:
                    st.divider()
                    # Sessions that match this error
                    matching_sessions = set(reasons_df[reasons_df["reason"] == chosen_error]["session_id"].astype(str))
                    total_matching = len(matching_sessions)
                    st.metric("Sessions with this reason", total_matching)

                    if total_matching > 0:
                        # Always show navigation and a single events table by default
                        key_base = f"insights_{chosen_error.replace(' ', '_').lower()}"
                        index_key = f"{key_base}_idx"
                        if index_key not in st.session_state:
                            st.session_state[index_key] = 0

                        ordered_sessions = sorted(list(matching_sessions))
                        total_sessions = len(ordered_sessions)
                        if total_sessions == 0:
                            st.info("No sessions to show.")
                        else:
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
                            )
            else:
                st.write("No errors detected among non-converting sessions.")
        else:
            st.info("No non-converting sessions found from product views.")



if __name__ == "__main__":
    main()

