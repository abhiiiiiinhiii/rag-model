import glob
import os
from typing import List, Any, Dict, AsyncGenerator
import uuid
from sentence_transformers import CrossEncoder
from langchain.retrievers.document_compressors.base import BaseDocumentCompressor
from pydantic.v1 import ConfigDict
import pandas as pd
from langchain_core.documents import Document
import json
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.runnable import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_redis import RedisChatMessageHistory

MANUALS_PATH = "manuals"
PERSIST_DIRECTORY = "chroma_db_wms"

def format_docs(docs: list[Document]) -> str:
    """Concatenates the page content of a list of Document objects into a single string."""
    return "\n\n".join(doc.page_content for doc in docs)

class LocalReranker(BaseDocumentCompressor):
    """
    A reranker that uses a local cross-encoder model to reorder and filter documents
    based on their relevance to a query.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    model: CrossEncoder = CrossEncoder("BAAI/bge-reranker-base")
    top_n_guaranteed: int = 2
    drop_off_threshold: float = 0.20
    top_n_limit: int = 5

    def compress_documents(self, documents: List[Document], query: str, **kwargs: Any) -> List[Document]:
        if not documents: return []
        doc_query_pairs = [[query, doc.page_content] for doc in documents]
        scores = self.model.predict(doc_query_pairs)
        doc_scores = list(zip(documents, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        final_docs = []
        if not doc_scores: return final_docs
        for i in range(min(len(doc_scores), self.top_n_guaranteed)):
            final_docs.append(doc_scores[i][0])
        for i in range(self.top_n_guaranteed, len(doc_scores)):
            current_score = doc_scores[i][1]
            previous_score = doc_scores[i-1][1]
            if current_score < (previous_score * (1 - self.drop_off_threshold)): break
            final_docs.append(doc_scores[i][0])
        return final_docs[:self.top_n_limit]

class WMSChatbot:
    """
    The core class for the WMS Chatbot, handling ingestion, retrieval, and generation.
    """
    MAX_WINDOW = 6
    MAX_SUMMARY_LENGTH = 300

    def __init__(self, embedding_model: GoogleGenerativeAIEmbeddings):
        print("Initializing WMSChatbot...")
        self.embedding_model = embedding_model
        self.vectorstore = Chroma(persist_directory=PERSIST_DIRECTORY, embedding_function=self.embedding_model)
        self.faq_vectorstore = Chroma(
            persist_directory=f"{PERSIST_DIRECTORY}_faq",
            embedding_function=self.embedding_model
        )
        self.query_decomposition_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at query understanding. Your task is to analyze a user's question and the conversation history, then generate a list of simple, self-contained search queries that are necessary to answer the user's request.
            
            **Follow these rules precisely:**
            - **For follow-up questions**, use the chat history to resolve them into a clear, self-contained question.
            - **For comparative questions**, like asking for the "difference between X and Y", you MUST break them into separate queries: "What is X?" and "What is Y?".
            - **For complex questions**, break them down into multiple simple, self-contained questions.
            - **For simple questions**, return them as a single-item list.

            **CRITICAL: YOU MUST ONLY RETURN A VALID JSON OBJECT with a single key "queries" that contains a list of strings. DO NOT INCLUDE ANY OTHER TEXT, EXPLANATION, OR MARKDOWN.**
            """),
            ("user", "What is the difference between a sales order and a purchase order?"),
            ("assistant", '{{"queries": ["What is a sales order?", "What is a purchase order?"]}}'),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{question}")
        ])
        self.answer_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a highly advanced WMS assistant. Your primary goal is to be helpful, accurate, and logical. Your tone should always be professional and informational.

            **CRITICAL: Your entire response must be based exclusively on the information, terms, and concepts found in the provided CONTEXT. Do not add any outside knowledge. Always use Markdown formatting to structure your answers. do NOT write "Based on the context provided:" in the answer** Use headings, subheadings, bold text for key terms, and bullet points for lists to make your responses clear and easy to read.** If the answer is not in the context, you MUST follow RULE B.

            **Your Task:**
            Construct your answer by synthesizing and restructuring the information from the CONTEXT into a single, cohesive, and easy-to-understand response. Use Markdown for formatting. The context may contain multiple sections; use information from all relevant sections to form your answer.

            **Rules:**
            * **RULE A (Direct WMS Question):** If the user asks a direct WMS question and the **CONTEXT** contains the answer, synthesize the information to form your response. **Never simply copy and paste the context.**
            * **RULE B (Information Not Found):** If the user asks a WMS question and the **CONTEXT** is empty or irrelevant, you MUST state: "I don't have that information right now, but I've logged your question and our team will get back to you as soon as possible."
            * **RULE C (Conversational History):** If the user asks about the conversation itself (e.g., "what was my last question?"), use the **Chat History** to answer. Do not use the context.
            * **RULE D (General Chit-Chat):** If the user asks a non-WMS question, respond conversationally.

            ---
            **CONTEXT (For WMS Queries ONLY):**
            {context}
            ---
            """),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{question}"),
        ])

    # --- NEW METHODS FOR CONTROL PANEL ---
    def get_all_kb_documents(self) -> List[Dict]:
        """Retrieves a unique list of all documents from the main Chroma vectorstore."""
        results = self.vectorstore.get(include=["metadatas"])
        processed_docs = []
        seen_sources = set()
        if results and results.get('ids'):
            for metadata in results['metadatas']:
                source = metadata.get('source')
                # Ensure we process each document source only once and exclude error logs
                if source and source not in seen_sources and metadata.get('client_id') != 'errors':
                    seen_sources.add(source)
                    processed_docs.append({
                        "id": source,  # Use the source path as the unique document identifier
                        "filename": os.path.basename(source),
                        "client": metadata.get('client_id', 'Unknown')
                    })
        return processed_docs

    def get_kb_document_content(self, doc_source: str) -> Dict:
        """Retrieves the full content of a single document by its source path."""
        results = self.vectorstore.get(where={"source": doc_source}, include=["documents", "metadatas"])
        if results and results.get('documents'):
            # This reconstructs the document content from its chunks.
            full_content = "\n\n".join(doc for doc in results['documents'])
            return {
                "id": doc_source,
                "content": full_content,
                "metadata": results['metadatas'][0]  # Metadata is the same for all chunks of a doc
            }
        return {}

    def update_kb_document(self, doc_source: str, new_content: str):
        """Updates a document by deleting its old chunks and ingesting new ones."""
        existing_doc_info = self.get_kb_document_content(doc_source)
        if not existing_doc_info:
            raise ValueError("Document not found")
        
        self.vectorstore.delete(where={"source": doc_source})
        
        client_id = existing_doc_info['metadata'].get('client_id', 'common')
        doc = Document(page_content=new_content, metadata={"source": doc_source, "client_id": client_id})
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = text_splitter.split_documents([doc])
        
        # Create new unique IDs for the new chunks
        ids_to_add = [f"{doc_source}-chunk-{i}" for i, _ in enumerate(chunks)]
        self.vectorstore.add_documents(documents=chunks, ids=ids_to_add)

    def delete_kb_document(self, doc_source: str):
        """Deletes all chunks of a document from the vectorstore by its source path."""
        self.vectorstore.delete(where={"source": doc_source})

    def get_all_faqs(self) -> List[Dict]:
        """Retrieves all FAQs from the FAQ vectorstore."""
        results = self.faq_vectorstore.get(include=["metadatas", "documents"])
        processed_faqs = []
        if results and results.get('ids'):
            for i, doc_id in enumerate(results['ids']):
                processed_faqs.append({
                    "id": doc_id,
                    "question": results['documents'][i],
                    "answer": results['metadatas'][i].get('faq_answer', '')
                })
        return processed_faqs

    def add_single_faq(self, question: str, answer: str) -> Dict[str, Any]:
        """
        Adds a single new FAQ to the vector store.
        UPDATED: Now includes the question text in the metadata for efficient duplicate checking.
        """
        doc_id = f"faq_{uuid.uuid4()}"
        new_doc = Document(
            page_content=f"Question: {question}\nAnswer: {answer}",
            metadata={
                "source": "faq",
                "question": question, # IMPORTANT: Added for duplicate checking
                "id": doc_id
            }
        )
        self.vectorstore.add_documents([new_doc], ids=[doc_id])
        return {"id": doc_id, "question": question, "answer": answer}

    def update_faq(self, faq_id: str, question: str, answer: str):
        """Updates an existing FAQ by overwriting it."""
        doc = Document(page_content=question, metadata={"faq_answer": answer, "type": "faq"})
        # Using add_documents with the same ID will overwrite the existing entry in Chroma
        self.faq_vectorstore.add_documents(documents=[doc], ids=[faq_id])

    def delete_faq(self, faq_id: str):
        """Deletes an FAQ by its ID."""
        self.faq_vectorstore.delete(ids=[faq_id])
    def faq_question_exists(self, question: str) -> bool:
        """
        Checks if an FAQ with the exact question already exists in the vector store.
        This is used to prevent duplicate entries during CSV imports.
        """
        if not self.vectorstore:
            return False
        # Use the 'get' method with a 'where' filter for an exact match on metadata.
        # This is highly efficient as it doesn't perform a vector search.
        results = self.vectorstore.get(where={"question": question, "source": "faq"})
        return len(results['ids']) > 0

    def ingest_faqs_from_csv(self, faq_directory: str):
        if not os.path.isdir(faq_directory):
            print(f"Error: Directory '{faq_directory}' not found.")
            return

        csv_files = glob.glob(os.path.join(faq_directory, "*.csv"))

        if not csv_files:
            print(f"No CSV files found in '{faq_directory}'.")
            return

        faq_docs = []
        for file_path in csv_files:
            try:
                df = pd.read_csv(file_path)
                for index, row in df.iterrows():
                    question = row.get('question')
                    answer = row.get('answer')
                    if question and answer:
                        doc = Document(
                            page_content=question,
                            metadata={"faq_answer": answer, "type": "faq", "source_file": os.path.basename(file_path)}
                        )
                        faq_docs.append(doc)
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                continue

        if faq_docs:
            source_files = list(set(doc.metadata["source_file"] for doc in faq_docs))
            if source_files:
                self.faq_vectorstore.delete(where={"source_file": {"$in": source_files}})
            print(f"Ingesting {len(faq_docs)} FAQs...")
            self.faq_vectorstore.add_documents(faq_docs)
            print("FAQ ingestion complete.")
        else:
            print("No valid FAQ data found in the CSV files.")

    def _get_llms_for_key(self, api_key: str):
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", temperature=0, google_api_key=api_key)
        decomposition_llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite", temperature=0, google_api_key=api_key
        )
        return llm, decomposition_llm

    def local_summarize(self, old_messages: list[str]) -> str:
        summary_lines = []
        for msg in old_messages:
            first_line = msg.split('\n')[0]
            if len(" ".join(summary_lines + [first_line])) > self.MAX_SUMMARY_LENGTH:
                break
            summary_lines.append(first_line)
        return "Summary of previous conversation:\n" + "\n".join(summary_lines)

    def get_session_history(self, session_id: str) -> RedisChatMessageHistory:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        # FIX: The parameter name is `url`, not `redis_url` as used in older versions.
        return RedisChatMessageHistory(session_id=session_id, redis_url=redis_url)

    def ingest_documents(self, source_folder: str) -> Dict[str, int]:
        ingestion_path = os.path.join(MANUALS_PATH, source_folder)
        client_id = source_folder

        if not os.path.isdir(ingestion_path):
            raise FileNotFoundError(f"Source folder '{ingestion_path}' not found.")

        loader = DirectoryLoader(ingestion_path, glob="**/*.md", loader_cls=UnstructuredMarkdownLoader, show_progress=True)
        documents = loader.load()

        new_chunks_with_ids = {}
        if documents:
            for doc in documents:
                doc.metadata["client_id"] = client_id
            
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
            chunks = text_splitter.split_documents(documents)
            
            for i, chunk in enumerate(chunks):
                source_path = chunk.metadata.get("source", "unknown_source")
                unique_id = f"{source_path}-chunk-{i}"
                new_chunks_with_ids[unique_id] = chunk
        
        existing_docs = self.vectorstore.get(where={"client_id": client_id})
        existing_ids = set(existing_docs.get('ids', []))
        new_ids = set(new_chunks_with_ids.keys())

        chunks_to_add = list(new_chunks_with_ids.values())
        ids_to_add = list(new_chunks_with_ids.keys())
        
        if chunks_to_add:
            self.vectorstore.add_documents(documents=chunks_to_add, ids=ids_to_add)

        ids_to_delete = list(existing_ids - new_ids)
        
        if ids_to_delete:
            self.vectorstore.delete(ids=ids_to_delete)
            
        return {"added_or_updated": len(ids_to_add), "deleted": len(ids_to_delete)}

    def ask(self, query: str, client_id: str, session_id: str, llm: ChatGoogleGenerativeAI, decomposition_llm: ChatGoogleGenerativeAI):
        base_retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={'k': 5, 'filter': {'$or': [{'client_id': {'$eq': client_id}}, {'client_id': {'$eq': 'common'}}]}},
        )
        reranker = LocalReranker()
        decomposition_chain = self.query_decomposition_prompt | decomposition_llm | JsonOutputParser()

        def retrieve_and_rerank_docs(input_dict: dict) -> str:
            sub_queries = input_dict.get("decomposed_queries", {}).get("queries", [input_dict["question"]])
            final_docs = []
            for q in sub_queries:
                retrieved_docs = base_retriever.invoke(q)
                reranked_docs = reranker.compress_documents(documents=retrieved_docs, query=q)
                final_docs.extend(reranked_docs)
            unique_docs = list({doc.page_content: doc for doc in final_docs}.values())
            return format_docs(unique_docs)

        conversational_rag_chain = (
            RunnablePassthrough.assign(decomposed_queries=decomposition_chain)
            | RunnablePassthrough.assign(context=retrieve_and_rerank_docs)
            | self.answer_prompt
            | llm
            | StrOutputParser()
        )
        final_chain = RunnableWithMessageHistory(
            conversational_rag_chain, self.get_session_history,
            input_messages_key="question", history_messages_key="chat_history",
        )
        return final_chain.invoke(
            {"question": query},
            config={"configurable": {"session_id": session_id}}
        )
    
    async def ask_stream(self, query: str, client_id: str, session_id: str, llm: ChatGoogleGenerativeAI, decomposition_llm: ChatGoogleGenerativeAI) -> AsyncGenerator[str, None]:

        faq_retriever = self.faq_vectorstore.as_retriever(search_kwargs={'k': 4})
        candidate_faqs = faq_retriever.invoke(query)
        suggestion_questions = [doc.page_content for doc in candidate_faqs]

        if candidate_faqs:
            reranker = LocalReranker()
            doc_query_pairs = [[query, doc.page_content] for doc in candidate_faqs]
            scores = reranker.model.predict(doc_query_pairs)
            doc_scores = list(zip(candidate_faqs, scores))
            doc_scores.sort(key=lambda x: x[1], reverse=True)
            
            best_doc, best_score = doc_scores[0]
            
            RERANKER_THRESHOLD = 0.99 
            if best_score > RERANKER_THRESHOLD:
                faq_answer = best_doc.metadata.get("faq_answer", "Sorry, the cached answer is missing.")
                yield faq_answer
                
                final_suggestions = [q for q in suggestion_questions if q != best_doc.page_content]
                if final_suggestions:
                    yield f"SUGGESTIONS::{json.dumps(final_suggestions)}"
                return

        base_retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={'k': 5, 'filter': {'$or': [{'client_id': {'$eq': client_id}}, {'client_id': {'$eq': 'common'}}]}},
        )
        reranker = LocalReranker()
        decomposition_chain = self.query_decomposition_prompt | decomposition_llm | JsonOutputParser()

        def retrieve_and_rerank_docs(input_dict: dict) -> str:
            decomposed_queries_data = input_dict.get("decomposed_queries")
            if isinstance(decomposed_queries_data, dict) and 'queries' in decomposed_queries_data:
                sub_queries = decomposed_queries_data['queries']
            else:
                sub_queries = [input_dict["question"]]

            final_docs = []
            for q in sub_queries:
                retrieved_docs = base_retriever.invoke(q)
                reranked_docs = reranker.compress_documents(documents=retrieved_docs, query=q)
                final_docs.extend(reranked_docs)
            unique_docs = list({doc.page_content: doc for doc in final_docs}.values())
            return format_docs(unique_docs)

        conversational_rag_chain = (
            RunnablePassthrough.assign(decomposed_queries=decomposition_chain)
            | RunnablePassthrough.assign(context=retrieve_and_rerank_docs)
            | self.answer_prompt
            | llm
            | StrOutputParser()
        )
        final_chain = RunnableWithMessageHistory(
            conversational_rag_chain, self.get_session_history,
            input_messages_key="question", history_messages_key="chat_history",
        )
        
        async for chunk in final_chain.astream(
            {"question": query},
            config={"configurable": {"session_id": session_id}}
        ):
            yield chunk
        
        if suggestion_questions:
            yield f"SUGGESTIONS::{json.dumps(suggestion_questions)}"

    def ask_error_solution(self, query: str, llm: ChatGoogleGenerativeAI):
        error_solution_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a technical analyst. Based on the CONTEXT and the user's QUESTION, generate a JSON object with "answer" and "confidence_score" keys.

        - **answer**: Synthesize a solution from the CONTEXT. You may use details from the QUESTION to be more specific.
        - **confidence_score**: A score from 0-100. The score should be high (90+) if the CONTEXT is relevant to the QUESTION. The score must be 0 if the CONTEXT is irrelevant.
        - **CRITICAL**: Only use the provided CONTEXT. If the context is irrelevant, the answer must be "I don't have enough information...". Your entire output must be a valid JSON object.

        ---
        **CONTEXT:**
        {context}
        ---
        """),
        ("user", "{question}"),
    ])


        error_retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={'k': 1, 'filter': {'client_id': {'$eq': 'errors'}}},
        )
        
        error_rag_chain = (
            {"context": error_retriever | format_docs, "question": RunnablePassthrough()}
            | error_solution_prompt
            | llm
            | JsonOutputParser()
        )

        return error_rag_chain.invoke(query)

