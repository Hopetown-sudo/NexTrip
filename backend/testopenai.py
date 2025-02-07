import openai
import os
openai.api_key = os.getenv("OPENAI_API_KEY")
try:
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ]
    )

    # Output the response
    print("Response:", response.choices[0].message.content.strip())

except openai.AuthenticationError:
    print("Authentication failed. Check your API key.")
except openai.OpenAIError as e:
    print("An error occurred:", str(e))
