# Repliq: Draftly
**Repliq** is an AI-powered reply drafting assistant for Gmail. It integrates seamlessly into your existing inbox, helping you respond to emails faster — without leaving Gmail.

---

## ✨ Features

- ✍️ Learns your **writing style** from your past email replies.  
- 🤖 Automatically drafts context-aware replies for new incoming emails.  
- 📬 Saves generated replies directly into your **Gmail Drafts**, letting you pick the best one.  
- 🔒 Uses Google OAuth for secure access to your Gmail.  
- 🌐 Runs locally with public access via Ngrok for Gmail push notifications.

---

## 🧭 How It Works

1. **Login with Google** and authorize the app.  
   → Repliq fetches your **latest 50 sent email threads**.  

2. The fetched replies are sent to an **LLM** to deduce your **context-aware writing style**.

3. Repliq sets up an **email watch** to get notified when a new email arrives.

4. When a new email comes in, it is fed to the LLM along with your writing style.

5. The **LLM generates a draft reply** in your style.

6. The generated reply is **saved to Gmail Drafts**.

7. You simply open Gmail and pick or edit the most suitable draft.

---

## 🧠 Design Decisions

### 📌 Approach
Repliq is **not a standalone email client**.  
Instead of forcing users into a new interface, it **enhances Gmail** directly. This preserves familiarity while adding AI capabilities in a **non-intrusive** way.

### 🐍 Language — Python
Python’s rich **ML and AI ecosystem** makes it ideal for integrating LLMs. It’s also easy to extend and maintain.

### ⚡ Framework — FastAPI
- Lightweight and fast.  
- Developer-friendly for quick iterations.  
- Perfect for simple web backends.

### 🗄️ Database — PostgreSQL
- Only **two relational tables** are needed.  
- Records are fetched and used entirely, so NoSQL adds no benefit.  
- Even for large writing style records, entire strings are passed to the app.

### 🚀 Cache — Redis
- App is **multi-tenant**.  
- Tokens are stored in Redis hashes, not in-memory or DB, for fast access across users and functions.

### 🔐 Auth — Google OAuth API
Repliq requires permission to monitor and draft emails, so using **Google’s native OAuth** is the most secure and seamless approach.

### 🤖 LLM — Gemini
- Staying within Google’s ecosystem simplifies management.  
- Gemini’s responses matched other LLMs in testing.

### 🌍 Tunneling — Ngrok
- Gmail push notifications require a **public HTTPS endpoint**.  
- Ngrok offers free static domains, making it ideal for local development.

---

## 🛠️ Setup & Installation

Follow these steps to run Repliq locally:

### 1. 🧪 Create Environment
``` bash
# Install Conda if not already installed
# Create the environment
conda env create -f environment.yml
# Activate it
conda activate repliq
```

### 2. 🔑 Set Up Google Cloud Project
- Create a [Google Cloud](https://console.cloud.google.com) account.  
- Go to **APIs & Services → OAuth consent screen**.  
- Fill out all required fields to register a client.  
- Under **Test users**, add the Gmail account(s) you’ll use.

### 3. 🌐 Set Up Ngrok
- Install and configure [Ngrok](https://ngrok.com/).  
- Start a tunnel to expose your app to the internet:
  ```bash
  ngrok http 8000
  ```
- Copy the **Ngrok domain** for use in the next step.

### 4. 📬 Configure Pub/Sub
- In Google Cloud, create a **Pub/Sub topic** for Gmail push notifications.  
- Set the **Ngrok URL** as the endpoint for notifications.

### 5. ⚙️ Configure the App
- Update the app’s configuration file with:
  - Google OAuth client credentials
  - Pub/Sub details
  - Redis connection info
  - Any other environment-specific values

### 6. ▶️ Run the App
```bash
# From the project root
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Once running, you can log in with Google, authorize the app, and start drafting AI replies 🚀

---

## 🛳️ Kubernetes manifest details
### 🧩 Components:
- Deployemnt
- Service
- HPA

### 📒 Explanation:
- Deployemnt makes sure our app is always running
- Service exposes our app
- HPA scales our app horizontally to cater incoming traffic. 


---

## 📝 Roadmap
- [ ] Add support for multiple email accounts per user  
- [ ] Web UI for configuration and usage metrics  
- [ ] LLM fine-tuning for improved personalization  
- [✅] Deployment templates (Kubernetes)