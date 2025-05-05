from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm, vectorstore

# Hardcoded links for fallback
HARDCODED_LINKS = {
    "environment":     "https://sites.google.com/view/chez-govinda/environmental-commitment",
    "rooms":           "https://sites.google.com/view/chez-govinda/rooms",
    "breakfast":       "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities",
    "amenities":       "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities",
    "wellness":        "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities",
    "policy":          "https://sites.google.com/view/chez-govinda/policy",
    "contactlocation": "https://sites.google.com/view/chez-govinda/contact-location"
}

# Category link messages
link_map = {
    "environment": (
        ["environment", "eco", "green", "sustainab", "organic", "nature", "footprint"],
        "🌱 You can read more about this on our [Environmental Commitment page]({link})."
    ),
    "rooms": (
        ["rooms", "accommodation", "suites", "bedroom", "stay", "lodging"],
        "🛏️ You can check out more details on our [Rooms page]({link})."
    ),
    "breakfast": (
        ["breakfast", "dining", "food", "plant-based", "vegan", "vegetarian", "organic", "local produce", "morning meal"],
        "🍳 You can find details about [Breakfast and Guest Amenities]({link})."
    ),
    "amenities": (
        ["amenities", "facilities", "services", "Wi-Fi", "garden", "yoga", "snacks", "honesty bar", "relaxation"],
        "✨ You can find details about [Breakfast and Guest Amenities]({link})."
    ),
    "wellness": (
        ["wellness", "relaxation", "peace", "meditation", "yoga", "mindfulness", "garden access"],
        "🧘 For a rejuvenating experience, explore our [Wellness offerings]({link})."
    ),
    "policy": (
        ["policy", "policies", "rules", "terms", "conditions", "pet", "dog", "cat", "animal", "pets"],
        "📄 You can find more details on our [Hotel Policy page]({link})."
    ),
    "contactlocation": (
        ["contact", "location", "address", "directions", "how to get", "map", "reach", "navigate"],
        "📍 You can find details about [Contact and Location]({link})."
    )
}


def vector_search(query):
    docs_and_scores = vectorstore.similarity_search_with_score(query, k=30)

    if not docs_and_scores:
        return "❌ I couldn’t find anything relevant in our documents."

    # Filter out very short or empty chunks
    filtered = [(doc, score) for doc, score in docs_and_scores if len(doc.page_content.strip()) >= 50]
    if not filtered:
        return "Hmm, I found some documents but they seem too short to be helpful. Could you rephrase your question?"

    # Deduplicate by chunk content
    seen = set()
    unique_docs = []
    for doc, score in filtered:
        snippet = doc.page_content[:100]
        if snippet not in seen:
            unique_docs.append((doc, score))
            seen.add(snippet)

    # Boost sustainability content
    boost_terms = ["eco", "green", "environment", "sustainab", "organic"]
    if any(term in query.lower() for term in boost_terms):
        unique_docs = sorted(
            unique_docs,
            key=lambda pair: any(term in pair[0].page_content.lower() for term in boost_terms),
            reverse=True
        )

    top_docs = [doc for doc, _ in unique_docs[:10]]

    # Prepare context for LLM
    context = "\n\n".join(doc.page_content for doc in top_docs)
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
You are George, the friendly receptionist at Chez Govinda.

Answer the user's question in a warm and concise paragraph, using only the information below. Prioritize anything about sustainability or green practices when applicable.

{context}

User: {question}
"""
    )

    final_answer = (prompt | llm).invoke({"context": context, "question": query}).content.strip()

    # Decide best link based on query and matched content
    matched_link = None
    for category, (keywords, message_template) in link_map.items():
        if any(word in query.lower() for word in keywords):
            # Try to find a matching source link from the top docs
            for doc in top_docs:
                source = doc.metadata.get("source", "")
                if category in source.lower():
                    matched_link = source
                    break
            # Fallback to hardcoded link
            if not matched_link:
                matched_link = HARDCODED_LINKS.get(category)
            if matched_link:
                final_answer += "\n\n" + message_template.format(link=matched_link)
            break

    return final_answer


vector_tool = Tool(
    name="vector",
    func=vector_search,
    description="Hotel details and policies."
)
