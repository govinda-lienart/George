# Last updated: 2025-05-05

# ========================================
# 📦 Imports
# ========================================
from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm, vectorstore

# ========================================
# 🤖 Vector Search Function for George
# ========================================
def vector_search(query):
    # ----------------------------------------
    # 🔍 Retrieve and clean similar documents
    # ----------------------------------------
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

    # ----------------------------------------
    # 🌱 Boost sustainability-related content
    # ----------------------------------------
    boost_terms = ["eco", "green", "environment", "sustainab", "organic"]
    if any(term in query.lower() for term in boost_terms):
        docs = sorted(
            docs,
            key=lambda d: any(term in d.page_content.lower() for term in boost_terms),
            reverse=True
        )

    docs = docs[:10]

    # ----------------------------------------
    # ✏️ Prompt construction
    # ----------------------------------------
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

    # ----------------------------------------
    # 🔗 Link map and friendly names
    # ----------------------------------------
    friendly_names = {
        "policy": "Hotel Policies page",
        "rooms": "Rooms page",
        "environmental-commitment": "Environmental Commitment page",
        "breakfast-guest-amenities": "Breakfast & Amenities page",
        "contactlocation": "Contact & Location page",
        "enviroment": "Environmental Info page",
        "home": "homepage"
    }

    link_map = {
        "policy": "https://sites.google.com/view/chez-govinda/policy",
        "rooms": "https://sites.google.com/view/chez-govinda/rooms",
        "environmental-commitment": "https://sites.google.com/view/chez-govinda/environmental-commitment",
        "breakfast-guest-amenities": "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities",
        "contactlocation": "https://sites.google.com/view/chez-govinda/contactlocation",
        "enviroment": "https://sites.google.com/view/chez-govinda/enviroment",
        "home": "https://sites.google.com/view/chez-govinda/home"
    }

    # ----------------------------------------
    # ✅ Match using explicit metadata["page"]
    # ----------------------------------------
    matched_key = None
    for doc in docs:
        page_key = doc.metadata.get("page", "")
        if page_key in friendly_names:
            matched_key = page_key
            break

    if matched_key:
        name = friendly_names[matched_key]
        url = link_map[matched_key]
        final_answer += f"\n\n🔗 You can read more on our [{name}]({url})."

    return final_answer

# ========================================
# 🧰 Tool Registration
# ========================================
vector_tool = Tool(
    name="vector",
    func=vector_search,
    description="Hotel details and policies."
)
