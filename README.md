* REPLIQ: Draftly
*I'm calling my app Repliq

This is an AI reply drafting app.

Flow within our application:
1. Once you login with Google and authorize the app, it fetches your latest sent emails, limited to 50 email chains.
2. These fetched replies are then fed to an LLM for it to deduce a context aware writing style.
3. Then, we setup an email watch which notifies us as soon as a new email arrives.
4. We fetch that email, and feed it to the LLM along with our writing style. 
5. The LLM generates a response for the email based in the writing style.
6. We then save the responses to Gmail draft.
7. User can just go to Gmail and keep the appropriate response while deleting the discarded ones.

Decisions and explanation:

Approach: This is not designed as a standalone app but as an integration for Gmail.
    I find having a separate app for every little thing is just crazy. No app can replace your inbox and putting new app just to view your email is going to take a lot of time to accommodate. This preserves the damiliarity of Gmail while adding capabilities of AI in a non-intrusive way.

Language: Python 
    Since this project requires integration of LLMs, Python with it's ecosystem for ML and AI makes it a great choice. It makes it super easy to extend in the future.

Framework: FastAPI
    Quick and developer friendly. Building backend with FastAPI helps deliver projects fast. It is perfectly suited for simple web apps.

Database: Relational Database. PostgreSQL
    Relational Database as we only need two tables and all the records are fetched and used entirely. Our records are small and at almost all of the places, we're using complete records. Our records are big in case of writing style but there we need to pass the entire record as a string to the app. So going for additional NoSQL database didn't make sense.

Cache: Redis
    Our app will be multitenant. We cannot keep the tokens in memory with the app and We do not store tokens in a DB. But storing it in a cache makes sense as it's needed regularly by the various function in our app. Each user will have their token stored in a separate hash with a unique key.

Auth: Google auth API
    Since we'll be monitoring emails for roducing replies, it makes sense to just use Googles OAuth to obtain permissions to use Gmail.

LLM: Gemini
    Since I'm using everythin google, why not LLM. Makes it easier to manage. Also, the responses from different models were pretty much similar during my testing.

Tunnel: NGROK
    Google needs to reach our app in order to send push notifications. To make our app reachable, we need to expose it to the internet. NGROK is free and provides one free static domain.

Replication of Environemnt and running the app:

- install conda
- create conda envronment using "environment.yml" file.
- create google cloud account and goto console
- create a project and under API & Service, go to “OAuth consent screen”
- Fill out all the necessary details to register for a client.
- Then goto audience and under Test user section, enter the email you wish to test the application with.
- setup ngrok on your machine. This will expose your app to the internet. Google will need an endpoint to reach our app.
- Now, setup a pub/sub topic with the details of project you created above. Here, enter the ngrok domain that you obtained. This will act as an intermediary between user's gmail account and our application.
- come back to local machine, navigate to app's root folder and activate the conda environment we created earlier.
- update the config file with all your details.
- then start the application.