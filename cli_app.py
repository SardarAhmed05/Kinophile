import requests
import time
from dotenv import load_dotenv
import os
import json

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
tmdb_api = os.getenv("TMDB_API_KEY")
omdb_api = os.getenv("OMDB_API_KEY")

url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

def system_prompt(num_recs):
    return f"""
You are KinoAgent, a world-class film recommendation expert.

Your purpose is not merely to recommend movies, but to understand a person's cinematic taste and guide meaningful conversations about cinema.

When analyzing a user's taste, infer:
- Favorite genres
- Emotional tone
- Pacing preferences
- Cinematography and visual style
- Recurring themes
- Character archetypes
- Tolerance for ambiguity
- Preferred endings
- Appreciation for international or arthouse cinema

Before recommending anything, decide whether you have enough information.

If the user's input is vague, ambiguous, or too limited, ask ONE concise clarifying question and wait for the user's reply before making recommendations. Never make assumptions when a brief question would improve the recommendations.

Recommend exactly {num_recs} films.

Prioritize thoughtful, insightful recommendations over the most obvious choices. Balance acclaimed classics with lesser-known gems whenever appropriate.

- Include the movie's release year and IMDB rating as well.
For each recommendation, briefly explain:
- Why it matches the user's taste
- Which of their favorite films it resembles
- The director
- What makes the film unique

Keep recommendations concise and easy to read using clean spacing. Do not use tables or boxed layouts.

After you provide the initial recommendations, consider that request complete. From then on, respond naturally to the user's messages. Do not continue asking follow-up questions about the recommendations unless the user brings them up again.
After the initial recommendations, you may discuss the films, explore other genres, compare movies, or provide additional recommendations based on the user's evolving taste. 

End naturally with a friendly question that encourages further conversation, such as discussing one of the recommended films, exploring another genre, comparing movies, or asking for more recommendations. Vary this closing instead of repeating the same wording every time.

Be warm, conversational, and enthusiastic.

Treat cinema as art.

After your recommendations, on the very last line write exactly:
TITLES: [only the titles of the films you just recommended, separated by |]
"""

def agent(messages):
    response = requests.post(url, headers=headers, json={"model": "openai/gpt-oss-20b", "messages": messages, "temperature": 0.7})
    if response.status_code == 200:
        reply = response.json()["choices"][0]["message"]["content"]
        return reply
    else:
        return f"Error: {response.status_code} - {response.text}"
    
def validate_movie(title):
    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "query": title,
        "api_key": tmdb_api,
        "language": "en-US",
        "page": 1
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        results = response.json()
        if results['results']:
            return results["results"][0]  # Return the first matching movie
        else:
            print(f"No results found for '{title}'. Please check the title and try again.")

def get_movie_details(tmdb_id):
    tmdb_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    tmdb_params = {"api_key" : tmdb_api}
    tmdb_response = requests.get(tmdb_url, params=tmdb_params)
    imdb_id = tmdb_response.json().get("imdb_id")
    if not imdb_id:
        return None

    omdb_url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={omdb_api}"
    response = requests.get(omdb_url)
    result = response.json()
    movie_title = result.get("Title", "N/A")
    release_year = result.get("Year", "N/A")
    imdb_rating = result.get("imdbRating", "N/A")
    director = result.get("Director", "N/A")

    return {
        "title": movie_title,
        "release_year": release_year,
        "imdb_rating": imdb_rating,
        "director": director
    }

def enrich_recommendations(rec_movies):
    validated = []
    for title in rec_movies:
        movie = validate_movie(title)
        if movie:
            details = get_movie_details(movie['id'])
            validated.append(details)
        else:
            print(f"Could not find {title} on TMDB. Skipping.")
        
    return validated

def extract_titles(response):
    for line in response.split("\n"):
        if line.startswith("TITLES:"):
            return [t.strip() for t in line.replace("TITLES:", "").split("|")]
    return []
        
print("\nTHE KINO AGENT!")
time.sleep(1)

movies = []
print("\nKino Agent: Welcome to the Kino Agent Recommendation System!")
time.sleep(1)
num_recs = input("Kino Agent: How many recommendations would you like? (default is 5): ")
if not num_recs.strip():
    num_recs = 5
else:
    try:
        num_recs = int(num_recs)
    except ValueError:
        print("Invalid input. Defaulting to 5.")
        num_recs = 5
      
print("\nKino Agent: Enter films one by one, press enter on empty line when you are done")
while True:
    movie = input("Kino Agent: Movie: ")
    if movie.strip() == "":
        break
    movies.append(movie.strip())

if not movies:
    print("Kino Agent: No movies entered. Entering chat mode...")
    time.sleep(1)
    messages = [
    {"role": "system", "content": system_prompt(num_recs)}
    ]
    print("\nKino Agent: Tell me about your taste in films, or ask me anything about cinema.\n")

else:
    user_input = f"Favourite films: {', '.join(movies)}"

    messages = [{"role": "system", "content": system_prompt(num_recs)},
                {"role": "user", "content": user_input}]       

    print("\nKino Agent: Thinking...\n")
    recommendations = agent(messages)
    titles = extract_titles(recommendations)
    final_recommendations = "\n".join([line for line in recommendations.split("\n") if not line.startswith("TITLES:")])
    print(final_recommendations)
    messages.append({"role": "assistant", "content": final_recommendations})

    if titles:
        enriched = enrich_recommendations(titles)

#        for movie in enriched:
#           print(f"\n{movie['title']} ({movie['release_year']}) — IMDB: {movie['imdb_rating']} — Director: {movie['director']}")

while True:
    user_input = input("You: ").strip()
    if user_input.lower() == "exit":
        print("Exiting KinoAgent. Goodbye!")
        break
    messages.append({"role": "user", "content": user_input})
    reply = agent(messages)
    titles = extract_titles(reply)
    final_recommendations = "\n".join([line for line in reply.split("\n") if not line.startswith("TITLES:")])

    print(f"KinoAgent: {final_recommendations}")
    messages.append({"role": "assistant", "content": final_recommendations})
    if titles:
        enriched = enrich_recommendations(titles)
