
import os
import io
import csv
import re
import pdfplumber
import pandas as pd
import faiss
import tiktoken
from openai import OpenAI
import openai
from datetime import datetime
import numpy as np

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_openai_embeddings(texts, openai_key, model="text-embedding-3-small"):
    client = OpenAI(api_key=openai_key)
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]
    
def extract_text_and_tables_flex(file_obj):
    combined_text = ""
    all_table_rows = []

    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                combined_text += f"\n{text.strip()}\n"
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if any(cell and cell.strip() for cell in row):
                        row_text = ", ".join([cell.strip() if cell else "" for cell in row])
                        all_table_rows.append(row_text)

    if all_table_rows:
        table_text = "[TABLE START]\n" + "\n".join(all_table_rows) + "\n[TABLE END]\n"
        combined_text += "\n--- Combined Table Block ---\n" + table_text

    return combined_text

def chunk_text(text):
    paragraphs = text.split('\n\n')
    return [p.strip() for p in paragraphs if p.strip()]

def contains_date_info(text):
    return bool(re.search(
        r'\b(due|exam|test|quiz|paper|project|assignment|submit|submission|by|read|reading|chapter|[A-Z][a-z]{2,8} \d{1,2}|on \d{1,2}/\d{1,2})\b',
        text, re.IGNORECASE
    ))

def is_valid_year(date_str, allowed_year_str):
    try:
        allowed_year = int(allowed_year_str)
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return dt.year == allowed_year
    except:
        return False

def count_tokens(text, tokenizer):
    return len(tokenizer.encode(text))

def batch_chunks_token_based(chunks, tokenizer, max_tokens=6000, overlap=1):
    batches = []
    current_batch = []
    current_tokens = 0
    i = 0
    while i < len(chunks):
        chunk = chunks[i]
        chunk_tokens = count_tokens(chunk, tokenizer)
        if current_tokens + chunk_tokens <= max_tokens:
            current_batch.append(chunk)
            current_tokens += chunk_tokens
            i += 1
        else:
            if current_batch:
                batches.append("\n\n".join(current_batch))
            i = max(0, i - overlap)
            current_batch = []
            current_tokens = 0
    if current_batch:
        batches.append("\n\n".join(current_batch))
    return batches

def normalize_row(row):
    subject = re.sub(r'[\s\W_]+', '', row[0].strip().lower())
    start_date = row[1].strip()
    return (subject, start_date)

def query_gpt(prompt, model):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert at extracting structured calendar events from academic syllabi. Follow the user instructions exactly."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

def process_pdf_and_generate_csv(file_obj, course_name, user_comment, openai_key, model_name="gpt-3.5-turbo", allowed_year="2025"):
    raw_text = extract_text_and_tables_flex(file_obj)
    all_chunks = chunk_text(raw_text)
    date_chunks = [chunk for chunk in all_chunks if contains_date_info(chunk)]
    
    embeddings = get_openai_embeddings(date_chunks, openai_key)

    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings).astype("float32"))


    query = "Find any assignments, readings, quizzes, presentations, projects, or exams with specific due dates."
    query_embedding = np.array(get_openai_embeddings([query], openai_key)).astype("float32")
    D, I = index.search(query_embedding, k=10)
    relevant_chunks = [date_chunks[i] for i in I[0]]

    tokenizer = tiktoken.encoding_for_model(model_name)
    batched_chunks = batch_chunks_token_based(relevant_chunks, tokenizer)

    base_prompt = f"""You are helping convert a college course syllabus into Google Calendar assignments.

Here is a bit of information about the PDF's format: {user_comment}

You are also given excerpts from the syllabus, including some text blocks and tables marked with [TABLE START] and [TABLE END].

Extract any deliverables that have due dates — including assignments, readings, quizzes, presentations, projects, or exams.

Format your output as a CSV with the following columns:
Subject, Start Date, Start Time, End Date, End Time, All Day Event, Description, Location.

• Use the course name "{course_name}" as the prefix for every Subject (e.g., "{course_name}: Homework 1")
• Use the Description column to describe the assignment, reading, or quiz
• Leave the Location column blank unless an exam location is explicitly provided
• Only include deliverables with specific due dates
• If no time is listed, classify it as an all day event
• If no end time is listed, make it 30 minutes after the start time
• Use {allowed_year} as the year for the date.
• If any field contains a comma, enclose it in double quotes
• If any two items have the same date and describe the same general task (even if the title or wording is slightly different), treat them as duplicates and only include one.

Return only the CSV — no extra explanation.
"""

    all_rows_by_key = {}
    column_names = ("Subject", "Start Date", "Start Time", "End Date", "End Time", "All Day Event", "Description", "Location")

    for i, batch in enumerate(batched_chunks):
        full_prompt = f"{base_prompt}\n\n{batch}"
        response = query_gpt(full_prompt, model_name)
        try:
            f = io.StringIO(response)
            reader = csv.reader(f)
            headers = next(reader, None)
            for row in reader:
                if len(row) >= 2 and tuple(row) != column_names:
                    row_key = normalize_row(row)
                    if row_key not in all_rows_by_key or len("".join(row)) > len("".join(all_rows_by_key[row_key])):
                        all_rows_by_key[row_key] = tuple(row)
        except Exception as e:
            print(f"Error parsing GPT output batch {i + 1}: {e}")
            print("Raw output:\n", response)
            
    
    expected_col_count = len(column_names)
    clean_rows = []
    skipped_count = 0
    
    for row in all_rows_by_key.values():
        if len(row) == expected_col_count and is_valid_year(row[1], allowed_year):
            clean_rows.append(row)
        else:
            skipped_count += 1
    
    if not clean_rows:
        return pd.DataFrame(columns=column_names)
    
    return pd.DataFrame(clean_rows, columns=column_names)
