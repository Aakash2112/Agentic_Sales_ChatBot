from rag.retriever import get_context


def search_cars(query: str) -> str:
    """
    Tool: Search the Kia car catalog using RAG.
    Returns relevant information from the PDF data based on the query.
    """
    context = get_context(query)
    return context
