# Halaqah Syumuliyah Islamiyah

Demo platform bahtsul masail virtual Fakhruddin Razi dan Sunan Bonang.

Streamlit + GPT 4.o + Pinecone + Google STTS

## Diagram Alur

```mermaid
graph TD
    A[User Input] -->|Text/Voice| B(Streamlit Interface)
    B -->|Query| C{OpenAI API}
    C -->|Generate Embedding| D[Pinecone Vector DB]
    D -->|Relevant Data| C
    C -->|Generate Responses| E[Razi Response]
    C -->|Generate Responses| F[Bonang Response]
    E --> G[Text-to-Speech]
    F --> G
    G -->|Audio| B
    B -->|Display/Play| H[User Interface]
    
    I[Google Cloud Speech-to-Text] -->|Voice Input| B
    J[Google Cloud Text-to-Speech] -->|Generate Audio| G
    
    K[Conversation Context] -->|Load/Save| B
    B -->|Update| K

    subgraph "Backend Services"
    C
    D
    I
    J
    K
    end

    subgraph "Frontend"
    B
    H
    end

    class C,D,I,J,K backend;
    class B,H frontend;
```

## Keterangan

1. Frontend: Streamlit untuk UI dan interaksi pengguna
2. Backend:
   - OpenAI API: Generasi respons dan embedding
   - Pinecone: Vector DB untuk data relevan
   - Google Cloud: Speech-to-Text dan Text-to-Speech
3. Alur:
   - Input user (teks/suara) -> Streamlit -> OpenAI
   - OpenAI query Pinecone untuk konteks
   - OpenAI generate respons Razi dan Bonang
   - Respons dikonversi ke audio
   - Hasil ditampilkan/diputar di UI
4. Konteks percakapan disimpan/dimuat untuk kontinuitas