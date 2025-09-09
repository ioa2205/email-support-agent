# AI Customer Support Email Agent

An automated email agent that uses AI to categorize, process, and respond to customer support emails. The agent can answer questions using a Retrieval-Augmented Generation (RAG) system, handle refund requests through a database, and classify other emails for manual review.

## Features

-   **Automatic Email Categorization**: Classifies incoming emails into `Question`, `Refund`, or `Other`.
-   **RAG-Powered Q&A**: Answers user questions by retrieving relevant information from a local knowledge base (`faq.txt`).
-   **Stateful Refund Processing**: Manages refund requests by checking an order database, asking for missing information, and logging invalid attempts.
-   **Gmail Integration**: Securely connects to one or more Gmail accounts using OAuth 2.0 to listen for and reply to emails.
-   **Database Integration**: Uses PostgreSQL to manage orders, unhandled emails, and user credentials.
-   **Minimalist Web UI**: A simple Flask web interface for connecting and disconnecting Gmail accounts.

## Tech Stack

-   **Backend**: Python
-   **Web Framework**: Flask
-   **Database**: PostgreSQL
-   **AI / RAG**: LangChain, Hugging Face Transformers, Sentence-Transformers, FAISS
-   **Email API**: Google Gmail API
-   **Containerization**: Docker

## Architectural Overview

The system is composed of two main parts: a web application for account management and a background listener for email processing.

```mermaid
graph TD
    subgraph User Interaction
        A[Client App UI] -- Connect Account --> B(Authentication Service);
        B -- OAuth 2.0 --> G(Google Gmail);
        G -- Tokens --> B;
        B -- Store Encrypted Tokens --> DB[(PostgreSQL)];
    end

    subgraph Backend Processing
        W[Email Listener Worker] -- Every N minutes --> DB;
        W -- Fetches New Emails --> G;
        G -- Raw Email --> W;
        W -- Sends Email to --> P(Processing Pipeline);

        P -- 1. Preprocess --> C(Classifier / LLM);
        C -- Categorizes as --> R{Category?};

        R -- "Question" --> QH(Question Handler);
        QH -- 1. Embed Question --> VDB([Vector DB / KB]);
        VDB -- 2. Find Relevant Docs --> QH;
        QH -- 3. Generate Answer (RAG) --> LLM2(LLM);
        LLM2 -- Answer --> ES(Email Sender);
        QH -- If cannot answer --> Unhandled(Save as Unhandled);

        R -- "Refund" --> RH(Refund Handler);
        RH -- Interacts with --> DB;
        RH -- Sends Reply --> ES;

        R -- "Other" --> OH(Other Handler);
        OH -- Assesses Importance (LLM) --> Unhandled;

        Unhandled -- Save to --> DB;
        ES -- Sends via Gmail API --> G;
    end
```

## Setup and Installation

### Prerequisites

-   Python 3.9+
-   Docker and Docker Desktop
-   A Google Cloud Platform account

### Step 1: Google Cloud & Gmail API Setup

1.  **Create a Google Cloud Project**: Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2.  **Enable the Gmail API**: In your project, go to "APIs & Services" > "Library", search for "Gmail API", and enable it.
3.  **Configure OAuth Consent Screen**:
    -   Go to "APIs & Services" > "OAuth consent screen".
    -   Choose **External** and fill in the required app details.
    -   **Add Scopes**: Add the `.../auth/gmail.readonly`, `.../auth/gmail.modify`, `.../auth/gmail.send`, `.../auth/userinfo.email`, and `openid` scopes.
    -   **Add Test Users**: Add the Google account(s) you intend to connect to the agent. **This is critical for the login to work in testing mode.**
4.  **Create Credentials**:
    -   Go to "APIs & Services" > "Credentials".
    -   Click "+ Create Credentials" > "OAuth client ID".
    -   Select **Web application**.
    -   Add `http://localhost:5000/oauth2callback` and `http://127.0.0.1:5000/oauth2callback` as authorized redirect URIs.
    -   Click **Download JSON** and save the file as `client_secret.json` in the project's root directory.

### Step 2: Local Project Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/ioa2205/email-support-agent-1.git
    cd email-support-agent-1
    ```
2.  **Create a virtual environment and activate it**:
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\Activate.ps1
    # macOS / Linux
    source .venv/bin/activate
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### Step 3: Database Setup

1.  **Start PostgreSQL using Docker**: Make sure Docker Desktop is running. This command will start a database that is ready to use.
    ```bash
    docker run --rm -d --name pg-email-agent -e POSTGRES_PASSWORD=mysecretpassword -e POSTGRES_DB=email_agent -p 5432:5432 postgres
    ```
2.  **Create the database tables**: Run the setup script to initialize the schema and add sample orders.
    ```bash
    python database.py
    ```

### Step 4: Populate Knowledge Base

Edit the `knowledge_base/faq.txt` file to include the questions and answers you want the RAG system to use.

## Usage

The application has two parts that you run separately.

### 1. Manage Accounts (Connect/Disconnect)

This starts the web server for managing your connected accounts.
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5000`. From here, you can connect new Gmail accounts or disconnect existing ones. You only need to run this when managing accounts.

### 2. Run the Email Agent

This is the main worker process that continuously listens for and processes emails.
```bash
python run_listener.py
```
Leave this terminal running. The agent will check for new emails every 60 seconds. The first time it runs, it will download the necessary AI models, which may take a few minutes.

## How to Test

Once the listener is running, send emails to the connected Gmail account from another address:

-   **Question**: Subject: "Help", Body: "How do I reset my password?"
-   **Refund (Valid)**: Subject: "Refund", Body: "My order ID is ORD1234G." (Use an ID from `database.py`)
-   **Refund (Invalid)**: Subject: "Money Back", Body: "The order ID is ORD99999."

Watch the console output of `run_listener.py` to see the agent in action. You will receive automated replies.