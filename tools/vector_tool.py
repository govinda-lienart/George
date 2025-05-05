# ========================================
# 🧠 LangChain & Vector Store Configuration
# ========================================
from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm, vectorstore

# ========================================
# 🔗 Hardcoded Backup URLs for Each Category
# ========================================
HARDCODED_LINKS = {
    "environment":     "https://sites.google.com/view/chez-govinda/environmental-commitment",
    "rooms":           "https://sites.google.com/view/chez-govinda/rooms",
    "breakfast":       "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities",
    "amenities":       "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities",
    "wellness":        "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities",
    "policy":          "https://sites.google.com/view/chez-govinda/policy",
    "contactlocation": "https://sites.google.com/view/chez-govinda/contact-location"
}

# ========================================
# 🧩 Query Keywords → URL + Message Mapping
# ========================================
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

# ========================================
# 🤖 George’s Smart Vector-Based Search Tool
# ========================================
def vector_search(query):
    docs_and_scores = vectorstore.similarity_search_with_score(query, k=30)

    if not docs_and_scores:
        return "❌ I couldn’t find anything relevant in our documents."

    # ----------------------------------------
    # 🧹 Filter and deduplicate content
    # ----------------------------------------
    filtered = [(doc, score) for doc, score in docs_and_scores if len(doc.page_content.strip()) >= 50]
    seen, unique_docs = set(), []
    for doc, score in filtered:
        snippet = doc.page_content[:100]
        if snippet not in seen:
            unique_docs.append((doc, score))
            seen.add(snippet)

    if not unique_docs:
        return "Hmm, I found some documents but they seem too short to be helpful. Could you rephrase your question?"

    # ----------------------------------------
    # 🍃 Boost sustainability results if needed
    # ----------------------------------------
    boost_terms = ["eco", "green", "environment", "sustainab", "organic"]
    if any(term in query.lower() for term in boost_terms):
        unique_docs = sorted(
            unique_docs,
            key=lambda pair: any(term in pair[0].page_content.lower() for term in boost_terms),
            reverse=True
        )

    # ----------------------------------------
    # 📚 Prepare top content chunks as context
    # ----------------------------------------
    top_docs = [doc for doc, _ in unique_docs[:10]]
    context = "\n\n".join(doc.page_content for doc in top_docs)

    # ----------------------------------------
    # 🔍 Match query to relevant source link
    # ----------------------------------------
    matched_link = None
    for category, (keywords, _) in link_map.items():
        if any(k in query.lower() for k in keywords):
            for doc in top_docs:
                source = doc.metadata.get("source", "")
                if category in source.lower():
                    matched_link = source
                    break
            if not matched_link:
                matched_link = HARDCODED_LINKS.get(category)
            break

    # ----------------------------------------
    # 📝 Prompt Template with Link Injection
    # ----------------------------------------
    prompt = PromptTemplate(
        input_variables=["context", "question", "source_link"],
        template="""
You are George, the friendly AI receptionist at *Chez Govinda*.

You always speak **as part of the hotel team**, so say **"our hotel"**, **"we offer"**, or **"our rooms"** — never use "their hotel" or talk about Chez Govinda in third person.
If someone asks about rooms, **always return the full list of the seven room types** from hotel documentation in the database.

Answer the user's question in a warm, concise paragraph using only the information below.
If a helpful page is available about rooms and other topics, conclude with a sentence like: "You can find more details [here]({source_link})."

{context}

User: {question}
"""
    )

    # ----------------------------------------
    # 🤖 Invoke LLM with context and link
    # ----------------------------------------
    final_answer = (prompt | llm).invoke({
        "context": context,
        "question": query,
        "source_link": matched_link or ""
    }).content.strip()

    return final_answer

# ========================================
# 🧰 LangChain Tool Wrapper
# ========================================
vector_tool = Tool(
    name="vector",
    func=vector_search,
    description="Hotel details and policies."
)