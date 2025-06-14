# tds-project-virtual-ta

A Retrieval-Augmented Generation (RAG) based Virtual Teaching Assistant for the "Tools in Data Science" course at IIT Madras. This system answers student questions using course content and Discourse forum posts.

## Features

- Answers questions from course materials and forum discussions
- Supports both text and image queries
- Persistent chat history
- Deployable via Docker
- Automatic ChromaDB vector store initialization

```git clone https://github.com/24f2000164/tds-project-virtual-ta.git```

## Project Structure
tds-virtual-ta/
|__ main.py # FastAPI endpoint
│__ data_processor.py # Data processing pipeling
|__ course_scaper.py # for scrape the course content
|__ discourse_scraper.py # for scrape the discourse posts
|__ chroma_db/ # Vector store (auto-generated)
|__ Dockerfile # Docker configuration
|__ render.yaml # Render deployment config
|__ requirements.txt # Python dependencies
|__ vector_store.py # for converting the into vector
|__ README.md

---

## 📦 Requirements

All dependencies are in `requirements.txt`, but key packages include:

- `fastapi`
- `uvicorn`
- `langchain`
- `langchain-openai`
- `openai`
- `chromadb`
- `markdownify`
- `Pillow`
- `pydantic`
- `langchain-chroma`
- `playwright`
- `dotenv`
- `langchain-community`
- `langchain-core`
- `requests` *(for scraping)*
- `beautifulsoup4` *(for scraping)*




---

## 🐳 Docker Setup

### Build and Run Locally

Access the app at:
like 
```
http://localhost:8000```


```bash
docker build -t virtual-ta .
docker run -p 8000:8000 virtual-ta


🌐 Deployment (Render)
Uses render.yaml to deploy directly from GitHub with Docker.

Set environment variables  in .env file like:

OPENAI_API_KEY=api key here

OPENAI_BASE_URL=base url of chat completion

EMBEDDINGS_BASE_URL= base url fo embedding


The endpoint must accept a POST request, e.g. POST https://app.example.com/api/ with a student question as well as optional base64 file attachments as JSON.

 
For example, here’s how anyone can make a request:
if you run this command on your terminal and replace "https://app.example.com/api/" with your exact endpoint  it may local or deployed
```curl "https://app.example.com/api/" \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"I know Docker but have not used Podman before. Should I use Docker for this course?"}" ```
 


The response must be a JSON object like this:
```
{"answer":"In this course, while Docker is the industry standard for containerization, Podman is recommended due to its better security features. However, Docker works in a similar way, so you can use either Docker or Podman for the course.",

"links":[{"url":"https://tds.s-anand.net/#/docker",
"text":"I would recommend Podman or Docker CE rather than Docker Desktop. Docker Desktop is not free for organizations over 250 people and many organizations have therefore moved away from it...."},

{"url":"https://discourse.onlinedegree.iitm.ac.in/t/sudo-permission-needed-to-create-data-folder-in-root/167072/2",
"text":"Hi Vikram, This is because (if you watched the session, or examined the code, you would have realised that) datagen.py was designed to run inside your docker container. And datagen.py (or a similar na..."}]}```

if you want to evaluate your  project with promptfoo file then as sample file is available in directory and in file only change the openai api 
run this command in terminal:


``` npx -y promptfoo eval --config project-tds-virtual-ta-promptfoo.yaml```



🔗 Deployment URL:
Live App: https://tds-project-virtual-ta.onrender.com
(Replace with actual URL once deployed)

🛡️ License
MIT License – free to use and modify.


🙋‍♂️ Author
Sahil Kumar

[bt23ece015@nituk.ac.in](bt23ece015@nituk.ac.in)
[24f2000164@ds.study.iitm.ac.in](24f2000164@ds.study.iitm.ac.in)


[GitHub](https://github.com/24f2000164/tds-project-virtual-ta)

[LinkedIn](https://www.linkedin.com/in/sahil-kumar-1645a3324/)



```
### 📌 To Do:
1. Replace `https://your-service-name.onrender.com` with your **Render URL**.
2. Confirm if your scraping script should be documented — if not, I’ll remove that section.

Want me to save this and send it to you as a file or push it to GitHub?```