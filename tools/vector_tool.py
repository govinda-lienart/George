# Vector_tool.py

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
    # 🔗 Add top document source as link
    # ----------------------------------------
    top_doc = docs[0]
    top_source = top_doc.metadata.get("source", "")

    friendly_names = {
        "home": "homepage",
        "rooms": "Rooms page",
        "policy": "Hotel Policies page",
        "enviroment": "Environmental Info page",
        "environmental-commitment": "Environmental Commitment page",
        "contactlocation": "Contact & Location page",
        "breakfast-guest-amenities": "Breakfast & Amenities page"
    }

    for key, name in friendly_names.items():
        if key in top_source:
            final_answer += f"\n\n🔗 You can read more on our [{name}]({top_source})."
            break

    return final_answer

# ========================================
# 🧰 Tool Registration
# ========================================
vector_tool = Tool(
    name="vector",
    func=vector_search,
    description="Hotel details and policies."
)

)
