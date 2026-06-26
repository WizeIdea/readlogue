from __future__ import annotations

from pathlib import Path

import streamlit as st

from reader.config import load_config
from reader.storage import connect, initialize, list_items_page, mark_read, set_category, set_rating


st.set_page_config(page_title="Reader", layout="wide")
st.title("Reader")

config_path = Path(st.sidebar.text_input("Config file", value="config.example.yaml"))
config = load_config(config_path)
initialize(config.database)

# Pagination state
PAGE_SIZE = 25
if "page" not in st.session_state:
    st.session_state.page = 0

st.sidebar.header("Navigation")
st.sidebar.write(f"Page size: {PAGE_SIZE}")
st.sidebar.write(f"Items per page: {PAGE_SIZE}")

with connect(config.database) as connection:
    items, total_items = list_items_page(connection, offset=st.session_state.page * PAGE_SIZE, limit=PAGE_SIZE)

total_pages = max(0, (total_items - 1) // PAGE_SIZE) if total_items > 0 else 0


def _apply_category_change(database: Path, item_id: int, select_key: str) -> None:
    selected_category = st.session_state[select_key]
    category_value = None if selected_category == "Uncategorized" else selected_category
    with connect(database) as connection:
        set_category(connection, item_id, category_value)
        connection.commit()


def _go_prev() -> None:
    if st.session_state.page > 0:
        st.session_state.page -= 1


def _go_next() -> None:
    if st.session_state.page < total_pages:
        st.session_state.page += 1


category_options = ["Uncategorized", *[category for category in config.categories if category != "Uncategorized"]]

for item in items:
    with st.container(border=True):
        st.subheader(item["title"])
        st.caption(f"{item['source_name']} · {item['url']}")
        if item["summary"]:
            st.write(item["summary"])
        st.write(f"Status: {'Read' if item['read_at'] else 'Unread'}")
        st.write(f"Rating: {item['rating'] or 'None'}")
        st.write(f"Source category: {item['source_category'] or 'Unknown'}")
        st.write(f"Category: {item['category'] or 'Uncategorized'}")
        category_key = f"category-{item['id']}"
        current_category = item["category"] or "Uncategorized"
        if current_category not in category_options:
            category_options = [current_category, *category_options]
        st.selectbox(
            "Category",
            category_options,
            index=category_options.index(current_category),
            key=category_key,
            on_change=_apply_category_change,
            args=(config.database, int(item["id"]), category_key),
            label_visibility="collapsed",
        )
        col1, col2, col3, col4 = st.columns(4)
        if col1.button("Mark read", key=f"read-{item['id']}"):
            with connect(config.database) as connection:
                mark_read(connection, int(item["id"]), True)
                connection.commit()
            st.rerun()
        if col2.button("Mark unread", key=f"unread-{item['id']}"):
            with connect(config.database) as connection:
                mark_read(connection, int(item["id"]), False)
                connection.commit()
            st.rerun()
        if col3.button("Like", key=f"like-{item['id']}"):
            with connect(config.database) as connection:
                set_rating(connection, int(item["id"]), "like")
                connection.commit()
            st.rerun()
        if col4.button("Dislike", key=f"dislike-{item['id']}"):
            with connect(config.database) as connection:
                set_rating(connection, int(item["id"]), "dislike")
                connection.commit()
            st.rerun()

# Pagination controls
st.divider()
col_prev, col_info, col_next = st.columns([1, 2, 1])
with col_prev:
    st.button("← Previous", on_click=_go_prev, disabled=st.session_state.page <= 0, use_container_width=True)
with col_info:
    st.markdown(
        f"<p style='text-align: center; margin-top: 4px;'>"
        f"Page {st.session_state.page + 1} of {total_pages + 1} ({total_items} total articles)</p>",
        unsafe_allow_html=True,
    )
with col_next:
    st.button("Next →", on_click=_go_next, disabled=st.session_state.page >= total_pages, use_container_width=True)
