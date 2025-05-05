#   Last updated: 2025-05-05 18:30:00 CEST (Generalized)
def find_source_link(docs, relevant_keywords):
    for doc in docs:
        source = doc.metadata.get("source", "")
        if source:
            for keyword in relevant_keywords:
                if keyword.lower() in source.lower():
                    return source
    return None