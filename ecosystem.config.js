module.exports = {
    apps: [
      {
        name: "halaqah",
        script: "streamlit",
        args: "run halaqah.py --server.port 8059",
        interpreter: "python3",
        env: {
          GOOGLE_APPLICATION_CREDENTIALS: "/path/to/your/credentials.json",
          OPENAI_API_KEY: "your_openai_api_key",
          PINECONE_API_KEY: "your_pinecone_api_key",
          PINECONE_ENVIRONMENT: "your_pinecone_environment",
        },
      },
    ],
  };