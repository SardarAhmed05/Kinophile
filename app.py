import requests
import time
from dotenv import load_dotenv
import os
import json
import streamlit as st
import aiohttp
import asyncio
from tavily import TavilyClient
import concurrent.futures

api_key = st.secrets["GROQ_API_KEY"]
tmdb_api = st.secrets["TMDB_API_KEY"]
omdb_api = st.secrets["OMDB_API_KEY"]
tavily_api = st.secrets["TAVILY_API_KEY"]

url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

def run_async(coro):
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()

def title_generation_prompt(num_recs, movies, previous=[]):
    avoid = f"\nAlso do NOT recommend these previously recommended films: {previous}" if previous else ""
    return f"""
    You are a world-class film recommendation expert.
    
    The user's favourite films are: {movies}
    
    Analyze their cinematic taste by inferring:
    - Favorite genres and themes
    - Emotional tone and pacing preferences
    - Cinematography and visual style
    - Recurring character archetypes
    - Tolerance for ambiguity
    - Appreciation for international or arthouse cinema
    
    Based on this analysis, recommend exactly {num_recs} NEW films.
    STRICTLY FORBIDDEN - do NOT recommend ANY of these films under any circumstances:
    Favourite films: {movies}
    Previously recommended: {previous}
    Prioritize thoughtful, insightful recommendations over obvious choices.
    Balance acclaimed classics with lesser-known gems.
    Do NOT ask questions. Always return recommendations.
    
    Return ONLY this JSON format, nothing else:
    {{"titles": ["Movie1", "Movie2", "Movie3"]}}
    You MUST recommend exactly {num_recs} films. Count carefully.
    """

def explanation_prompt():
    return """
    You are Kinophile, an expert film critic and recommendation analyst with deep knowledge of world cinema.

    Your job is to explain WHY each recommended film is a great match for the user's taste.

    You will receive:
    - The user's favourite films (with verified metadata)
    - A list of recommended films (with verified metadata)

    STRICT RULES

    - Use ONLY the information provided.
    - Never invent directors, release years, genres, ratings, awards, themes, actors, or plot details.
    - Never recommend movies outside the provided recommendations.
    - Do not compare a recommendation to a favourite film unless that favourite was provided.
    - Every factual statement must come from the supplied metadata or from safe high-level analysis of the recommendation.

    WRITING STYLE

    Write like an experienced movie analyst from Letterboxd or a respected film magazine.

    The writing should be:
    - Intelligent but easy to understand
    - Warm and engaging
    - Natural and conversational
    - Insightful without sounding academic
    - Passionate about cinema without being overly dramatic

    Avoid:
    - Generic praise like "masterpiece" or "must-watch"
    - Empty buzzwords
    - Repeating the same sentence structure
    - Overly poetic language
    - Long plot summaries
    - Bullet points
    - Lists

    STRUCTURE

    Every explanation should naturally follow this flow:

    1. Begin with a short introduction.

    Example style:
    "<Movie> (YEAR), directed by <DIRECTOR>, is a <GENRE> that..."

    Never force this exact wording, but always introduce the film using the verified metadata.

    2. Explain why it matches the user's taste.

    Discuss elements such as:
    - themes
    - atmosphere
    - tone
    - pacing
    - emotional impact
    - character writing
    - storytelling style
    - world-building
    - tension
    - humor
    - philosophy
    - visual style

    Only mention aspects supported by the supplied information.

    3. Connect it to one or more of the user's favourite films.

    Explain WHY they are similar.

    Good comparisons:
    - emotional weight
    - moral ambiguity
    - psychological depth
    - slow-burn storytelling
    - character-driven narrative
    - epic scale
    - bleak atmosphere
    - dialogue
    - mystery
    - cinematic style

    Do NOT simply say:
    "If you liked X, you'll like Y."

    Explain the connection.

    4. Finish with one sentence describing what makes the recommendation unique compared to the user's favourites.

    LENGTH

    Each explanation should be approximately 120–180 words.

    OUTPUT

    Return ONLY valid JSON.

    Example:

    {
    "Movie Title": "Explanation...",
    "Movie Title 2": "Explanation..."
    }

    Return no markdown.
    Return no code fences.
    Return no additional text.
"""

def generate_titles(num_recs, movies, previous=[]):
    for attempt in range(3):
        messages = [{"role": "system", "content": title_generation_prompt(num_recs, movies, previous)}]
        try:
            response = requests.post(url, headers=headers, json={
                "model": "openai/gpt-oss-20b",
                "messages": messages,
                "temperature": 0.7
            })
            print("STATUS:", response.status_code)
            print("CONTENT:", response.text)
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            titles = json.loads(content.strip())
            return titles["titles"]
        except:
            continue
    return []

async def validate_movie(title):
    title = title.strip().lower()

    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "query": title,
        "api_key": tmdb_api,
        "language": "en-US",
        "page": 1
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status != 200:
                return None

            data = await response.json()
            results = data.get("results", [])

            if not results:
                return None

            return results[0]

async def get_movie_details(tmdb_id):
    tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    tmdb_params = {"api_key" : tmdb_api}
    async with aiohttp.ClientSession() as session:
        async with session.get(tmdb_url, params=tmdb_params) as tmdb_response:
            tmdb_data = await tmdb_response.json()
            imdb_id = tmdb_data.get("imdb_id")
            poster_path = tmdb_data.get("poster_path", "")
            if not imdb_id:
                return None

        omdb_url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={omdb_api}"
        async with session.get(omdb_url) as response:
            result = await response.json()
            movie_title = result.get("Title", "N/A")
            release_year = result.get("Year", "N/A")
            imdb_rating = result.get("imdbRating", "N/A")
            director = result.get("Director", "N/A")

    return {
        "title": movie_title,
        "release_year": release_year,
        "imdb_rating": imdb_rating,
        "director": director,
        "poster": f"https://image.tmdb.org/t/p/w500{poster_path}"
    }

async def enrich_recommendations(rec_movies):
    async def process_movie(title):
        title = title.strip().lower()
        movie = await validate_movie(title)
        if movie:
            details = await get_movie_details(movie['id'])
            return details
        else:
            return None
        
    results = await asyncio.gather(*[process_movie(title) for title in rec_movies])
    return [r for r in results if r is not None]

@st.cache_data
def generate_explanations(user_movies, enriched_movies):
    for attempt in range(5):
        messages = [
            {"role": "system", "content" : explanation_prompt()}
        ]
        user_message = f"User's favourite films with verified data: {user_movies}\n\nRecommended films with verified data: {enriched_movies}"
        messages.append({"role": "user", "content": user_message})
        response = requests.post(url, headers=headers, json={"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": 0.4 })
        try:
            content = response.json()["choices"][0]["message"]["content"]
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content.strip())
        except:
            continue
            
    return {}

def chat_agent(messages):
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Search the web for current information about movies, directors, actors, or any film-related query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    
    response = requests.post(url, headers=headers, json={
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.5,
        "tools": tools
    })
    
    data = response.json()
    message = data["choices"][0]["message"]
    
    if message.get("tool_calls"):
        tool_call = message["tool_calls"][0]
        query = json.loads(tool_call["function"]["arguments"])["query"]
        search_results = search_web(query)
        
        clean_message = {
            "role": message["role"],
            "tool_calls": message["tool_calls"]
        }
        messages.append(clean_message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": str(search_results)
        })
        
        final_response = requests.post(url, headers=headers, json={
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": 0.5
        })
        final_data = final_response.json()
        if "choices" not in final_data:
            return "Sorry, something went wrong with the search."
        return final_data["choices"][0]["message"]["content"]

    else:
        return message["content"]
    
def search_web(query):
    client = TavilyClient(api_key=tavily_api)
    results = client.search(query=query, max_results=3)
    return results

st.set_page_config(
    page_title="Kinophile",
    page_icon="🎬",
    layout="wide"
)

st.markdown("""
    <style>
    .stApp {
        background-color: #0f0f0f;
        color: #e8e8e8;
    }
    [data-testid="stSidebar"] {
        padding: 0;
    }
    [data-testid="stSidebarContent"] {
        padding: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Kinophile")
st.caption("Your personal cinema recommendation expert")

if "movies" not in st.session_state:
    st.session_state.movies = []

if "messages" not in st.session_state:
    st.session_state.messages = []

if "recommendations_made" not in st.session_state:
    st.session_state.recommendations_made = False

if "enriched" not in st.session_state:
    st.session_state.enriched = []

if "last_response" not in st.session_state:
    st.session_state.last_response = ""

if "explanations" not in st.session_state:
    st.session_state.explanations = {}

if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None

if not st.session_state.messages:
    st.session_state.messages = [
        {"role": "system", "content": f"""You are Kinophile, a cinema expert assistant.
    Be conversational and brief. Only elaborate when the user specifically asks.
    If the user says hi or hey, just greet them back simply.
    The user's favourites: {st.session_state.movies}
    Recommended films: {[m['title'] for m in st.session_state.enriched]}"""}
    ]

if "previous_recommendations" not in st.session_state:
    st.session_state.previous_recommendations = []

# KINO BOT

with st.sidebar:
    st.title("💬 Chat with KinoBOT")
    st.caption("Ask anything about the recommendations")
    
    for message in st.session_state.messages:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(message["content"])
        elif message["role"] == "assistant":
            if message.get("content"):
                with st.chat_message("assistant"):
                    st.markdown(message["content"])
    
    if prompt := st.chat_input("Ask Kinophile anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("Thinking..."):
            reply = chat_agent(st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()

st.divider()
st.subheader("🎬 Movies you love")

with st.form(key="movie_form", clear_on_submit=True):
    col1, col2 = st.columns([4, 1])
    with col1:
        movie_input = st.text_input("Enter a movie title", label_visibility="collapsed", placeholder="e.g. Blade Runner 2049")
    with col2:
        add_button = st.form_submit_button("Add")

if add_button and movie_input:
    st.session_state.movies.append(movie_input.strip())

if st.session_state.movies:
    st.write("**Your list:**")
    for i, movie in enumerate(st.session_state.movies):
        col1, col2 = st.columns([6, 1])
        with col1:
            st.write(f"🎬 {movie}")
        with col2:
            if st.button("✕", key=f"remove_{i}"):
                st.session_state.movies.pop(i)
                st.rerun()

st.divider()
num_recs = st.slider("How many recommendations?", min_value=1, max_value=10, value=5)
get_recs_button = st.button("🎬 Get Recommendations", type="primary")

if get_recs_button:
    if not st.session_state.movies:
        st.error("Please add at least one movie before getting recommendations.")
        st.stop()

if get_recs_button and st.session_state.movies:
    with st.spinner("Analyzing your taste..."):
        titles = generate_titles(num_recs, st.session_state.movies, st.session_state.previous_recommendations)
        if not titles:
            st.error("Could not generate recommendations. Please try again.")
            st.stop()
        st.session_state.enriched = run_async(enrich_recommendations(titles))
        st.session_state.previous_recommendations.extend([m['title'] for m in st.session_state.enriched])        
        user_enriched = run_async(enrich_recommendations(titles))
        explanation = generate_explanations(user_enriched, st.session_state.enriched)
        st.session_state.explanations = explanation
        if not explanation:
            st.warning("Could not generate explanations. Try clicking Get Recommendations again.")
    
    st.session_state.last_response = explanation
    st.session_state.recommendations_made = True
    
    st.session_state.messages = [
        {"role": "system", "content": f"""You are Kinophile, a cinema expert. 
        You just recommended these films: {[m['title'] for m in st.session_state.enriched]}
        The user's favourite films were: {st.session_state.movies}
        Discuss these films naturally and answer any questions about them."""}
    ]

if st.session_state.enriched:
    st.divider()
    st.subheader("Recommendations")
    cols = st.columns(len(st.session_state.enriched))
    for i, movie in enumerate(st.session_state.enriched):
        with cols[i]:
            if movie.get("poster"):
                st.image(movie["poster"], use_container_width=True)

            st.write(f"**{movie['title']}**")
            st.write(f"⭐ IMDB: {movie['imdb_rating']}")
            st.caption(f"📅 {movie['release_year']} · 🎬 {movie['director']}")
            if st.button("Why this film?", key=f"movie_{i}"):
                st.session_state.selected_movie = movie["title"]

if st.session_state.selected_movie and st.session_state.explanations:
    st.divider()
    st.subheader(f"Why {st.session_state.selected_movie}?")
    if st.session_state.selected_movie in st.session_state.explanations:
        st.write(st.session_state.explanations[st.session_state.selected_movie])


