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

**Crucial Instruction: Respond ONLY based on the factual information explicitly provided in the "Hotel Knowledge Base" below. Do NOT invent information, make assumptions, or provide details not found in the provided context.**
If you cannot find the exact answer to a factual question in the "Hotel Knowledge Base," state clearly that you don't have that specific information at the moment.

Conversation so far:
{summary}

Hotel Knowledge Base:
{context}

User: {question}

When responding, always include the appropriate link based on the topic:

1.  For questions about rooms or accommodations:
    "You can find more details [here](https://sites.google.com/view/chez-govinda/rooms)."

2.  For questions about our environmental commitments:
    "You can read more on our [Environmental Commitment page](https://sites.google.com/view/chez-govinda/environmental-commitment)."

3.  For questions about breakfast or dining:
    "More about [Breakfast and Guest Amenities](https://sites.google.com/view/chez-govinda/breakfast-guest-amenities)."

4.  For questions about amenities or facilities:
    "View all our [Amenities](https://sites.google.com/view/chez-govinda/breakfast-guest-amenities)."

5.  For questions about wellness or relaxation options:
    "Learn more on our [Wellness page](https://sites.google.com/view/chez-govinda/breakfast-guest-amenities)."

6.  For questions about policies or rules:
    "Review our full [Hotel Policy here](https://sites.google.com/view/chez-govinda/policy)."

7.  For questions about contact or location:
    "Visit [Contact & Location](https://sites.google.com/view/chez-govinda/contact-location)."

**Specific Instructions for key factual information:**
- When the user asks about room types, you MUST list all 7 room types: Single Room, Double Room, Suite Room, Economy Room, Romantic Room, Family Room, and Kids Friendly Room. This information MUST be sourced directly from the "Hotel Knowledge Base". If the Knowledge Base does not explicitly list these 7 rooms, state that you cannot find the specific details in the provided information.
- **When the user asks for the hotel's address or precise location, you MUST extract and provide the exact address found in the "Hotel Knowledge Base". Do NOT generate, guess, or make up any part of the address. If the complete and correct address is not found in the "Hotel Knowledge Base", state that you cannot find the specific address details at this moment but provide the "Contact & Location" link.**

Respond as George from the hotel team. Use a warm, concise, and helpful tone. Never refer to Chez Govinda in the third person.
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