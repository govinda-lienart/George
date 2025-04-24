# Last updated: 2025-04-24 22:11:38
def find_source_link(docs, keyword):
    for doc in docs:
        source = doc.metadata.get("source", "")
        if keyword.lower() in source.lower():
            return source
    return None