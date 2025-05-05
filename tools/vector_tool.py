# Last updated: 2025-05-05
from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm, vectorstore

def vector_search(query):
    docs_and_scores = vectorstore.similarity_search_with_score(query, k=30)

    if not docs_and_scores:
        return "❌ I couldn’t find anything relevant in our documents."

    # Filter out too-short chunks
    filtered = [(doc, score) for doc, score in docs_and_scores if len(doc.page_content.strip()) >= 50]
    if not filtered:
        return "Hmm, I found some documents but they seem too short to be helpful. Could you rephrase your question?"

    # Deduplicate based on content snippet
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

    # Trim to top 10 documents
    top_docs = [doc for doc, _ in unique_docs[:10]]

    # Create context
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

    # Use highest scoring doc's metadata URL
    top_source_url = unique_docs[0][0].metadata.get("source")
    if top_source_url:
        final_answer += f"\n\n📖 You can find more details on this topic at: {top_source_url}"

    return final_answer

vector_tool = Tool(
    name="vector",
    func=vector_search,
    description="Hotel details and policies."
)
