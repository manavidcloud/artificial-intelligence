# 1. preresisites prior start real project
# Install Uv
- It will install uv package manager 
https://docs.astral.sh/uv/getting-started/installation/

powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"


# Create Virtual enviornmnet 
1. initialise in working direcotry 
uv init 

2. create virtual enviorinment
uv venv
- It will create .venv dirctory

3. Now activate it
- To Install library in virtual we have to active it 
.venv\Scripts\activate

4. (Optional) Instlall jupyter librarya
uv add ipykernel

uv add <libraryname>
=============
# 2. Create requirments.txt
create requirments.txt file outside .venv folder
- enter which library you want to use it here.
langchain
langchain-community
langchain-openai
langchain-xai
langchain-google-genai
python-dotenv

- don't give any version so it will install recent versions in it

- once installed in srv folder check pyproject.toml file you will see all version details of this librarary. 

=============

# 3. create the API keys
- - Generate the API key
1. Google
https://aistudio.google.com/

2. Grok
https://console.groq.com/keys

3. OpenAI key
https://platform.openai.com/

=============

# 4. Cretae .env file
- create .env outside the .venv folder 
- enter the api key with key=value pair

OPENAI_API_KEY= ""
GROQ_API_KEY= ""
GOOGLE_API_KEY= ""
