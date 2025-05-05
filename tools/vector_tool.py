# Last updated: 2025-05-05 17:32:00 CEST
from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm, vectorstore
# from utils.helpers import find_source_link  # We might not need this anymore


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
        if doc.page_content[:100] not in seen:
            unique_docs.append(doc)
            seen.add(doc.page_content[:100])
    docs = unique_docs

    # Boost sustainability
    boost_terms = ["eco", "green", "environment", "sustainab", "organic"]
    if any(term in query.lower() for term in boost_terms):
        docs = sorted(docs, key=lambda d: any(term in d.page_content.lower() for term in boost_terms), reverse=True)

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

    # Directly use the URL from the most relevant document
    if docs:
        most_relevant_doc = docs[0]  # Assuming the first doc is the most relevant
        source_url = most_relevant_doc.metadata.get("source")
        if source_url:
            final_answer += f"\n\n📖 You can find more details on this topic at: {source_url}"

    return final_answer


vector_tool = Tool(
    name="vector",
    func=vector_search,
    description="Hotel details and policies."
)