import openai

def create_chat_gpt_request(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
        {"role": "system", "content": """You are a zen master who is enlightened 
            and knows everything about birds, including ancient secrets. You speak cryptically and,
            although you don't blatantly lie, you use your mystical language to make things
            seem as interesting as possible."""},
        {"role": "user", "content": prompt},
        #{"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
        #{"role": "user", "content": "Where was it played?"}
    ]
    )

    return response.choices[0].message.content