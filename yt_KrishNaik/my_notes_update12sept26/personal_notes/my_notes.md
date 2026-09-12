# 1. Prerequisites Prior to Starting the Real Project

## Install uv
- It will install the uv package manager.
- https://docs.astral.sh/uv/getting-started/installation/

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Create Virtual Environment

1. Initialise in working directory
   ```
   uv init
   ```

2. Create virtual environment
   ```
   uv venv
   ```
   - It will create a `.venv` directory.

3. Now activate it
   - To install a library in the virtual environment, we have to activate it first.
   ```
   .venv\Scripts\activate
   ```

4. (Optional) Install jupyter library
   ```
   uv add ipykernel
   uv add <libraryname>
   ```

---

# 2. Create requirements.txt

- Create a `requirements.txt` file outside the `.venv` folder.
- Enter which libraries you want to use here:
  ```
  langchain
  langchain-community
  langchain-openai
  langchain-xai
  langchain-google-genai
  python-dotenv
  ```
- Don't give any version, so it will install the most recent versions.
- Once installed, check the `pyproject.toml` file in the project folder — you will see all the version details of these libraries.

---

# 3. Create the API Keys

Generate the API key from each provider:

1. **Google** — https://aistudio.google.com/
2. **Grok** — https://console.groq.com/keys
3. **OpenAI** — https://platform.openai.com/

---

# 4. Create .env File

- Create `.env` outside the `.venv` folder.
- Enter the API key as a key=value pair.

```
OPENAI_API_KEY=""
GROQ_API_KEY=""
GOOGLE_API_KEY=""
```
