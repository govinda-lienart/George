
# ================================
# 🔗 Source Link Finder
# ================================
def find_source_link(docs, keyword):
    """
    Returns the source path from a list of doc objects where the keyword is found.
    """
    for doc in docs:
        source = doc.metadata.get("source", "")
        if keyword.lower() in source.lower():
            return source
    return None