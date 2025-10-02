from google import genai
import config
import os
import re
import logging

app_name = config.APP_NAME
logger = logging.getLogger(app_name)

os.environ["GEMINI_API_KEY"] = config.GEMINI_API_KEY

def get_writing_style(messages):
    method_name = "get_writing_style"
    logger.info("processing begins.", extra={"path": method_name})

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
                                                        How the tone changes with respect to a received message.\
                                                            The writing style part should be enclosed between ---"
    content = extract_text_from_messages(messages)

    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=content+"\n\n"+prompt
    )
    logger.info("processing ends.", extra={"path": method_name})
    return remove_extra_text_from_llm_response(response.text)

def extract_text_from_messages(messages:dict):
    method_name = "extract_text_from_messages"
    logger.info("processing begins.", extra={"path": method_name})
    text = ''
    for thread in messages:
        text=text+str(thread)+'\n'
    logger.info("processing ends.", extra={"path": method_name})
    return text

def remove_extra_text_from_llm_response(text):
    method_name = "remove_extra_text_from_llm_response"
    logger.info("processing begins.", extra={"path": method_name})
    match = re.search(r"---\s*(.*?)\s*---", text, re.DOTALL)

    if match:
        extracted = match.group(1).strip()
        logger.info("processing ends.", extra={"path": method_name})
        return extracted
    else:
        logger.info("processing ends with nothign to extract from LLM response.", extra={"path": method_name})


def get_draft(writing_style, email_message_text):
    method_name = "get_draft"
    logger.info("processing begins.", extra={"path": method_name})

    prompt = "this is my writing style. I want you to draft possible responses for the email I received. The email is attached below.\
        Do not give any extra text or follow up questions that are not relavant to the email or the response. \
            Your response should only contain text for the possible responses."
    
    content = writing_style + "\n\n" + prompt + "\n\n" + email_message_text

    client = genai.Client()


    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=content
    )
    logger.info("processing ends.", extra={"path": method_name})
    return response.text