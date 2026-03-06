from openai import AsyncOpenAI
from .prompts import LAW_QUERY_PROMPT
from .retrieval import RetrievalQueue

MODEL_NAME = "qwen/qwen3.5-27b"


async def retrieve_laws(
    client: AsyncOpenAI,
    content: str,
    categories: list[str],
    search_queue: RetrievalQueue,
) -> str:
    """Finds and formats relevant Indonesian laws, returning a Markdown string."""
    if not categories:
        return ""

    cats_str = ", ".join(categories)

    # 1. Ask LLM to generate search query
    try:
        res = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": LAW_QUERY_PROMPT},
                {
                    "role": "user",
                    "content": f"Categories: {cats_str}\n\nContent snippet: {content[:500]}",
                },
            ],
            temperature=0.1,
        )
        query = res.choices[0].message.content.strip()
    except Exception as e:
        print(f"Law query generation error: {e}")
        return "Gagal menghasilkan pencarian hukum (Error in LLM)."

    # 2. Run retrieval
    results = []
    try:
        results = await search_queue.retrieve(query)
    except Exception as e:
        print(f"Retrieval error: {e}")
        return "Gagal mencari pasal (Network error)."

    if not results:
        return f"*(Dicari: {query})*\nTidak ditemukan pasal hukum secara spesifik."

    # 3. Format raw results into readable text
    laws_prompt = """Based on the search results provided, summarize the core Indonesian laws (Undang-Undang, KUHP, UU ITE, dsb) that relate to the offense categories provided.
    Format your response in simple Markdown, answering directly in Indonesian. Cite the pasal (article numbers) clearly.
    Do not hallucinate laws not mentioned in the typical context of these search results.
    """

    search_context = "\n".join(
        [f"- {r['title']}: {r['description']}" for r in results[:5]]
    )  # Top 5

    try:
        final_res = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": laws_prompt},
                {
                    "role": "user",
                    "content": f"Categories: {cats_str}\n\nSearch Results:\n{search_context}",
                },
            ],
            temperature=0.2,
        )
        laws_summary = final_res.choices[0].message.content.strip()
        return laws_summary
    except Exception as e:
        print(f"Law summarization error: {e}")
        return "Gagal merangkum hukum (Error in LLM)."
