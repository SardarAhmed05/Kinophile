# Kinophile

A personalized film recommendation app powered by AI.

## What it does

Kinophile analyzes your cinematic taste based on films you love and recommends new ones you'll genuinely connect with. No generic suggestions, every recommendation comes with a detailed explanation of why it fits your taste.

## How it works

Three-layer pipeline:
1. **AI** — analyzes your favourite films and generates recommendations
2. **TMDB + OMDB** — validates every recommended film with real data (ratings, director, year, poster)
3. **AI** — writes personalized explanations using only verified facts

## Features

- Add your favourite films one by one
- Get 1-10 personalized recommendations
- Film cards with real posters, IMDB ratings, director, and year
- Per-film explanations — click any film to understand why it was recommended
- Direct IMDB links for each recommendation
- Chat with KinoBOT — ask anything about cinema, recommendations, or directors
- Web search integration — KinoBOT can find current film information
- Session history — recommendations don't repeat across sessions

## Stack

- Python
- Streamlit
- Groq API (LLM)
- TMDB API (film data)
- OMDB API (IMDB ratings)
- Tavily (web search)
- aiohttp + asyncio (parallel API calls)

## Run locally

1. Clone the repo
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Create `.streamlit/secrets.toml`:
```toml
GROQ_API_KEY = "your_key"
TMDB_API_KEY = "your_key"
OMDB_API_KEY = "your_key"
TAVILY_API_KEY = "your_key"
```
4. Run:
```bash
streamlit run app.py
```

## Live demo

[kinophile.streamlit.app](https://kinophile.streamlit.app)
