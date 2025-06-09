# ========================================
# 📋 ROLE OF THIS SCRIPT - vector_tool.py
# ========================================

"""
Vector tool module for the George AI Hotel Receptionist app.
- Performs semantic search on hotel knowledge base using vector embeddings
- Retrieves relevant information about rooms, policies, amenities, and services
- Processes user queries through similarity search and document filtering
- Provides intelligent content boosting for specific query types (eco, location)
- Manages conversation memory integration for contextual responses
- Generates accurate, fact-based responses from embedded hotel documentation
- Essential component for George's knowledge-driven guest information system
"""

# ========================================
# 📦 VECTOR TOOL DEFINITION
# ========================================

# ────────────────────────────────────────────────
# 🧠 LANGCHAIN & CONFIG IMPORTS
# ────────────────────────────────────────────────
from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm, vectorstore  # Pre-initialized LLM and vector store

# ────────────────────────────────────────────────
# 🔧 STANDARD & THIRD-PARTY IMPORTS
# ────────────────────────────────────────────────
from logger import logger
import streamlit as st
from langchain.callbacks import LangChainTracer  # For LangSmith logging
from langchain.chains import RetrievalQA  # Optional helper from LangChain

# ========================================
# 🧾 PROMPT TEMPLATE FOR VECTOR TOOL
# ========================================
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

**Key factual rules:**
- If asked about room types, always list all 7 standard room types : Single, Double, Suite, Economy, Romantic, Family, Kids Friendly.
- If asked about the address/location, extract it **exactly** from the context or say it's not available, and include the location link.

Conversation so far:
{summary}

Hotel Knowledge Base:
{context}

User: {question}

---
**Key factual rules:**
- If asked about room types, always list all 7 standard room types : Single (€100/night), Double (€150/night), Suite (€250/night), Economy (€90/night), Romantic (€220/night), Family (€300/night), Kids Friendly (€200/night).
- If asked about the address/location, extract it **exactly** from the context or say it's not available, and include the location link.

Please answer the user's question using the facts above. Do not include any additional remarks or ask if the user needs anything else.

Use markdown when helpful. When relevant, include one of these reference links:

1. Rooms and accommodations: [Rooms](https://sites.google.com/view/chez-govinda/rooms)
2. Environmental commitments: [Environmental Commitment](https://sites.google.com/view/chez-govinda/environmental-commitment)
3. Breakfast and dining: [Breakfast and Guest Amenities](https://sites.google.com/view/chez-govinda/breakfast-guest-amenities)
4. Amenities: [Amenities](https://sites.google.com/view/chez-govinda/breakfast-guest-amenities)
5. Wellness options: [Wellness page](https://sites.google.com/view/chez-govinda/breakfast-guest-amenities)
6. Policies: [Hotel Policy](https://sites.google.com/view/chez-govinda/policy)
7. Contact and location: [Contact & Location](https://sites.google.com/view/chez-govinda/contactlocation)



Respond as George. Use a warm tone, but never follow up or prolong the chat.
"""
)

# ========================================
# ⚙️ VECTOR TOOL FUNCTION
# ========================================
# ┌─────────────────────────────────────────┐
# │  PROCESS USER INPUT THROUGH VECTORS     │
# └─────────────────────────────────────────┘
def vector_tool_func(user_input: str) -> str:
    """Main logic to handle questions routed to the vector tool."""
    logger.info(f"🔍 Vector tool processing: {user_input}")

    try:

        # ────────────────────────────────────────────────
        # 🔎 Perform vector similarity search across docs/chunks
        # ────────────────────────────────────────────────
        logger.info("📚 Performing similarity search...")
        docs_and_scores = vectorstore.similarity_search_with_score(user_input, k=14)
        logger.info(f"🔎 Retrieved {len(docs_and_scores)} raw documents from vectorstore")

        # Filter short documents
        filtered = [(doc, score) for doc, score in docs_and_scores if len(doc.page_content.strip()) >= 50]
        logger.info(f"🔍 {len(filtered)} documents passed minimum length filter (≥ 50 chars)")

        # ────────────────────────────────────────────────
        # 🧹 Remove duplicates
        # ────────────────────────────────────────────────
        seen, unique_docs = set(), []
        for doc, score in filtered:
            snippet = doc.page_content
            if snippet not in seen:
                unique_docs.append((doc, score))
                seen.add(snippet)
        logger.info(f"🧹 {len(unique_docs)} unique documents retained after de-duplication")

        if not unique_docs:
            return "Hmm, I found some documents but they seem too short or irrelevant to be helpful. Could you rephrase your question?"

        # ────────────────────────────────────────────────
        # 🚀 Boost relevant terms based on query intent
        # ────────────────────────────────────────────────

        location_query_terms = ["where", "address", "location", "find", "street", "map", "directions"]
        if any(term in user_input.lower() for term in location_query_terms):
            logger.info("⚡ Location query detected — reordering results for location relevance")
            unique_docs = sorted(
                unique_docs,
                key=lambda pair: any(term in pair[0].page_content.lower() for term in location_query_terms)
                     or ("address" in pair[0].page_content.lower() or "location" in pair[0].page_content.lower()),
                reverse=True
            )

        # ────────────────────────────────────────────────
        # 🧠 Generate response from top documents
        # ────────────────────────────────────────────────
        top_docs = [doc for doc, _ in unique_docs[:10]]
        context = "\n\n".join(doc.page_content for doc in top_docs) # main var
        summary = st.session_state.george_memory.load_memory_variables({}).get("summary", "")

        logger.debug("📥 Prompt inputs for LLM:")
        logger.debug(f"→ Summary: {summary[:100]}...")
        logger.debug(f"→ Context (first 500 chars): {context[:500]}...")
        logger.debug(f"→ FULL CONTEXT PASSED TO LLM for question '{user_input}':\n{context}")
        logger.debug(f"→ Question: {user_input}")

        # Generate answer using prompt + context from the vector
        response = (vector_prompt | llm).invoke(
            {"summary": summary, "context": context, "question": user_input},
            config={"callbacks": [LangChainTracer()]}
        ).content.strip()

        # Save the exchange in memory
        st.session_state.george_memory.save_context(
            {"input": user_input},
            {"output": response}
        )

        logger.info(f"🤖 Vector tool response: {response}")
        return response

    except Exception as e:
        logger.error(f"❌ vector_tool_func error: {e}", exc_info=True)
        return "Sorry, I encountered an issue trying to retrieve information for you right now. Please try again or rephrase your question."

# ========================================
# 🧩 LANGCHAIN TOOL OBJECT (Exported)
# ========================================
# ┌─────────────────────────────────────────┐
# │  WRAP VECTOR TOOL INTO LangChain Tool   │
# └─────────────────────────────────────────┘
vector_tool = Tool(
    name="vector_tool",
    func=vector_tool_func,
    description="Answers questions about rooms, policies, amenities, and hotel info from embedded documents."
)