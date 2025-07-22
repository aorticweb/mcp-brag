import time

from embedder.store.store import DataSourceMap
from server.workers.embedding import generate_embeddings_for_file, search
from server.main import start_embedder_thread, start_vec_storage_thread

if __name__ == "__main__":
    embedder_read_queue, embedder_write_queue = start_embedder_thread()
    my_source_map = DataSourceMap()
    start_vec_storage_thread(my_source_map, embedder_write_queue)
    # file_path = "data/How I Built a Multi-Agent Powerhouse with Google’s ADK and MCP Without Losing My Mind _ by Subhadip Saha _ May, 2025 _ AI Advances.html"
    file_path = "data/2025-05-22_Quanta_Services_Announces_Quarterly_Cash_376.pdf"
    text_input_count = generate_embeddings_for_file(file_path, embedder_read_queue)
    print(f"Text input count: {text_input_count}")

    while len(my_source_map.get(file_path)._id_to_text) < text_input_count:
        time.sleep(0.1)

    results = search(
        "What is the purpose of an mcp server in an agentic framework?",
        embedder_read_queue,
        my_source_map,
    )
    assert len(results) > 0

    print("==================")
    for result in results:
        print(result.text)
        print("==================")
