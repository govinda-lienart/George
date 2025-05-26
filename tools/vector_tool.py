# Last updated: 2025-05-20 — memory support + improved vector logging + Hallucination Fix

from langchain.agents import Tool
from langchain.prompts import PromptTemplate
# Ensure these imports from utils.config are correctly defined in your utils/config.py
# For example:
# from langchain_google_genai import ChatGoogleGenerativeAI # if using Google's models
# from langchain_community.vectorstores import FAISS # or whatever vectorstore you use
# from langchain_community.embeddings import GoogleGenerativeAIEmbeddings # or your embedding model
from utils.config import llm, vectorstore  # Assuming llm and vectorstore are properly initialized here

from logger import logger
import streamlit as st
from langchain.callbacks import LangChainTracer  # Import the tracer
from langchain.chains import RetrievalQA  # Although not directly used for the tool logic, useful for context

# --- Prompt template for response generation ---
vector_prompt = PromptTemplate(
    input_variables=["summary", "context", "question"],
    template="""
You are George, the friendly AI receptionist at *Chez Govinda*.

**Important: Answer ONLY based on the factual information explicitly provided in the "Hotel Knowledge Base" below.**
- Do NOT make up or guess any details.
- Do NOT ask follow-up questions or offer further assistance.
- Do NOT try to continue the conversation.
- Simply answer the user's question clearly and accurately based on the context.
- If the answer is not found in the provided context, say so honestly.

Conversation so far:
{summary}

Hotel Knowledge Base:
{context}

User: {question}

---

Please answer the user's question using the facts above. Do not include any additional remarks or ask if the user needs anything else.

Use markdown when helpful. When relevant, include one of these reference links:

1. Rooms and accommodations: [Rooms](https://sites.google.com/view/chez-govinda/rooms)
2. Environmental commitments: [Environmental Commitment](https://sites.google.com/view/chez-govinda/environmental-commitment)
3. Breakfast and dining: [Breakfast and Guest Amenities](https://sites.google.com/view/chez-govinda/breakfast-guest-amenities)
4. Amenities: [Amenities](https://sites.google.com/view/chez-govinda/breakfast-guest-amenities)
5. Wellness options: [Wellness page](https://sites.google.com/view/chez-govinda/breakfast-guest-amenities)
6. Policies: [Hotel Policy](https://sites.google.com/view/chez-govinda/policy)
7. Contact and location: [Contact & Location](https://sites.google.com/view/chez-govinda/contactlocation)

**Key factual rules:**
- If asked about room types, list these 7: Single, Double, Suite, Economy, Romantic, Family, Kids Friendly — but ONLY if they appear in the context.
- If asked about the address/location, extract it **exactly** from the context or say it's not available, and include the location link.

Respond as George. Use a warm tone, but never follow up or prolong the chat.
"""
)


# --- Tool logic ---
def vector_tool_func(user_input: str) -> str:
    logger.info(f"🔍 Vector tool processing: {user_input}")

    try:
        summary = st.session_state.george_memory.load_memory_variables({}).get("summary", "")

        # --- Retrieval ---
        logger.info("📚 Performing similarity search...")
        # Increase k temporarily if you suspect relevant docs are too far down the ranking
        docs_and_scores = vectorstore.similarity_search_with_score(user_input, k=30)

        logger.info(f"🔎 Retrieved {len(docs_and_scores)} raw documents from vectorstore")

        filtered = [(doc, score) for doc, score in docs_and_scores if len(doc.page_content.strip()) >= 50]
        logger.info(f"🔍 {len(filtered)} documents passed minimum length filter (≥ 50 chars)")

        seen, unique_docs = set(), []
        for doc, score in filtered:
            # Using full page_content for de-duplication can be safer for exact facts
            # or a larger snippet than just 100 chars if content is often very similar
            snippet = doc.page_content  # Changed from [:100] to full content for more robust deduplication
            if snippet not in seen:
                unique_docs.append((doc, score))
                seen.add(snippet)

        logger.info(f"🧹 {len(unique_docs)} unique documents retained after de-duplication")

        if not unique_docs:
            return "Hmm, I found some documents but they seem too short or irrelevant to be helpful. Could you rephrase your question?"

        # You can add more specific boost terms here if needed,
        # e.g., for location-specific queries
        boost_terms = ["eco", "green", "environment", "sustainab", "organic"]
        if any(term in user_input.lower() for term in boost_terms):
            logger.info("⚡ Boost terms detected — reordering results for eco-relevance")
            unique_docs = sorted(
                unique_docs,
                key=lambda pair: any(term in pair[0].page_content.lower() for term in boost_terms),
                reverse=True
            )

        # Add a specific boost for location if the query explicitly asks for it
        location_query_terms = ["where", "address", "location", "find", "street", "map", "directions"]
        if any(term in user_input.lower() for term in location_query_terms):
            logger.info("⚡ Location query detected — reordering results for location relevance")
            unique_docs = sorted(
                unique_docs,
                key=lambda pair: any(term in pair[0].page_content.lower() for term in location_query_terms) or \
                                 ("address" in pair[0].page_content.lower() or "location" in pair[
                                     0].page_content.lower()),
                reverse=True
            )

        # Pass the top 10 documents to the LLM
        top_docs = [doc for doc, _ in unique_docs[:10]]
        context = "\n\n".join(doc.page_content for doc in top_docs)

        summary = st.session_state.george_memory.load_memory_variables({}).get("summary", "")

        logger.debug("📥 Prompt inputs for LLM:")
        logger.debug(f"→ Summary: {summary[:100]}...")  # Log truncated summary
        logger.debug(f"→ Context (first 500 chars): {context[:500]}...")  # Log truncated context for brevity
        logger.debug(
            f"→ FULL CONTEXT PASSED TO LLM for question '{user_input}':\n{context}")  # Keep this for detailed debugging
        logger.debug(f"→ Question: {user_input}")

        response = (vector_prompt | llm).invoke(
            {"summary": summary, "context": context, "question": user_input},
            config={"callbacks": [LangChainTracer()]}  # Trace the LLM call
        ).content.strip()

        st.session_state.george_memory.save_context(
            {"input": user_input},
            {"output": response}
        )

        logger.info(f"🤖 Vector tool response: {response}")
        return response

    except Exception as e:
        logger.error(f"❌ vector_tool_func error: {e}", exc_info=True)
        return "Sorry, I encountered an issue trying to retrieve information for you right now. Please try again or rephrase your question."


# --- LangChain tool definition ---
vector_tool = Tool(
    name="vector_tool",
    func=vector_tool_func,
    description="Answers questions about rooms, policies, amenities, and hotel info from embedded documents."
)