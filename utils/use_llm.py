import os
import openai
import config  # Added this import back so config.LLM_MODEL works

# 1. Initialize the OpenAI client
# Note: client = openai.OpenAI() automatically looks for os.getenv("OPENAI_API_KEY"),
# but explicitly passing it like you did works perfectly too!
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)


def ask_llm(prompt):
    # 2. Use OpenAI's chat completion structure
    reply = client.chat.completions.create(
        model=config.LLM_MODEL,  # e.g., "gpt-4o" or "gpt-4o-mini"
        max_completion_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    # 3. Extract the text response correctly using list index [0]
    return reply.choices[0].message.content


def summarize_text(text):
    return ask_llm("Summarize this text in 2-3 sentences:\n\n" + text)


def convert_to_quiz(text):
    return ask_llm(
        "Write 3 multiple-choice questions (with answers) based on this text:\n\n" + text
    )
    
def generate_visuals(text):
    return ask_llm(
        f"Take the following text and break it down into logical chunks. "
        f"For each chunk, find relevant visual media (images, videos, or GIFs) that fit its meaning. "
        f"Return the URLs of the visuals, organized in array.\n\n"
        f"Text:\n{text}"
    )
