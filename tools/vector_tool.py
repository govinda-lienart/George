from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm, vectorstore
from utils.helpers import find_source_link

HARDCODED_LINKS = {
    "environment":     "https://sites.google.com/view/chez-govinda/environmental-commitment",
    "rooms":           "https://sites.google.com/view/chez-govinda/rooms",
    "breakfast":       "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities",
    "amenities":       "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities",
    "wellness":        "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities",
    "policy":          "https://sites.google.com/view/chez-govinda/policy",
    "contactlocation": "https://sites.google.com/view/chez-govinda/contact-location"
}

def find_source_link(docs, relevant_keywords):
    for doc in docs:
        source = doc.metadata.get("source", "")
        if source:
            for keyword in relevant_keywords:
                if keyword.lower() in source.lower():
                    return source

    for doc in docs:
        source = doc.metadata.get("source", "")
        content = doc.page_content.lower()
        for keyword in relevant_keywords:
            if keyword.lower() in content and source:
                return source

    for category, url in HARDCODED_LINKS.items():
        if any(keyword.lower() in category for keyword in relevant_keywords):
            return url

    return None


def vector_search(query):
    docs = vectorstore.similarity_search(query, k=30)

    if not docs:
        return "❌ I couldn’t find anything relevant in our documents."

    if all(len(doc.page_content.strip()) < 50 for doc in docs):
        return "Hmm, I found some documents but they seem too short to be helpful. Could you rephrase your question?"

    # Deduplicate
    seen = set()
    unique_docs = []
    for doc in docs:
        snippet = doc.page_content[:100]
        if snippet not in seen:
            unique_docs.append(doc)
            seen.add(snippet)
    docs = unique_docs

    # Boost sustainability
    boost_terms = ["eco", "green", "environment", "sustainab", "organic"]
    if any(term in query.lower() for term in boost_terms):
        docs = sorted(
            docs,
            key=lambda d: any(term in d.page_content.lower() for term in boost_terms),
            reverse=True
        )

    docs = docs[:10]

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
You are George, the friendly receptionist at Chez Govinda.

Answer the user's question in a warm and concise paragraph, using only the information below. Prioritize anything about sustainability or green practices when applicable.

{context}

User: {question}
"""
    )

    context = "\n\n".join(doc.page_content for doc in docs)
    final_answer = (prompt | llm).invoke({"context": context, "question": query}).content.strip()

    # Always try to find a relevant link
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
            ["policy", "policies", "rules", "terms", "conditions", "pet"],
            "📄 You can find more details on our [Hotel Policy page]({link})."
        ),
        "contactlocation": (
            ["contact", "location", "address", "directions", "how to get", "map", "reach", "navigate"],
            "📍 You can find details about [Contact and Location]({link})."
        )
    }

    priority = ["environment", "rooms", "breakfast", "amenities", "wellness", "policy", "contactlocation"]

    # Try metadata source from top doc
    source_url = docs[0].metadata.get("source")
    if not source_url:
        # If not available, try keyword-based lookup
        for category in priority:
            keywords, _ = link_map[category]
            source_url = find_source_link(docs, keywords)
            if source_url:
                break

    if source_url:
        final_answer += f"\n\n📖 You can find more details on this topic at: {source_url}"

    return final_answer


vector_tool = Tool(
    name="vector",
    func=vector_search,
    description="Hotel details and policies."
)
