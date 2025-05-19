# Last updated: 2025-05-19 — memory support + detailed score logging + LangSmith tracing

from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm, vectorstore
from logger import logger
import streamlit as st
import time

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

vector_prompt = PromptTemplate(
    input_variables=["summary", "context", "question", "source_link"],
    template="""
You are George, the friendly AI receptionist at *Chez Govinda*.

Conversation so far:
{summary}

Hotel Knowledge Base:
{context}

User: {question}

IMPORTANT INSTRUCTION: You must ONLY respond based on information explicitly found in the Hotel Knowledge Base above.
If the Knowledge Base does not contain information that directly answers the user's question, you must say:
"I'm sorry, I don't have specific information about that in our system. Would you like me to check with our staff for you?"

Do NOT make up or assume any hotel information that is not explicitly stated in the Knowledge Base.

Respond as George from the hotel team. Use a warm and concise tone. Never refer to Chez Govinda in third person.
If available, append: "You can find more details [here]({source_link})."
"""
)


def vector_tool_func(user_input: str, callbacks=None) -> str:
    try:
        # Start the vector search process - trace if callbacks provided
        logger.info(f"🔍 Vector search started for: {user_input}")
        search_start_time = time.time()

        # If we have LangSmith callbacks, create a trace for the vector search
        if callbacks:
            # Start a trace for the vector search process
            callbacks[0].on_chain_start(
                {"name": "vector_search_process"},
                {"query": user_input, "timestamp": search_start_time}
            )

        # Perform vector search
        docs_and_scores = vectorstore.similarity_search_with_score(user_input, k=30)
        search_duration = time.time() - search_start_time
        logger.info(f"🔎 Retrieved {len(docs_and_scores)} raw documents from vectorstore")

        # Log search results in the trace
        if callbacks:
            search_results_metadata = {
                "duration_seconds": search_duration,
                "total_documents": len(docs_and_scores),
                "top_scores": [float(score) for _, score in docs_and_scores[:5]] if docs_and_scores else []
            }
            callbacks[0].on_chain_end(search_results_metadata)

        # Step 1: Filter for minimum length
        filtered = [(doc, score) for doc, score in docs_and_scores if len(doc.page_content.strip()) >= 50]
        logger.info(f"🔍 {len(filtered)} documents passed minimum length filter (≥ 50 chars)")

        # Start trace for document processing
        if callbacks:
            callbacks[0].on_chain_start(
                {"name": "document_processing"},
                {"documents_after_length_filter": len(filtered)}
            )

        # Step 2: Remove duplicates
        seen, unique_docs = set(), []
        for doc, score in filtered:
            snippet = doc.page_content[:100].replace("\n", " ").strip()
            if snippet not in seen:
                unique_docs.append((doc, score))
                seen.add(snippet)

        logger.info(f"🧹 {len(unique_docs)} unique documents retained after de-duplication")

        # Log similarity scores for top matches
        for i, (doc, score) in enumerate(unique_docs[:10], start=1):
            logger.info(
                f"📊 Match {i}: Score={score:.4f} — Snippet: {doc.page_content[:80].strip().replace(chr(10), ' ')}")

            # Include document source in logging if available
            if 'source' in doc.metadata and callbacks:
                callbacks[0].on_text(f"Document {i} from {doc.metadata['source']} with score {score:.4f}")

        # End document processing trace
        if callbacks:
            callbacks[0].on_chain_end({
                "unique_documents": len(unique_docs),
                "top_document_score": float(unique_docs[0][1]) if unique_docs else 0
            })

        # Handle no documents case
        if not unique_docs:
            no_docs_msg = "Hmm, I couldn't find any relevant information in our system. Could you rephrase your question?"
            if callbacks:
                callbacks[0].on_chain_end({"message": "No relevant documents found", "response": no_docs_msg})
            return no_docs_msg

        # Optional: Boost eco-relevant content if query contains eco terms
        boost_terms = ["eco", "green", "environment", "sustainab", "organic"]
        if any(term in user_input.lower() for term in boost_terms):
            logger.info("⚡ Boost terms detected — reordering results for eco-relevance")
            unique_docs = sorted(
                unique_docs,
                key=lambda pair: any(term in pair[0].page_content.lower() for term in boost_terms),
                reverse=True
            )

        # Prepare context from top documents
        top_docs = [doc for doc, _ in unique_docs[:10]]
        context = "\n\n".join(doc.page_content for doc in top_docs)

        # Start trace for link matching
        if callbacks:
            callbacks[0].on_chain_start(
                {"name": "link_matching"},
                {"query": user_input}
            )

        # Match relevant link if available
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

        # End link matching trace
        if callbacks:
            callbacks[0].on_chain_end({
                "matched_link": matched_link or "None",
                "link_category": next((cat for cat, (kw, _) in link_map.items()
                                       if any(k in user_input.lower() for k in kw)), "None")
            })

        # Get conversation memory summary
        summary = st.session_state.george_memory.load_memory_variables({}).get("summary", "")

        # Start trace for LLM response generation
        if callbacks:
            callbacks[0].on_chain_start(
                {"name": "llm_response_generation"},
                {
                    "context_length": len(context),
                    "context_preview": context[:200] + "..." if len(context) > 200 else context,
                    "has_conversation_history": bool(summary),
                    "history_length": len(summary)
                }
            )

        # Prepare prompt inputs
        prompt_inputs = {
            "summary": summary,
            "context": context,
            "question": user_input,
            "source_link": matched_link or ""
        }

        # Log the full prompt for debugging
        full_prompt = vector_prompt.format(**prompt_inputs)
        logger.info(f"📝 Sending prompt to LLM with context length {len(context)} chars")

        # Get LLM response with callbacks for tracing
        llm_start_time = time.time()
        response = (vector_prompt | llm).invoke(
            prompt_inputs,
            callbacks=callbacks
        ).content.strip()
        llm_duration = time.time() - llm_start_time

        # End LLM response trace
        if callbacks:
            callbacks[0].on_chain_end({
                "response": response,
                "response_length": len(response),
                "duration_seconds": llm_duration,
                "has_link": matched_link is not None
            })

        # Log the final response
        logger.info(f"🤖 Vector tool response: {response}")
        return response

    except Exception as e:
        # Log error details
        error_message = f"❌ vector_tool_func error: {e}"
        logger.error(error_message, exc_info=True)

        # Include error in trace if callbacks available
        if callbacks:
            callbacks[0].on_chain_error(e)

        return "Sorry, I encountered an error while searching for information. Please try asking in a different way."


# Define the Tool with updated function
vector_tool = Tool(
    name="vector_tool",
    func=vector_tool_func,
    description="Answers questions about rooms, policies, amenities, and hotel info from embedded documents."
)