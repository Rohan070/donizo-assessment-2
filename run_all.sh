#!/bin/bash

cd donizo-material-scraper

# Start FastAPI (on port 8000) in the background
uvicorn apis.api:app --reload &
API_PID=$!

# Start Streamlit (on port 8501) in the foreground
streamlit run streamlit_app.py

# When Streamlit exits, kill the FastAPI server
kill $API_PID 