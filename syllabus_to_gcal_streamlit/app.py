import streamlit as st
import pandas as pd
from pipeline import process_pdf_and_generate_csv

st.set_page_config(page_title="📚 Syllabus Calendar Converter", layout="centered")
st.title(":books: Syllabus Calendar Converter")

openai_key = st.secrets["OPENAI_API_KEY"]

password = st.text_input("Enter access code", type="password")
if password != st.secrets["APP_PASSWORD"]:
    st.warning("Unauthorized access. Please enter the correct password.")
    st.stop()

st.markdown("Upload a syllabus PDF and generate a calendar-friendly CSV of all deliverables.")
uploaded_file = st.file_uploader(":page_facing_up: Upload your syllabus (.pdf)", type="pdf")
course_name = st.text_input("Course Name")
user_note = st.text_area(":memo: Notes about the syllabus format (optional)")

model_name = st.radio(
    "Choose GPT model for extraction:",
    ["gpt-3.5-turbo", "gpt-4o"],
    help="gpt-3.5-turbo is faster and cheaper; gpt-4o may be more accurate"
)

if uploaded_file:
    st.info(":hourglass: File uploaded. Ready to process?")
    
    if st.button("🚀 Process Syllabus"):
        with st.spinner("Processing your syllabus..."):
            df = process_pdf_and_generate_csv(uploaded_file, course_name, user_note, openai_key, model_name)

        if not df.empty:
            st.success(":white_check_mark: Success! Your CSV is ready.")
            st.dataframe(df)

            csv_bytes = df.to_csv(index=False).encode('utf-8')

            st.download_button(
                label=":inbox_tray: Download Calendar CSV",
                data=csv_bytes,
                file_name="syllabus_calendar.csv",
                mime="text/csv",
                help="Click to download. Check your browser's Downloads folder."
            )

            st.subheader(":calendar: Upload to Google Calendar")
            st.markdown("""
            1. Open [Google Calendar](https://calendar.google.com)
            2. Click the ⚙️ gear icon → **Settings**
            3. Go to **Import & Export**
            4. Choose your downloaded `syllabus_calendar.csv`
            5. Pick a calendar to import to
            6. Click **Import**
            """)
        else:
            st.error(":warning: No assignments found. Try another syllabus or check formatting.")

