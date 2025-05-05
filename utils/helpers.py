def find_source_link(docs, relevant_keywords):
    # 1. Try to match by source URL
    for doc in docs:
        source = doc.metadata.get("source", "")
        if source:
            for keyword in relevant_keywords:
                if keyword.lower() in source.lower():
                    return source

    # 2. If not found in source, look inside page content (fallback)
    for doc in docs:
        source = doc.metadata.get("source", "")
        content = doc.page_content.lower()
        for keyword in relevant_keywords:
            if keyword.lower() in content and source:
                return source

    return None
