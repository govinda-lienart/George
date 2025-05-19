# Last updated: 2025-05-19 — memory support + improved vector logging

from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm, vectorstore
from logger import logger
import streamlit as st
from langchain.callbacks import LangChainTracer  # Import the tracer
from langchain.chains import RetrievalQA

# --- Prompt template for response generation ---
vector_prompt = PromptTemplate(
    input_variables=["summary", "context", "question"],
    template="""
You are George, the friendly AI receptionist at *Chez Govinda*.

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

When discussing rooms, always list all 7 room types: Single Room, Double Room, Suite Room, Economy Room, Romantic Room, Family Room, and Kids Friendly Room.

Respond as George from the hotel team. Use a warm and concise tone. Never refer to Chez Govinda in third person.
"""
)


# --- Tool logic ---
def vector_tool_func(user_input: str) -> str:
    logger.info(f"🔍 Vector tool processing: {user_input}")

    try:
        summary = st.session_state.george_memory.load_memory_variables({}).get("summary", "")

        # --- Retrieval ---
        logger.info("📚 Performing similarity search...")
        docs_and_scores = vectorstore.similarity_search_with_score(user_input, k=30)

        logger.info(f"🔎 Retrieved {len(docs_and_scores)} raw documents from vectorstore")

        filtered = [(doc, score) for doc, score in docs_and_scores if len(doc.page_content.strip()) >= 50]
        logger.info(f"🔍 {len(filtered)} documents passed minimum length filter (≥ 50 chars)")

        seen, unique_docs = set(), []
        for doc, score in filtered:
            snippet = doc.page_content[:100]
            if snippet not in seen:
                unique_docs.append((doc, score))
                seen.add(snippet)

        logger.info(f"🧹 {len(unique_docs)} unique documents retained after de-duplication")

        if not unique_docs:
            return "Hmm, I found some documents but they seem too short to be helpful. Could you rephrase your question?"

        boost_terms = ["eco", "green", "environment", "sustainab", "organic"]
        if any(term in user_input.lower() for term in boost_terms):
            logger.info("⚡ Boost terms detected — reordering results for eco-relevance")
            unique_docs = sorted(
                unique_docs,
                key=lambda pair: any(term in pair[0].page_content.lower() for term in boost_terms),
                reverse=True
            )

        top_docs = [doc for doc, _ in unique_docs[:10]]
        context = "\n\n".join(doc.page_content for doc in top_docs)

        summary = st.session_state.george_memory.load_memory_variables({}).get("summary", "")

        logger.debug("📥 Prompt inputs for LLM:")
        logger.debug(f"→ Summary: {summary[:100]}...")
        logger.debug(f"→ Context: {context[:100]}...")
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
        return "Sorry, I couldn't retrieve relevant information right now."


# --- LangChain tool definition ---
vector_tool = Tool(
    name="vector_tool",
    func=vector_tool_func,
    description="Answers questions about rooms, policies, amenities, and hotel info from embedded documents."
)