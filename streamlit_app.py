from __future__ import annotations

from pathlib import Path

import streamlit as st

from reader.config import load_config
from reader.storage import connect, initialize, list_items, mark_read, set_rating


st.set_page_config(page_title="Reader", layout="wide")
st.title("Reader")

config_path = Path(st.sidebar.text_input("Config file", value="config.example.yaml"))
config = load_config(config_path)
initialize(config.database)

with connect(config.database) as connection:
    items = list_items(connection)

for item in items:
    with st.container(border=True):
        st.subheader(item["title"])
        st.caption(f"{item['source_name']} · {item['url']}")
        if item["summary"]:
            st.write(item["summary"])
        st.write(f"Status: {'Read' if item['read_at'] else 'Unread'}")
        st.write(f"Rating: {item['rating'] or 'None'}")
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