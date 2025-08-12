import streamlit as st
import pandas as pd
import re
from emoji import emoji_list
from collections import Counter
import seaborn as sns
import matplotlib.pyplot as plt

st.set_page_config(page_title="Emoji Frequency Counter", page_icon="📊", layout="wide")
st.title("📊 Emoji Frequency Counter")
st.write("Upload your WhatsApp or Telegram chat export to see your emoji trends!")

uploaded_file = st.file_uploader("Upload chat file (.txt or .json)", type=["txt", "json"])

def extract_emojis(text):
    return [e["emoji"] for e in emoji_list(text)]

def parse_whatsapp(lines):
    """
    Parse WhatsApp exported chat lines with this format:
    [DD.MM.YY, HH:MM:SS AM/PM] Sender: message
    """

    records = []
    # Regex explanation:
    # \[(.*?)\] captures everything inside the brackets (date and time)
    # Date format is DD.MM.YY, time is HH:MM:SS AM/PM (with some unicode spaces)
    # Sender: message separated by ': '
    pattern = re.compile(
        r"^\[(\d{1,2}\.\d{1,2}\.\d{2}), (\d{1,2}:\d{2}:\d{2}\s*[AP]M)\] (.*?): (.*)$"
    )

    for line in lines:
        match = pattern.match(line)
        if match:
            date_str, time_str, sender, message = match.groups()
            records.append((date_str, time_str, sender, message))
        else:
            # Could be system messages or multi-line messages, ignore or handle later
            continue

    if not records:
        return None

    df = pd.DataFrame(records, columns=["date", "time", "sender", "message"])

    # Parse date and time to datetime
    # Date format is DD.MM.YY
    df["datetime"] = pd.to_datetime(
        df["date"] + " " + df["time"],
        format="%d.%m.%y %I:%M:%S %p",
        errors="coerce",
    )

    return df

if uploaded_file:
    content = uploaded_file.read().decode("utf-8", errors="ignore")
    lines = content.splitlines()

    df = parse_whatsapp(lines)

    if df is None or df.empty:
        st.error("Couldn't parse the chat file. Make sure it's a WhatsApp export (text format) without media.")
    else:
        df["emojis"] = df["message"].apply(extract_emojis)

        # Top emojis
        all_emojis = [e for sublist in df["emojis"] for e in sublist]
        if not all_emojis:
            st.info("No emojis found in the chat.")
        else:
            emoji_counts = Counter(all_emojis).most_common(10)

            st.subheader("Top Emojis")
            st.dataframe(pd.DataFrame(emoji_counts, columns=["Emoji", "Count"]))

            # Trend chart
            emoji_df = df.explode("emojis").dropna(subset=["emojis"])
            emoji_df["date_only"] = emoji_df["datetime"].dt.date
            top_5 = [e for e, _ in emoji_counts[:5]]
            daily_counts = emoji_df.groupby(["date_only", "emojis"]).size().reset_index(name="count")
            daily_counts = daily_counts[daily_counts["emojis"].isin(top_5)]

            if not daily_counts.empty:
                plt.figure(figsize=(12,6))
                sns.lineplot(data=daily_counts, x="date_only", y="count", hue="emojis")
                plt.xticks(rotation=45)
                plt.title("Emoji usage over time")
                st.pyplot(plt)
            else:
                st.info("No emojis found to plot.")