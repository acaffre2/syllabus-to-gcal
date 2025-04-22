# 🗓️ Syllabus-to-Calendar Dashboard

This is a Streamlit web app that extracts assignments, exams, readings, and other deliverables from a college course syllabus in PDF format and converts them into a downloadable Google Calendar-compatible CSV file.

## 🚀 Try the App
Once deployed to Streamlit Cloud, you can upload your syllabus and get a ready-to-import calendar of due dates and assignments.

## 📂 How to Use
1. Upload a syllabus PDF using the upload box.
2. Enter the course name — this will be used to label each calendar event.
3. Optionally describe how the syllabus is structured to guide the model.
4. Click **Process Syllabus** to generate your calendar.
5. Preview the results and download your CSV!

## 💡 What It Does
- Extracts text and tables from syllabi (even if they span multiple pages)
- Filters for chunks likely to contain assignment dates
- Uses semantic search (FAISS) and GPT-4o to interpret due dates
- Deduplicates overlapping events
- Returns a clean, 8-column CSV ready for Google Calendar

## 🛠️ Built With
- [Streamlit](https://streamlit.io)
- [pdfplumber](https://github.com/jsvine/pdfplumber)
- [sentence-transformers](https://www.sbert.net/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [OpenAI API](https://platform.openai.com)
- [tiktoken](https://github.com/openai/tiktoken)

## 🔐 Security
This app uses a secure environment variable (`OPENAI_API_KEY`) managed via Streamlit Secrets. Your key is never stored in the code or uploaded.

## 📎 For Educators
This project was developed for a class project to demonstrate the potential of combining NLP with course organization tools. Feedback welcome!
