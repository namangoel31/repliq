from google import genai
import config
import os
import re

# Configure your API key
# Replace 'YOUR_API_KEY' with your actual Gemini API key
os.environ["GEMINI_API_KEY"] = config.GEMINI_API_KEY

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
def get_writing_style(messages):
    print("inside get writing style")
    client = genai.Client()
    prompt = "these are a few conversation I've had with people over email.\
        It is a list of messages in order of occurance. \
            The messages I sent are prefixed with 'Sent:' and the messages I received are prefixed with 'Received:'.\
                I want you to act as my assistant and reply for me to the messages I receive.\
                    I want you to deduce my general writing style, sentence structure, flow and whatever is necessary for you to respond as me. \
                        Take note of my tone, the tone of incoming message and how my tone changes with respect to a received message. \
                            I want you to generate my writing style in a manner such that I can store it somewhere and If i provide you that information later, \
                                you can consume it and respond as me later on.\
                                    it should have everything summarised in following 6 sections: Tone & Formality,\
                                          Sentence Structure & Flow, \
                                            Specific Language & Punctuation, \
                                                Greetings & Closings, \
                                                    Reply Behavior, and, \
                                                        How the tone changes with respect to a received message."
    content = extract_text_from_messages(messages)

    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=content+"\n\n"+prompt
    )
    return remove_extra_text_from_llm_response(response.text)

def extract_text_from_messages(messages:dict):
    text = ''
    for thread in messages:
        text=text+str(thread)+'\n'
    return text

def remove_extra_text_from_llm_response(text):
    # Use regex to capture everything between --- markers
    match = re.search(r"---\s*(.*?)\s*---", text, re.DOTALL)

    if match:
        extracted = match.group(1).strip()
        return extracted
    else:
        print("No match found")


def get_draft(writing_style, email):
    prompt = "this is my writing style. I want you to draft possible responses for the email I received. The email is attached below.\
        Do not give any extra text or follow up questions that are not relavant to the email or the response. \
            Your response should only contain text tfor the possible responses."
    
    content = writing_style + "\n\n" + prompt + "\n\n" + email

    client = genai.Client()


    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=content
    )
    return response.text