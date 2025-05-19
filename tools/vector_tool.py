# Last updated: 2025-05-19 — memory support + improved vector logging

from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm, vectorstore
from logger import logger
import streamlit as st

# --- Hardcoded fallback links per category ---
HARDCODED_LINKS = {
    "environment": "https://sites.google.com/view/chez-govinda/environmental-commitment",
    "rooms": "https://sites.google.com/view/chez-govinda/rooms",
    "breakfast": "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities",
    "amenities": "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities",
    "wellness": "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities",
    "policy": "https://sites.google.com/view/chez-govinda/policy",
    "contactlocation": "https://sites.google.com/view/chez-govinda/contact-location"
}

link_map = {
    "environment": (
        ["environment", "eco", "green", "sustainab", "organic", "nature", "footprint"],
        "🌱 You can read more on our [Environmental Commitment page]({link})."
    ),
    "rooms": (
        ["rooms", "accommodation", "suites", "bedroom", "stay", "lodging"],
        "🛏️ You can explore our [Rooms page]({link})."
    ),
    "breakfast": (
        ["breakfast", "dining", "food", "plant-based", "vegan", "vegetarian", "organic", "morning meal"],
        "🍳 More about [Breakfast and Guest Amenities]({link})."
    ),
    "amenities": (
        ["amenities", "facilities", "services", "Wi-Fi", "garden", "yoga", "honesty bar"],
        "✨ View all our [Amenities]({link})."
    ),
    "wellness": (
        ["wellness", "relaxation", "peace", "meditation", "yoga", "mindfulness", "garden access"],
        "🧘 Learn more on our [Wellness page]({link})."
    ),
    "policy": (
        ["policy", "policies", "rules", "terms", "conditions", "pet", "dog", "cat", "animal"],
        "📄 Review our full [Hotel Policy here]({link})."
    ),
    "contactlocation": (
        ["contact", "location", "address", "directions", "map", "navigate"],
        "📍 Visit [Contact & Location]({link})."
    )
}

# --- Prompt template for response generation ---
vector_prompt = PromptTemplate(
    input_variables=["summary", "context", "question", "source_link"],
    template="""
You are George, the friendly AI receptionist at *Chez Govinda*.

Conversation so far:
{summary}

Hotel Knowledge Base:
{context}

User: {question}

When responding to questions about rooms or accommodations, always include a complete list of all 7 room types

Respond as George from the hotel team. Use a warm and concise tone. Never refer to Chez Govinda in third person.
If available, append: "You can find more details [here]({source_link})."
"""
)

# --- Tool logic ---
def vector_tool_func(user_input: str) -> str:
    try:
        logger.info(f"🔍 Vector search started for: {user_input}")
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

        # Determine source link
        matched_link = None
        for category, (keywords, _) in link_map.items():
            if any(k in user_input.lower() for k in keywords):
                for doc in top_docs:
                    source = doc.metadata.get("source", "")
                    if category in source.lower():
                        matched_link = source
                        logger.info(f"🔗 Matched source: {source} (from vector metadata)")
                        break
                if not matched_link:
                    matched_link = HARDCODED_LINKS.get(category)
                    logger.info(f"🔗 Using hardcoded fallback link for category: {category} → {matched_link}")
                break

        summary = st.session_state.george_memory.load_memory_variables({}).get("summary", "")

        logger.debug("📥 Prompt inputs for LLM:")
        logger.debug(f"→ Summary: {summary[:100]}...")
        logger.debug(f"→ Context: {context[:100]}...")
        logger.debug(f"→ Question: {user_input}")
        logger.debug(f"→ Source Link: {matched_link}")

        response = (vector_prompt | llm).invoke({
            "summary": summary,
            "context": context,
            "question": user_input,
            "source_link": matched_link or ""
        }).content.strip()

        st.session_state.george_memory.save_context(
            {"input": user_input},
            {"output": response}
        )

        logger.info(f"🤖 Vector tool response: {response}")
        return response

    except Exception as e:
        logger.error(f"❌ vector_tool_func error: {e}", exc_info=True)
        return "Sorry, I couldn’t retrieve relevant information right now."

# --- LangChain tool definition ---
vector_tool = Tool(
    name="vector_tool",
    func=vector_tool_func,
    description="Answers questions about rooms, policies, amenities, and hotel info from embedded documents."
)